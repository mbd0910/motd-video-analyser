#!/usr/bin/env python3
"""Validate LLM analysis JSON files against schema.

This script validates analysis.json files saved from Claude's LLM analysis
against the schema defined in docs/domain/analysis_schema.md.

Usage:
    python scripts/validate_analysis.py                           # Validate all
    python scripts/validate_analysis.py motd_2025-26_2025-11-22  # Validate one
    python scripts/validate_analysis.py --list                    # Show status

Examples:
    # Check all episodes for valid analysis files
    python scripts/validate_analysis.py

    # Validate specific episode
    python scripts/validate_analysis.py motd_2025-26_2025-11-01

    # List which episodes have/need analysis
    python scripts/validate_analysis.py --list
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# Timestamp format: MM:SS (e.g., "12:30", "01:05", "125:00")
TIMESTAMP_PATTERN = re.compile(r'^\d{1,3}:\d{2}$')


def validate_timestamp(value: Any, field_path: str) -> list[str]:
    """Validate a timestamp field (MM:SS format or null)."""
    errors = []
    if value is None:
        return errors  # null is valid for optional timestamps
    if not isinstance(value, str):
        errors.append(f"{field_path}: expected string or null, got {type(value).__name__}")
    elif not TIMESTAMP_PATTERN.match(value):
        errors.append(f"{field_path}: invalid timestamp format '{value}' (expected MM:SS)")
    return errors


def validate_timestamp_block(block: Any, field_path: str, required: bool = False) -> list[str]:
    """Validate a timestamp block with start/end fields."""
    errors = []

    if block is None:
        if required:
            errors.append(f"{field_path}: required but is null")
        return errors

    if not isinstance(block, dict):
        errors.append(f"{field_path}: expected object or null, got {type(block).__name__}")
        return errors

    # Check start and end fields
    if 'start' not in block:
        errors.append(f"{field_path}.start: missing required field")
    else:
        errors.extend(validate_timestamp(block['start'], f"{field_path}.start"))

    if 'end' not in block:
        errors.append(f"{field_path}.end: missing required field")
    else:
        errors.extend(validate_timestamp(block['end'], f"{field_path}.end"))

    return errors


def validate_episode(episode: Any) -> list[str]:
    """Validate the episode-level fields."""
    errors = []

    if not isinstance(episode, dict):
        errors.append("episode: expected object")
        return errors

    # Required: date
    if 'date' not in episode:
        errors.append("episode.date: missing required field")
    elif not isinstance(episode['date'], str):
        errors.append(f"episode.date: expected string, got {type(episode['date']).__name__}")
    elif not re.match(r'^\d{4}-\d{2}-\d{2}$', episode['date']):
        errors.append(f"episode.date: invalid format '{episode['date']}' (expected YYYY-MM-DD)")

    # Required: intro
    errors.extend(validate_timestamp_block(episode.get('intro'), 'episode.intro', required=True))

    # Optional: league_table, next_motd_promo, outro
    for field in ['league_table', 'next_motd_promo', 'outro']:
        if field in episode:
            errors.extend(validate_timestamp_block(episode[field], f'episode.{field}'))

    return errors


def validate_match(match: Any, index: int) -> list[str]:
    """Validate a single match entry."""
    errors = []
    prefix = f"matches[{index}]"

    if not isinstance(match, dict):
        errors.append(f"{prefix}: expected object")
        return errors

    # Required fields
    required_strings = ['home_team', 'away_team', 'venue']
    for field in required_strings:
        if field not in match:
            errors.append(f"{prefix}.{field}: missing required field")
        elif not isinstance(match[field], str):
            errors.append(f"{prefix}.{field}: expected string")

    # Required: order (integer)
    if 'order' not in match:
        errors.append(f"{prefix}.order: missing required field")
    elif not isinstance(match['order'], int):
        errors.append(f"{prefix}.order: expected integer, got {type(match['order']).__name__}")

    # Required: score
    if 'score' not in match:
        errors.append(f"{prefix}.score: missing required field")
    elif isinstance(match['score'], dict):
        if 'home' not in match['score']:
            errors.append(f"{prefix}.score.home: missing required field")
        elif not isinstance(match['score']['home'], int):
            errors.append(f"{prefix}.score.home: expected integer")
        if 'away' not in match['score']:
            errors.append(f"{prefix}.score.away: missing required field")
        elif not isinstance(match['score']['away'], int):
            errors.append(f"{prefix}.score.away: expected integer")
    else:
        errors.append(f"{prefix}.score: expected object")

    # Required: segments
    if 'segments' not in match:
        errors.append(f"{prefix}.segments: missing required field")
    elif isinstance(match['segments'], dict):
        segments = match['segments']
        seg_prefix = f"{prefix}.segments"

        # Required segments
        errors.extend(validate_timestamp_block(
            segments.get('studio_intro'), f'{seg_prefix}.studio_intro', required=True
        ))
        errors.extend(validate_timestamp_block(
            segments.get('highlights'), f'{seg_prefix}.highlights', required=True
        ))

        # Optional segments
        for seg in ['lineups', 'post_match_interviews', 'studio_analysis']:
            if seg in segments:
                errors.extend(validate_timestamp_block(segments[seg], f'{seg_prefix}.{seg}'))
    else:
        errors.append(f"{prefix}.segments: expected object")

    # Optional: notes (string or null)
    if 'notes' in match and match['notes'] is not None:
        if not isinstance(match['notes'], str):
            errors.append(f"{prefix}.notes: expected string or null")

    return errors


def validate_analysis(data: Any) -> list[str]:
    """Validate a complete analysis JSON structure."""
    errors = []

    if not isinstance(data, dict):
        errors.append("root: expected JSON object")
        return errors

    # Validate episode section
    if 'episode' not in data:
        errors.append("episode: missing required field")
    else:
        errors.extend(validate_episode(data['episode']))

    # Validate matches section
    if 'matches' not in data:
        errors.append("matches: missing required field")
    elif not isinstance(data['matches'], list):
        errors.append("matches: expected array")
    elif len(data['matches']) == 0:
        errors.append("matches: array is empty (expected at least one match)")
    else:
        for i, match in enumerate(data['matches']):
            errors.extend(validate_match(match, i))

        # Check order values are sequential starting from 1
        orders = [m.get('order') for m in data['matches'] if isinstance(m.get('order'), int)]
        expected_orders = list(range(1, len(orders) + 1))
        if sorted(orders) != expected_orders:
            errors.append(f"matches: order values should be sequential 1..N, got {sorted(orders)}")

    return errors


def load_and_validate(file_path: Path) -> tuple[bool, list[str]]:
    """Load a JSON file and validate it."""
    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except OSError as e:
        return False, [f"Cannot read file: {e}"]

    errors = validate_analysis(data)
    return len(errors) == 0, errors


def get_all_episodes(analysis_dir: Path) -> list[str]:
    """Get all episode IDs from the analysis directory structure."""
    episodes = []
    for path in sorted(analysis_dir.iterdir()):
        if path.is_dir() and path.name.startswith('motd_'):
            episodes.append(path.name)
    return episodes


def list_status(analysis_dir: Path) -> None:
    """List status of all episodes."""
    episodes = get_all_episodes(analysis_dir)

    print("Episode Analysis Status")
    print("=" * 70)

    valid_count = 0
    invalid_count = 0
    missing_count = 0

    for episode_id in episodes:
        analysis_path = analysis_dir / episode_id / 'analysis.json'

        if not analysis_path.exists():
            status = "[ ] Missing"
            missing_count += 1
        else:
            is_valid, errors = load_and_validate(analysis_path)
            if is_valid:
                status = "[✓] Valid"
                valid_count += 1
            else:
                status = f"[✗] Invalid ({len(errors)} errors)"
                invalid_count += 1

        print(f"  {status:20} {episode_id}")

    print("=" * 70)
    print(f"Total: {len(episodes)} episodes")
    print(f"  Valid:   {valid_count}")
    print(f"  Invalid: {invalid_count}")
    print(f"  Missing: {missing_count}")


def validate_single(episode_id: str, analysis_dir: Path) -> bool:
    """Validate a single episode's analysis file."""
    analysis_path = analysis_dir / episode_id / 'analysis.json'

    print(f"Validating {episode_id}")
    print("=" * 60)

    if not analysis_path.exists():
        print(f"✗ File not found: {analysis_path}")
        return False

    is_valid, errors = load_and_validate(analysis_path)

    if is_valid:
        print("✓ Valid - all schema checks passed")
        return True
    else:
        print(f"✗ Invalid - {len(errors)} error(s):\n")
        for error in errors:
            print(f"  - {error}")
        return False


def validate_all(analysis_dir: Path) -> bool:
    """Validate all episodes with analysis files."""
    episodes = get_all_episodes(analysis_dir)

    print("Validating All Episodes")
    print("=" * 70)

    all_valid = True
    results = []

    for episode_id in episodes:
        analysis_path = analysis_dir / episode_id / 'analysis.json'

        if not analysis_path.exists():
            results.append((episode_id, None, ["File not found"]))
            continue

        is_valid, errors = load_and_validate(analysis_path)
        results.append((episode_id, is_valid, errors))
        if not is_valid:
            all_valid = False

    # Print summary
    for episode_id, is_valid, errors in results:
        if is_valid is None:
            print(f"  [ ] {episode_id} - not yet analysed")
        elif is_valid:
            print(f"  [✓] {episode_id}")
        else:
            print(f"  [✗] {episode_id} - {len(errors)} error(s)")

    print("=" * 70)

    # Print detailed errors for invalid files
    invalid_results = [(ep, errs) for ep, valid, errs in results if valid is False]
    if invalid_results:
        print("\nDetailed Errors:")
        print("-" * 70)
        for episode_id, errors in invalid_results:
            print(f"\n{episode_id}:")
            for error in errors:
                print(f"  - {error}")

    return all_valid


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate LLM analysis JSON files against schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'episode_id',
        nargs='?',
        help='Episode ID to validate (e.g., motd_2025-26_2025-11-22)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List status of all episodes'
    )

    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    analysis_dir = project_root / 'data' / 'analysis'

    if not analysis_dir.exists():
        print(f"Error: Analysis directory not found: {analysis_dir}")
        sys.exit(1)

    # List mode
    if args.list:
        list_status(analysis_dir)
        sys.exit(0)

    # Single episode mode
    if args.episode_id:
        success = validate_single(args.episode_id, analysis_dir)
        sys.exit(0 if success else 1)

    # Default: validate all
    success = validate_all(analysis_dir)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
