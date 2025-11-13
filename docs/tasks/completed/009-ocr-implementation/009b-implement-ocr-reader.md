# Task 009b: Implement OCR Reader Module

## Objective
Create OCR reader module with EasyOCR integration, optimized using findings from 009a reconnaissance.

## Prerequisites
- Task 009a completed (visual patterns documented, episode manifest created)
- `docs/motd_visual_patterns.md` provides guidance on OCR regions and frame types
- EasyOCR will download ~100MB of models on first run

## Tasks

### 1. Create OCR Reader Module (45-60 min)
- [x] Create `src/motd/ocr/reader.py` with `OCRReader` class
- [x] Initialize EasyOCR with English language support
- [x] Support GPU/CPU mode from config
- [x] Implement region-based OCR extraction:
  - [x] `extract_ft_score()` - lower-middle region (full-time score graphic)
  - [x] `extract_scoreboard()` - top-left region (live scoreboard)
  - [x] `extract_formation()` - bottom-right region (formation graphic)
  - [x] `extract_all_regions()` - run all regions on a frame
- [x] Return structured results with text, confidence, and region type

### 2. Optimize Based on Reconnaissance Findings (15-30 min)
- [x] Review `docs/motd_visual_patterns.md` OCR recommendations
- [x] Adjust OCR regions in config based on multi-tiered strategy:
  - [x] **Add FT score region** (lower-middle): x: 800, y: 900, width: 320, height: 120
  - [x] **Update scoreboard region** (top-left): verify coordinates match 009a findings
  - [x] **Update formation region** (bottom-right): verify coordinates match 009a findings
- [x] Add any preprocessing steps identified (e.g., contrast enhancement for motion-blurred scoreboards)
- [x] **Strategy**: Prioritize FT score graphics (90-95% auto-capture) > scoreboards (ubiquitous but blurred) > formations (ground truth validation only)

### 3. Test on Sample Frames (30-45 min)
- [x] Select 5-10 test frames from 009a documentation:
  - [x] **Primary test**: Full-time score graphics (scene_219, 312, 401, 487, 583, 655, 736)
  - [x] **Secondary test**: Live scoreboards (scene_154, 277, 370, 486, 574, 673, 718)
  - [ ] **Ground truth validation**: Compare against manual formation screenshots
  - [ ] At least 1 studio frame (should return no teams)
- [x] Run OCR on test frames
- [x] Verify text extraction works
- [x] Check confidence scores are reasonable (>0.7 for clear text)
- [ ] Validate accuracy against ground truth manual screenshots
- [x] Debug any issues (GPU not detected, poor text extraction, etc.)

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
            region_name: Name of region ('ft_score', 'scoreboard', or 'formation')

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

    def extract_ft_score(self, frame_path: Path) -> List[Dict]:
        """Extract text from full-time score region (lower-middle)."""
        return self.extract_region(frame_path, 'ft_score')

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
    'data/cache/motd_2025-26_2025-11-01/frames/scene_219.jpg',  # FT score (Match 1)
    'data/cache/motd_2025-26_2025-11-01/frames/scene_312.jpg',  # FT score (Match 2)
    'data/cache/motd_2025-26_2025-11-01/frames/scene_154.jpg',  # Live scoreboard (Match 1)
    'data/cache/motd_2025-26_2025-11-01/frames/scene_277.jpg',  # Live scoreboard (Match 2)
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
- [x] `src/motd/ocr/reader.py` created with OCRReader class
- [x] EasyOCR initializes successfully (GPU or CPU mode)
- [x] Can extract text from scoreboard region
- [x] Can extract text from formation region
- [x] Tested on 5-10 sample frames identified in 009a
- [x] Text extraction works on formation graphics with >0.7 confidence
- [x] Module handles errors gracefully (missing frames, invalid regions)
- [x] Code follows Python guidelines (type hints, docstrings)

## Estimated Time
1-1.5 hours:
- Implementation: 45-60 min
- Optimization: 15-30 min
- Testing: 30-45 min
- Unit tests (optional): 20-30 min

## Notes
- **EasyOCR first run downloads models**: ~100MB, takes 1-2 minutes
- **GPU acceleration**: 5-10x faster than CPU for 810 frames
- **Multi-tiered strategy from 009a**: FT scores (primary, 90-95% auto-capture) > scoreboards (secondary, motion-blurred) > formations (ground truth from manual screenshots)
- **Formation graphics limitation**: Auto-captured for only 3-4 of 7 matches; use manual screenshots for validation
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
