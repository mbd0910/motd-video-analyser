# Task 009b: Implement OCR Reader Module

## Objective
Create OCR reader module with EasyOCR integration, optimized using findings from 009a reconnaissance.

## Prerequisites
- Task 009a completed (visual patterns documented, episode manifest created)
- `docs/motd_visual_patterns.md` provides guidance on OCR regions and frame types
- EasyOCR will download ~100MB of models on first run

## Tasks

### 1. Create OCR Reader Module (45-60 min)
- [ ] Create `src/motd/ocr/reader.py` with `OCRReader` class
- [ ] Initialize EasyOCR with English language support
- [ ] Support GPU/CPU mode from config
- [ ] Implement region-based OCR extraction:
  - [ ] `extract_scoreboard()` - top-left region
  - [ ] `extract_formation()` - bottom-right region
  - [ ] `extract_regions()` - run both regions on a frame
- [ ] Return structured results with text, confidence, and region type

### 2. Optimize Based on Reconnaissance Findings (15-30 min)
- [ ] Review `docs/motd_visual_patterns.md` OCR recommendations
- [ ] Adjust OCR regions in config if needed (based on actual frame analysis)
- [ ] Add any preprocessing steps identified (e.g., contrast enhancement, region cropping)
- [ ] Prioritize formation graphics over scoreboards (if findings support this)

### 3. Test on Sample Frames (30-45 min)
- [ ] Select 5-10 test frames from 009a documentation:
  - [ ] At least 3 formation graphic frames
  - [ ] At least 2 scoreboard frames
  - [ ] At least 1 studio frame (should return no teams)
- [ ] Run OCR on test frames
- [ ] Verify text extraction works
- [ ] Check confidence scores are reasonable (>0.6 for clear text)
- [ ] Debug any issues (GPU not detected, poor text extraction, etc.)

### 4. Create Unit Tests (Optional, 20-30 min)
- [ ] Create `tests/test_ocr_reader.py`
- [ ] Test OCR reader initialization
- [ ] Test region extraction (mock EasyOCR if needed)
- [ ] Test GPU/CPU mode selection

## Implementation Details

### Module Structure: `src/motd/ocr/reader.py`

```python
"""OCR reader for extracting text from video frames."""

import easyocr
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class OCRReader:
    """Reads text from video frames using EasyOCR."""

    def __init__(self, config: Dict):
        """
        Initialize OCR reader.

        Args:
            config: OCR configuration dict with:
                - languages: List of language codes (e.g., ['en'])
                - gpu: Whether to use GPU (bool)
                - confidence_threshold: Minimum confidence (float)
                - regions: Dict of region definitions
        """
        self.config = config
        self.reader = easyocr.Reader(
            config['languages'],
            gpu=config.get('gpu', True)
        )
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.regions = config.get('regions', {})

    def extract_region(
        self,
        frame_path: Path,
        region_name: str
    ) -> List[Dict]:
        """
        Extract text from a specific region of a frame.

        Args:
            frame_path: Path to frame image
            region_name: Name of region ('scoreboard' or 'formation')

        Returns:
            List of dicts with:
                - text: Extracted text
                - confidence: OCR confidence score
                - bbox: Bounding box coordinates
        """
        # Load frame
        frame = cv2.imread(str(frame_path))
        if frame is None:
            raise ValueError(f"Could not load frame: {frame_path}")

        # Get region coordinates
        if region_name not in self.regions:
            raise ValueError(f"Unknown region: {region_name}")

        region = self.regions[region_name]
        x, y, w, h = region['x'], region['y'], region['width'], region['height']

        # Crop to region
        cropped = frame[y:y+h, x:x+w]

        # Run OCR
        results = self.reader.readtext(cropped)

        # Format results
        formatted = []
        for bbox, text, conf in results:
            if conf >= self.confidence_threshold:
                formatted.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': bbox,
                    'region': region_name
                })

        return formatted

    def extract_scoreboard(self, frame_path: Path) -> List[Dict]:
        """Extract text from scoreboard region (top-left)."""
        return self.extract_region(frame_path, 'scoreboard')

    def extract_formation(self, frame_path: Path) -> List[Dict]:
        """Extract text from formation graphic region (bottom-right)."""
        return self.extract_region(frame_path, 'formation')

    def extract_all_regions(self, frame_path: Path) -> Dict[str, List[Dict]]:
        """
        Extract text from all defined regions.

        Returns:
            Dict mapping region names to extraction results
        """
        results = {}
        for region_name in self.regions.keys():
            try:
                results[region_name] = self.extract_region(frame_path, region_name)
            except Exception as e:
                # Log error but continue with other regions
                results[region_name] = {'error': str(e)}

        return results
```

### Test Script Example

Create `scripts/test_ocr.py` for manual testing:

```python
"""Manual test script for OCR reader."""

import yaml
from pathlib import Path
from src.motd.ocr.reader import OCRReader

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize reader
reader = OCRReader(config['ocr'])

# Test frames from 009a documentation
test_frames = [
    'data/cache/motd_2025-26_2025-11-01/frames/scene_123.jpg',  # Formation example
    'data/cache/motd_2025-26_2025-11-01/frames/scene_234.jpg',  # Scoreboard example
]

for frame_path in test_frames:
    print(f"\n=== Testing: {frame_path} ===")

    # Extract from all regions
    results = reader.extract_all_regions(Path(frame_path))

    for region, texts in results.items():
        print(f"\nRegion: {region}")
        if isinstance(texts, dict) and 'error' in texts:
            print(f"  Error: {texts['error']}")
        else:
            for item in texts:
                print(f"  Text: {item['text']}")
                print(f"  Confidence: {item['confidence']:.2f}")
```

## Success Criteria
- [ ] `src/motd/ocr/reader.py` created with OCRReader class
- [ ] EasyOCR initializes successfully (GPU or CPU mode)
- [ ] Can extract text from scoreboard region
- [ ] Can extract text from formation region
- [ ] Tested on 5-10 sample frames identified in 009a
- [ ] Text extraction works on formation graphics with >0.7 confidence
- [ ] Module handles errors gracefully (missing frames, invalid regions)
- [ ] Code follows Python guidelines (type hints, docstrings)

## Estimated Time
1-1.5 hours:
- Implementation: 45-60 min
- Optimization: 15-30 min
- Testing: 30-45 min
- Unit tests (optional): 20-30 min

## Notes
- **EasyOCR first run downloads models**: ~100MB, takes 1-2 minutes
- **GPU acceleration**: 5-10x faster than CPU for 810 frames
- **Formation graphics are priority**: Based on 009a findings, these should have best accuracy
- **Confidence threshold tuning**: Start with 0.7, adjust based on results

## Troubleshooting
- **GPU not detected**: Check PyTorch CUDA installation, fall back to CPU in config
- **Poor text extraction**: Try preprocessing (grayscale, contrast enhancement, thresholding)
- **Wrong region**: Verify video resolution is 1920x1080, adjust config regions if not

## Output Files
- `src/motd/ocr/reader.py` (new module)
- `tests/test_ocr_reader.py` (optional, if creating tests)
- `scripts/test_ocr.py` (optional manual test script)

## Next Task
[009c-implement-team-matcher.md](009c-implement-team-matcher.md) - Team name fuzzy matching
