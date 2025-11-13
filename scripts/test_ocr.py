"""Manual test script for OCR reader."""

import yaml
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.motd.ocr.reader import OCRReader


def main():
    """Test OCR reader on sample frames from Task 009a reconnaissance."""
    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Initialise reader
    print("Initialising OCR reader...")
    reader = OCRReader(config['ocr'])
    print(f"✓ OCR reader initialised (GPU: {config['ocr'].get('gpu', True)})\n")

    # Test frames from 009a documentation
    # These are the key frames identified during reconnaissance
    cache_dir = Path(__file__).parent.parent / 'data' / 'cache' / 'motd_2025-26_2025-11-01' / 'frames'

    test_frames = [
        # Full-time score graphics (PRIMARY target, 90-95% expected accuracy)
        ('scene_219.jpg', 'FT score (Match 1: Liverpool vs Brentford)'),
        ('scene_312.jpg', 'FT score (Match 2: Brighton vs Man United)'),
        ('scene_401.jpg', 'FT score (Match 3: Newcastle vs Arsenal)'),

        # Live scoreboards (SECONDARY target, 75-85% expected accuracy)
        ('scene_154.jpg', 'Live scoreboard (Match 1)'),
        ('scene_277.jpg', 'Live scoreboard (Match 2)'),
    ]

    for frame_filename, description in test_frames:
        frame_path = cache_dir / frame_filename

        if not frame_path.exists():
            print(f"⚠ SKIP: {frame_filename} - File not found")
            print(f"   Expected: {frame_path}\n")
            continue

        print(f"{'='*70}")
        print(f"Testing: {frame_filename}")
        print(f"Description: {description}")
        print(f"{'='*70}")

        try:
            # Extract from all regions using multi-tiered strategy
            result = reader.extract_with_fallback(frame_path)

            print(f"\nPrimary source: {result['primary_source']}")

            if result['results']:
                print(f"\n✓ Extracted {len(result['results'])} text items:")
                for item in result['results']:
                    if 'error' in item:
                        print(f"  ✗ Error: {item['error']}")
                    else:
                        print(f"  • Text: {item['text']}")
                        print(f"    Confidence: {item['confidence']:.2f}")
                        print(f"    Region: {item['region']}")
            else:
                print("\n✗ No text extracted from primary regions")

            # Show all regions for debugging
            print("\nAll regions:")
            for region_name, region_results in result['all_regions'].items():
                if region_results and not any('error' in r for r in region_results):
                    print(f"  {region_name}: {len(region_results)} items")
                elif region_results and any('error' in r for r in region_results):
                    print(f"  {region_name}: ERROR")
                else:
                    print(f"  {region_name}: empty")

        except Exception as e:
            print(f"\n✗ ERROR: {e}")

        print()

    print(f"{'='*70}")
    print("Test complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
