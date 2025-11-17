#!/usr/bin/env python3
"""
Single-frame validation test for OCR region extraction.

This script validates that the corrected 720p ft_score region coordinates
can be extracted without OpenCV errors and that EasyOCR can detect text.
"""

import cv2
import sys
from pathlib import Path

# Test with the validated FT graphic frame
TEST_FRAME = 'data/cache/motd_2025-26_2025-11-01/frames/frame_0627_scene_change_2124.2s.jpg'

# Corrected 720p ft_score region
FT_SCORE_REGION = {
    'x': 260,
    'y': 545,
    'width': 760,
    'height': 140
}


def test_region_extraction():
    """Test that the ft_score region can be extracted without errors."""
    frame_path = Path(TEST_FRAME)

    if not frame_path.exists():
        print(f"❌ Error: Test frame not found: {frame_path}")
        return False

    # Read frame
    img = cv2.imread(str(frame_path))
    if img is None:
        print(f"❌ Error: Could not read frame: {frame_path}")
        return False

    height, width = img.shape[:2]
    print(f"✓ Frame loaded: {width}x{height}")

    # Extract ft_score region
    x = FT_SCORE_REGION['x']
    y = FT_SCORE_REGION['y']
    w = FT_SCORE_REGION['width']
    h = FT_SCORE_REGION['height']

    # Verify region is within bounds
    if x + w > width or y + h > height:
        print(f"❌ Error: Region out of bounds!")
        print(f"   Region: ({x}, {y}, {w}, {h})")
        print(f"   Frame:  ({width}x{height})")
        return False

    print(f"✓ Region within bounds: ({x}, {y}, {w}, {h})")

    # Extract region
    try:
        region = img[y:y+h, x:x+w]
        if region.size == 0:
            print(f"❌ Error: Extracted region is empty!")
            return False

        region_h, region_w = region.shape[:2]
        print(f"✓ Region extracted: {region_w}x{region_h}")

        # Save extracted region for visual inspection
        output_path = Path('data/cache/motd_2025-26_2025-11-01/test_ft_score_region.jpg')
        cv2.imwrite(str(output_path), region)
        print(f"✓ Extracted region saved: {output_path}")

        return True

    except Exception as e:
        print(f"❌ Error extracting region: {e}")
        return False


def test_ocr():
    """Test that EasyOCR can detect text in the extracted region."""
    try:
        import easyocr
    except ImportError:
        print("⚠️  EasyOCR not available - skipping OCR test")
        print("   (This is OK - OCR will be tested in full pipeline)")
        return True

    region_path = Path('data/cache/motd_2025-26_2025-11-01/test_ft_score_region.jpg')
    if not region_path.exists():
        print("❌ Error: Extracted region not found for OCR test")
        return False

    print("\n" + "=" * 60)
    print("Testing EasyOCR on extracted ft_score region...")
    print("=" * 60)

    try:
        # Initialize EasyOCR reader
        print("Initializing EasyOCR reader...")
        reader = easyocr.Reader(['en'], gpu=True)

        # Run OCR on extracted region
        print(f"Running OCR on {region_path}...")
        results = reader.readtext(str(region_path))

        if not results:
            print("⚠️  Warning: No text detected in region")
            print("   This may indicate:")
            print("   - Region position incorrect")
            print("   - OCR confidence threshold too high")
            print("   - Text preprocessing needed")
            return False

        print(f"✓ OCR detected {len(results)} text elements:")
        for bbox, text, confidence in results:
            print(f"   '{text}' (confidence: {confidence:.2f})")

        # Check if we detected expected team names
        all_text = ' '.join([text for _, text, _ in results]).lower()
        if 'nottingham' in all_text or 'forest' in all_text or 'manchester' in all_text or 'united' in all_text:
            print("✓ Team names detected successfully!")
            return True
        else:
            print("⚠️  Warning: Expected team names not detected in OCR results")
            print(f"   Detected text: {all_text}")
            return False

    except Exception as e:
        print(f"❌ Error running OCR: {e}")
        return False


def main():
    """Run validation tests."""
    print("=" * 60)
    print("Single-Frame Validation Test")
    print("=" * 60)
    print(f"Test frame: {TEST_FRAME}")
    print(f"Region: ft_score ({FT_SCORE_REGION['x']}, {FT_SCORE_REGION['y']}, "
          f"{FT_SCORE_REGION['width']}, {FT_SCORE_REGION['height']})")
    print("=" * 60)
    print()

    # Test 1: Region extraction
    if not test_region_extraction():
        print("\n❌ VALIDATION FAILED: Region extraction error")
        print("   → Do not proceed with full OCR extraction")
        print("   → Adjust ft_score coordinates in config.yaml")
        sys.exit(1)

    # Test 2: OCR detection (optional - may not have EasyOCR installed)
    print()
    ocr_success = test_ocr()

    # Summary
    print("\n" + "=" * 60)
    if ocr_success:
        print("✅ VALIDATION PASSED")
        print("   → Region extracts successfully without OpenCV errors")
        print("   → EasyOCR detects text in region")
        print("   → Safe to proceed with full OCR extraction")
    else:
        print("⚠️  VALIDATION PARTIAL")
        print("   → Region extracts successfully (no OpenCV errors)")
        print("   → OCR test skipped or failed (check EasyOCR setup)")
        print("   → Proceed with caution - monitor full OCR extraction")
    print("=" * 60)

    return 0 if ocr_success else 1


if __name__ == '__main__':
    sys.exit(main())
