#!/usr/bin/env python3
"""Debug fixture matcher for a given episode.

This script helps verify fixture data when adding new episodes or debugging
fixture matching issues.

Usage:
    python scripts/debug_fixtures.py <episode_id>
    python scripts/debug_fixtures.py --list
    python scripts/debug_fixtures.py motd_2025-26_2025-11-01

Examples:
    # List all episodes in manifest
    python scripts/debug_fixtures.py --list

    # Show fixtures for specific episode
    python scripts/debug_fixtures.py motd_2025-26_2025-11-01

    # Test team validation for episode
    python scripts/debug_fixtures.py motd_2025-26_2025-11-08 --validate "Liverpool,Arsenal"
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motd.ocr.fixture_matcher import FixtureMatcher


def load_manifest(manifest_path: Path) -> dict:
    """Load episode manifest."""
    with open(manifest_path) as f:
        return json.load(f)


def list_episodes(manifest_path: Path) -> None:
    """List all episodes in manifest."""
    manifest = load_manifest(manifest_path)

    print("Available Episodes")
    print("=" * 60)

    for episode in manifest.get('episodes', []):
        episode_id = episode.get('episode_id', 'unknown')
        broadcast_date = episode.get('broadcast_date', 'unknown')
        match_count = len(episode.get('matches', []))
        print(f"  {episode_id} ({broadcast_date}) - {match_count} matches")

    print("=" * 60)
    print(f"Total: {len(manifest.get('episodes', []))} episodes")


def show_fixtures(matcher: FixtureMatcher, episode_id: str) -> None:
    """Show expected fixtures for an episode."""
    print(f"Expected Fixtures for {episode_id}")
    print("=" * 60)

    try:
        fixtures = matcher.get_expected_fixtures(episode_id)
    except ValueError as e:
        print(f"Error: {e}")
        return

    if not fixtures:
        print("No fixtures found for this episode.")
        print("Check that the episode_id matches the manifest.")
        return

    print(f"Found {len(fixtures)} expected matches:\n")

    for i, fixture in enumerate(fixtures, 1):
        home = fixture.get('home_team', 'Unknown')
        away = fixture.get('away_team', 'Unknown')
        match_id = fixture.get('match_id', 'N/A')
        score = fixture.get('score', 'N/A')

        print(f"{i}. {home} vs {away}")
        print(f"   Match ID: {match_id}")
        print(f"   Score: {score}")
        print()

    # Also show flat team list
    print("-" * 60)
    print("Expected Teams (for OCR matching):")
    print("-" * 60)

    teams = matcher.get_expected_teams(episode_id)
    for team in sorted(teams):
        print(f"  - {team}")


def validate_teams(matcher: FixtureMatcher, episode_id: str, teams_str: str) -> None:
    """Validate detected teams against episode fixtures."""
    teams = [t.strip() for t in teams_str.split(',')]

    print(f"Validating Teams for {episode_id}")
    print("=" * 60)
    print(f"Input teams: {teams}\n")

    validation = matcher.validate_teams(teams, episode_id)

    print(f"Validated teams: {validation['validated_teams']}")
    print(f"Unexpected teams: {validation['unexpected_teams']}")
    print(f"Confidence boost: {validation['confidence_boost']}")

    if validation['validated_teams'] and not validation['unexpected_teams']:
        print("\n✓ All teams validated successfully!")
    elif validation['unexpected_teams']:
        print(f"\n⚠ Warning: Unexpected teams: {validation['unexpected_teams']}")
        print("  These teams are not in the episode manifest.")
    else:
        print("\n✗ No teams validated")

    # Try to identify fixture if exactly 2 teams
    if len(teams) == 2:
        print("\n" + "-" * 60)
        print("Fixture Identification:")
        print("-" * 60)

        fixture = matcher.identify_fixture(teams[0], teams[1], episode_id)
        if fixture:
            print(f"✓ Match found: {fixture['home_team']} vs {fixture['away_team']}")
            print(f"  Match ID: {fixture['match_id']}")
            print(f"  Score: {fixture.get('score', 'N/A')}")
        else:
            print("✗ No fixture found for this team pairing")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Debug fixture matcher for MOTD episodes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'episode_id',
        nargs='?',
        help='Episode ID (e.g., motd_2025-26_2025-11-01)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all episodes in manifest'
    )
    parser.add_argument(
        '--validate',
        metavar='TEAMS',
        help='Validate comma-separated teams (e.g., "Liverpool,Arsenal")'
    )

    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    fixtures_path = project_root / 'data' / 'fixtures' / 'premier_league_2025_26.json'
    manifest_path = project_root / 'data' / 'episodes' / 'episode_manifest.json'

    # Check files exist
    if not fixtures_path.exists():
        print(f"Error: Fixtures file not found: {fixtures_path}")
        sys.exit(1)
    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}")
        sys.exit(1)

    # List mode
    if args.list:
        list_episodes(manifest_path)
        return

    # Need episode_id for other operations
    if not args.episode_id:
        parser.print_help()
        print("\nError: episode_id required (or use --list)")
        sys.exit(1)

    # Initialise matcher
    matcher = FixtureMatcher(fixtures_path, manifest_path)

    # Validate mode
    if args.validate:
        validate_teams(matcher, args.episode_id, args.validate)
        return

    # Default: show fixtures
    show_fixtures(matcher, args.episode_id)


if __name__ == '__main__':
    main()
