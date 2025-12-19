#!/usr/bin/env python3
"""Visualise OCR regions overlaid on video frames.

This script draws coloured boxes on frames to show where OCR regions
are configured. Useful for:
- Verifying OCR region calibration
- Checking if regions capture expected graphics
- Debugging OCR detection issues

Usage:
    python scripts/visualize_regions.py <frame_path>
    python scripts/visualize_regions.py <frame_path> --output annotated.jpg
    python scripts/visualize_regions.py --episode <episode_id>

Examples:
    # Annotate a single frame
    python scripts/visualize_regions.py frame.jpg

    # Save annotated frame to specific path
    python scripts/visualize_regions.py frame.jpg --output /tmp/annotated.jpg

    # Batch process all frames for an episode
    python scripts/visualize_regions.py --episode motd_2025-26_2025-11-01

    # Process specific frames from an episode
    python scripts/visualize_regions.py --episode motd_2025-26_2025-11-01 --limit 10
"""

import argparse
import sys
from pathlib import Path

import cv2
import yaml


# Colours for each region type (BGR format)
REGION_COLOURS = {
    'ft_score': (0, 255, 0),      # Green
    'scoreboard': (255, 0, 0),    # Blue
    'formation': (0, 0, 255),     # Red
}


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def draw_regions(img, regions: dict) -> tuple:
    """Draw OCR regions on an image.

    Returns:
        Tuple of (annotated_image, results_list)
    """
    height, width = img.shape[:2]
    annotated = img.copy()
    results = []

    for region_name, region in regions.items():
        x = region['x']
        y = region['y']
        w = region['width']
        h = region['height']

        # Get colour for this region type
        colour = REGION_COLOURS.get(region_name, (255, 255, 255))

        # Check bounds
        if x + w > width or y + h > height:
            results.append((region_name, False, f"Out of bounds: ({x},{y},{w},{h}) vs ({width}x{height})"))
            continue

        # Draw rectangle
        cv2.rectangle(annotated, (x, y), (x + w, y + h), colour, 2)

        # Draw label with background
        label = region_name.replace('_', ' ').title()
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Label background
        cv2.rectangle(
            annotated,
            (x, y - label_h - 10),
            (x + label_w + 4, y),
            colour,
            -1
        )

        # Label text
        cv2.putText(
            annotated,
            label,
            (x + 2, y - 5),
            font,
            font_scale,
            (255, 255, 255),
            thickness
        )

        results.append((region_name, True, f"({x},{y},{w},{h})"))

    return annotated, results


def process_frame(
    frame_path: Path,
    regions: dict,
    output_path: Path | None = None,
    verbose: bool = True
) -> bool:
    """Process a single frame.

    Returns:
        True if successful, False otherwise
    """
    # Load frame
    img = cv2.imread(str(frame_path))
    if img is None:
        if verbose:
            print(f"Error: Could not read {frame_path}")
        return False

    height, width = img.shape[:2]

    if verbose:
        print(f"\n{frame_path.name}")
        print(f"  Resolution: {width}x{height}")

    # Draw regions
    annotated, results = draw_regions(img, regions)

    # Print results
    if verbose:
        for region_name, success, message in results:
            status = "OK" if success else "ERROR"
            print(f"  {region_name}: [{status}] {message}")

    # Determine output path
    if output_path is None:
        output_dir = frame_path.parent
        output_name = f"regions_{frame_path.name}"
        output_path = output_dir / output_name

    # Save annotated frame
    cv2.imwrite(str(output_path), annotated)

    if verbose:
        print(f"  Saved: {output_path}")

    return True


def process_episode(
    episode_id: str,
    regions: dict,
    cache_dir: Path,
    limit: int | None = None,
    verbose: bool = True
) -> None:
    """Process all frames for an episode."""
    frames_dir = cache_dir / episode_id / 'frames'

    if not frames_dir.exists():
        print(f"Error: Frames directory not found: {frames_dir}")
        sys.exit(1)

    # Get all frame files
    frame_files = sorted(frames_dir.glob('frame_*.jpg'))

    if not frame_files:
        print(f"Error: No frames found in {frames_dir}")
        sys.exit(1)

    if limit:
        frame_files = frame_files[:limit]

    # Create output directory
    output_dir = frames_dir.parent / 'ocr_region_visualization'
    output_dir.mkdir(exist_ok=True)

    print(f"Processing {len(frame_files)} frames for {episode_id}...")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    success_count = 0
    for frame_path in frame_files:
        output_path = output_dir / f"regions_{frame_path.name}"
        if process_frame(frame_path, regions, output_path, verbose=verbose):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"Processed {success_count}/{len(frame_files)} frames")
    print(f"Output saved to: {output_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualise OCR regions on video frames',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'frame_path',
        nargs='?',
        help='Path to frame image file'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output path for annotated frame'
    )
    parser.add_argument(
        '--episode',
        metavar='EPISODE_ID',
        help='Process all frames for an episode (batch mode)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of frames to process (with --episode)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress per-frame output'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/config.yaml'),
        help='Path to config file (default: config/config.yaml)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.frame_path and not args.episode:
        parser.print_help()
        print("\nError: Either frame_path or --episode required")
        sys.exit(1)

    # Load config
    config = load_config(args.config)
    regions = config.get('ocr', {}).get('regions', {})

    if not regions:
        print("Error: No OCR regions defined in config")
        sys.exit(1)

    # Batch mode: process episode
    if args.episode:
        cache_dir = Path(config.get('cache', {}).get('directory', 'data/cache'))
        process_episode(
            args.episode,
            regions,
            cache_dir,
            limit=args.limit,
            verbose=not args.quiet
        )
        return

    # Single frame mode
    frame_path = Path(args.frame_path)
    if not frame_path.exists():
        print(f"Error: Frame not found: {frame_path}")
        sys.exit(1)

    print("Visualising OCR Regions")
    print("=" * 60)

    process_frame(frame_path, regions, args.output, verbose=True)

    print("\n" + "=" * 60)
    print("Done")


if __name__ == '__main__':
    main()
