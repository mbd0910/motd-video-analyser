#!/usr/bin/env python3
"""
Visualize OCR regions overlaid on FT graphic frames for verification.

This script helps verify that the calculated 720p OCR region coordinates
correctly capture the FT score graphics before updating config.yaml.
"""

import cv2
import sys
from pathlib import Path

# Final 720p OCR regions (calibrated for MOTD 2025-26 season)
OCR_REGIONS_720P = {
    'ft_score': {
        'x': 157,
        'y': 545,
        'width': 966,
        'height': 140,
        'color': (0, 255, 0),  # Green
        'label': 'FT Score'
    },
    'scoreboard': {
        'x': 0,
        'y': 0,
        'width': 350,
        'height': 70,
        'color': (255, 0, 0),  # Blue
        'label': 'Scoreboard'
    },
    'formation': {
        'x': 533,
        'y': 400,
        'width': 747,
        'height': 320,
        'color': (0, 0, 255),  # Red
        'label': 'Formation'
    }
}

# All 7 FT graphic frames from cache
FT_FRAMES = [
    'frame_0202_scene_change_611.0s.jpg',   # Liverpool vs Villa
    'frame_0398_scene_change_1329.2s.jpg',  # Burnley vs Arsenal
    'frame_0627_scene_change_2124.2s.jpg',  # Forest vs Man Utd
    'frame_0835_scene_change_2886.2s.jpg',  # Fulham vs Wolves
    'frame_1054_scene_change_3649.2s.jpg',  # Spurs vs Chelsea
    'frame_1232_scene_change_4303.7s.jpg',  # Brighton vs Leeds
    'frame_1394_interval_sampling_4845.0s.jpg'  # Palace vs Brentford
]


def draw_regions(image_path: Path, output_path: Path | None = None) -> None:
    """Draw OCR regions on frame and save/display result."""
    # Read image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: Could not read {image_path}")
        return

    height, width = img.shape[:2]
    print(f"\n{image_path.name}")
    print(f"Resolution: {width}x{height}")

    # Draw each region
    for region_name, region in OCR_REGIONS_720P.items():
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        color = region['color']
        label = region['label']

        # Verify region is within bounds
        if x + w > width or y + h > height:
            print(f"  ⚠️  {label}: OUT OF BOUNDS ({x},{y},{w},{h})")
            continue

        # Draw rectangle
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

        # Draw label background
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        cv2.rectangle(img, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)

        # Draw label text
        cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                   0.6, (255, 255, 255), 2)

        print(f"  ✓ {label}: ({x}, {y}, {w}, {h})")

    # Save or display
    if output_path:
        cv2.imwrite(str(output_path), img)
        print(f"  Saved: {output_path}")
    else:
        # Display (requires GUI)
        cv2.imshow(f'OCR Regions - {image_path.name}', img)
        print("  Press any key to continue...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def main():
    """Process all FT frames or a specific one."""
    cache_dir = Path('data/cache/motd_2025-26_2025-11-01/frames')
    output_dir = Path('data/cache/motd_2025-26_2025-11-01/ocr_region_visualization')

    if not cache_dir.exists():
        print(f"Error: Cache directory not found: {cache_dir}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Process all FT frames
    print("Visualizing OCR regions on all 7 FT graphic frames...")
    print("=" * 60)

    for frame_name in FT_FRAMES:
        frame_path = cache_dir / frame_name
        if not frame_path.exists():
            print(f"⚠️  Frame not found: {frame_name}")
            continue

        output_path = output_dir / f"regions_{frame_name}"
        draw_regions(frame_path, output_path)

    print("\n" + "=" * 60)
    print(f"All visualizations saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Open the visualization images to verify regions")
    print("2. Check that ft_score region captures the full-time score box")
    print("3. If regions look correct, proceed with config update")


if __name__ == '__main__':
    main()
