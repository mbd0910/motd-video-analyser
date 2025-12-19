#!/usr/bin/env python3
"""Debug OCR region extraction on a single frame.

This script helps verify that OCR regions from config.yaml correctly
capture the expected areas of video frames. Useful when:
- BBC changes video resolution
- Calibrating OCR regions for new episodes
- Debugging OCR detection failures

Usage:
    python scripts/debug_ocr_region.py <frame_path>
    python scripts/debug_ocr_region.py <frame_path> --region ft_score
    python scripts/debug_ocr_region.py <frame_path> --save
    python scripts/debug_ocr_region.py <frame_path> --ocr

Examples:
    # Extract all regions from a frame
    python scripts/debug_ocr_region.py data/cache/motd_2025-26_2025-11-01/frames/frame_0627.jpg

    # Extract specific region
    python scripts/debug_ocr_region.py frame.jpg --region ft_score

    # Save extracted regions to files
    python scripts/debug_ocr_region.py frame.jpg --save

    # Run OCR on extracted regions
    python scripts/debug_ocr_region.py frame.jpg --ocr
"""

import argparse
import sys
from pathlib import Path

import cv2
import yaml


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def extract_region(img, region: dict, name: str) -> tuple:
    """Extract a region from an image.

    Returns:
        Tuple of (cropped_image, success, message)
    """
    height, width = img.shape[:2]

    x = region['x']
    y = region['y']
    w = region['width']
    h = region['height']

    # Check bounds
    if x + w > width or y + h > height:
        return None, False, f"Region out of bounds: ({x},{y},{w},{h}) vs frame ({width}x{height})"

    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return None, False, f"Invalid region coordinates: ({x},{y},{w},{h})"

    # Extract
    cropped = img[y:y+h, x:x+w]

    if cropped.size == 0:
        return None, False, "Extracted region is empty"

    return cropped, True, f"Extracted {w}x{h} region"


def run_ocr(region_img, region_name: str) -> None:
    """Run EasyOCR on a region image."""
    try:
        import easyocr
    except ImportError:
        print("  EasyOCR not installed - skipping OCR test")
        return

    print(f"  Running OCR on {region_name}...")

    try:
        reader = easyocr.Reader(['en'], gpu=True, verbose=False)
        results = reader.readtext(region_img)

        if not results:
            print("    No text detected")
            return

        print(f"    Detected {len(results)} text elements:")
        for bbox, text, confidence in results:
            print(f"      '{text}' (confidence: {confidence:.2f})")

    except Exception as e:
        print(f"    OCR error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Debug OCR region extraction on video frames',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'frame_path',
        help='Path to frame image file'
    )
    parser.add_argument(
        '--region',
        choices=['ft_score', 'scoreboard', 'formation', 'all'],
        default='all',
        help='Region to extract (default: all)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save extracted regions to files'
    )
    parser.add_argument(
        '--ocr',
        action='store_true',
        help='Run EasyOCR on extracted regions'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/config.yaml'),
        help='Path to config file (default: config/config.yaml)'
    )

    args = parser.parse_args()

    # Load frame
    frame_path = Path(args.frame_path)
    if not frame_path.exists():
        print(f"Error: Frame not found: {frame_path}")
        sys.exit(1)

    img = cv2.imread(str(frame_path))
    if img is None:
        print(f"Error: Could not read frame: {frame_path}")
        sys.exit(1)

    height, width = img.shape[:2]
    print(f"Frame: {frame_path.name}")
    print(f"Resolution: {width}x{height}")
    print("=" * 60)

    # Load config
    config = load_config(args.config)
    regions = config.get('ocr', {}).get('regions', {})

    if not regions:
        print("Error: No OCR regions defined in config")
        sys.exit(1)

    # Determine which regions to process
    if args.region == 'all':
        region_names = list(regions.keys())
    else:
        if args.region not in regions:
            print(f"Error: Region '{args.region}' not found in config")
            print(f"Available regions: {list(regions.keys())}")
            sys.exit(1)
        region_names = [args.region]

    # Process each region
    for region_name in region_names:
        region = regions[region_name]
        print(f"\n{region_name}:")
        print(f"  Config: x={region['x']}, y={region['y']}, w={region['width']}, h={region['height']}")

        cropped, success, message = extract_region(img, region, region_name)

        if not success:
            print(f"  Error: {message}")
            continue

        print(f"  {message}")

        # Save if requested
        if args.save:
            output_dir = frame_path.parent
            output_name = f"{frame_path.stem}_{region_name}{frame_path.suffix}"
            output_path = output_dir / output_name
            cv2.imwrite(str(output_path), cropped)
            print(f"  Saved: {output_path}")

        # OCR if requested
        if args.ocr:
            run_ocr(cropped, region_name)

    print("\n" + "=" * 60)
    print("Done")


if __name__ == '__main__':
    main()
