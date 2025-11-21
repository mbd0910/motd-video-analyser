#!/usr/bin/env python3
"""Debug OCR on a single frame to investigate detection failures.

Usage:
    python scripts/debug_ocr_frame.py <frame_path> [--episode-id <id>]

Example:
    python scripts/debug_ocr_frame.py \
        data/cache/motd_2025-26_2025-11-08/frames/frame_0834_scene_change_1579.6.jpg \
        --episode-id motd_2025-26_2025-11-08
"""

import sys
import argparse
from pathlib import Path
import json
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motd.ocr.reader import OCRReader
from motd.ocr.team_matcher import TeamMatcher
import cv2


def load_config(config_path: Path = Path("config/config.yaml")) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        print(f"Warning: Config file not found at {config_path}")
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


def visualize_ocr_regions(frame_path: Path, config: dict, ocr_results: list) -> Path:
    """
    Draw OCR bounding boxes on the frame for visual inspection.

    Args:
        frame_path: Path to the frame image
        config: OCR configuration with region definitions
        ocr_results: List of OCR results with bboxes

    Returns:
        Path to the annotated image
    """
    # Load frame
    frame = cv2.imread(str(frame_path))

    # Draw FT score region
    region = config['ocr']['regions']['ft_score']
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(frame, 'ft_score', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Draw OCR bounding boxes
    for result in ocr_results:
        if 'bbox' in result:
            bbox = result['bbox']
            # Convert bbox to cv2 format (bbox is relative to region, need to offset)
            pts = [(int(pt[0]) + x, int(pt[1]) + y) for pt in bbox]
            for i in range(len(pts)):
                cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 0, 255), 2)

    # Save annotated frame
    output_path = frame_path.parent / f"{frame_path.stem}_debug.jpg"
    cv2.imwrite(str(output_path), frame)
    return output_path


def debug_frame(frame_path: str, episode_id: str = None):
    """Debug OCR extraction on a single frame."""
    frame_path = Path(frame_path)

    if not frame_path.exists():
        print(f"❌ Error: Frame not found: {frame_path}")
        sys.exit(1)

    print(f"🔍 Debugging OCR on frame: {frame_path.name}")
    print("=" * 80)

    # Load config
    config = load_config()

    # Initialize OCR reader
    print("\n📖 Initializing OCR reader...")
    reader = OCRReader(config['ocr'])

    # Initialize team matcher (optional, for advanced debugging)
    matcher = None
    expected_teams = []
    if episode_id:
        try:
            print(f"🏟️  Loading team matcher...")
            teams_path = Path(config['teams']['path'])
            matcher = TeamMatcher(teams_path)
            print(f"   ✅ Team matcher initialized")
        except Exception as e:
            print(f"   ⚠️  Could not load team matcher: {e}")
            print(f"   Continuing without team matching...")

    # Extract FT score region
    print("\n🎯 Extracting FT score region...")
    print(f"   Region coordinates: x={config['ocr']['regions']['ft_score']['x']}, "
          f"y={config['ocr']['regions']['ft_score']['y']}, "
          f"w={config['ocr']['regions']['ft_score']['width']}, "
          f"h={config['ocr']['regions']['ft_score']['height']}")
    print(f"   Confidence threshold: {config['ocr']['confidence_threshold']}")

    # Get raw OCR results (before confidence filtering)
    ft_region = config['ocr']['regions']['ft_score']
    x, y, w, h = ft_region['x'], ft_region['y'], ft_region['width'], ft_region['height']

    frame = cv2.imread(str(frame_path))
    cropped = frame[y:y+h, x:x+w]

    print("\n🤖 Running EasyOCR...")
    raw_results = reader.reader.readtext(cropped)

    print(f"\n📊 Raw OCR Results (ALL detections, before confidence filtering):")
    print(f"   Total detections: {len(raw_results)}")
    print()

    for i, (bbox, text, conf) in enumerate(raw_results, 1):
        status = "✅ PASS" if conf >= config['ocr']['confidence_threshold'] else "❌ REJECT"
        print(f"   {i}. '{text}'")
        print(f"      Confidence: {conf:.4f} ({status})")
        print(f"      BBox: {bbox}")
        print()

    # Get filtered results (what the pipeline actually uses)
    filtered_results = reader.extract_ft_score(frame_path)

    print(f"\n✨ Filtered Results (confidence >= {config['ocr']['confidence_threshold']}):")
    print(f"   Accepted: {len(filtered_results)}/{len(raw_results)} detections")
    print()

    for result in filtered_results:
        print(f"   • '{result['text']}' (confidence: {result['confidence']:.4f})")

    # Team matching and FT validation
    if matcher and filtered_results:
        print(f"\n🔍 Team Matching:")
        all_text = ' '.join([r['text'] for r in filtered_results])
        print(f"   Combined text: '{all_text}'")
        print()

        # Simple fuzzy matching for debugging
        print("   🔬 Trying fuzzy matching on each OCR text individually...")
        from rapidfuzz import fuzz

        # Load teams manually
        import json
        with open(config['teams']['path']) as f:
            teams_data = json.load(f)
            all_teams = [t['full'] for t in teams_data['teams']]

        matched_team_names = []
        for result in filtered_results:
            text = result['text']
            print(f"\n      Text: '{text}'")

            # Find best matches
            matches = []
            for team in all_teams:
                ratio = fuzz.partial_ratio(text.lower(), team.lower())
                if ratio >= 70:  # Lower threshold for debugging
                    matches.append((team, ratio))

            matches.sort(key=lambda x: x[1], reverse=True)
            if matches:
                print(f"      Possible matches:")
                for team, ratio in matches[:3]:
                    print(f"         - {team} ({ratio}%)")
                    if ratio >= 85:  # High confidence match
                        matched_team_names.append(team)
            else:
                print(f"      No fuzzy matches found (threshold: 70%)")

        # FT validation
        print(f"\n🎯 FT Graphic Validation:")
        is_valid = reader.validate_ft_graphic(filtered_results, matched_team_names)

        if is_valid:
            print(f"   ✅ VALID FT graphic")
        else:
            print(f"   ❌ INVALID FT graphic")

            # Show why it failed
            import re
            all_text_upper = ' '.join([r.get('text', '').upper() for r in filtered_results])

            score_pattern = r'\b\d+\s*[-–—|]?\s*\d+\b'
            has_score = bool(re.search(score_pattern, all_text_upper))

            ft_indicators = ['FT', 'FULL TIME', 'FULL-TIME', 'FULLTIME']
            has_ft = any(indicator in all_text_upper for indicator in ft_indicators)

            print(f"\n   Validation checks:")
            print(f"      Teams detected: {len(matched_team_names)} (need ≥1) {'✅' if len(matched_team_names) >= 1 else '❌'}")
            print(f"      Score pattern: {has_score} {'✅' if has_score else '❌'}")
            print(f"      FT text: {has_ft} {'✅' if has_ft else '❌'}")
    elif filtered_results:
        # No matcher, just do FT validation with empty team list
        print(f"\n🎯 FT Graphic Validation (no team matching):")
        import re
        all_text_upper = ' '.join([r.get('text', '').upper() for r in filtered_results])

        score_pattern = r'\b\d+\s*[-–—|]?\s*\d+\b'
        has_score = bool(re.search(score_pattern, all_text_upper))

        ft_indicators = ['FT', 'FULL TIME', 'FULL-TIME', 'FULLTIME']
        has_ft = any(indicator in all_text_upper for indicator in ft_indicators)

        print(f"   Validation checks:")
        print(f"      Score pattern: {has_score} {'✅' if has_score else '❌'}")
        print(f"      FT text: {has_ft} {'✅' if has_ft else '❌'}")

    # Visualize regions
    print(f"\n🎨 Generating annotated image...")
    annotated_path = visualize_ocr_regions(frame_path, config, filtered_results)
    print(f"   Saved to: {annotated_path}")

    print("\n" + "=" * 80)
    print("✅ Debug complete")


def main():
    parser = argparse.ArgumentParser(
        description="Debug OCR extraction on a single frame"
    )
    parser.add_argument(
        'frame_path',
        help='Path to frame image'
    )
    parser.add_argument(
        '--episode-id',
        help='Episode ID to load expected teams from fixtures (optional)'
    )

    args = parser.parse_args()
    debug_frame(args.frame_path, args.episode_id)


if __name__ == '__main__':
    main()
