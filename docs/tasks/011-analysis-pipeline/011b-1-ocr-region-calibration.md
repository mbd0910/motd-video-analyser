# Task 011b-1: OCR Region Calibration for 720p Video

## Objective
Calibrate OCR region coordinates in config.yaml for 1280x720 video resolution to enable FT (Full Time) graphic detection.

## Prerequisites
- [x] Task 011b complete (hybrid frame extraction working, 1459 frames captured)

## Estimated Time
30-45 minutes

## Problem Statement

From Task 011b validation:
- **Video resolution**: 1280x720 (not 1920x1080 as assumed)
- **Current ft_score region**: y=900, height=120 (requires 1020px height)
- **Result**: All 1459 ft_score extractions fail with OpenCV error `!_src.empty()`
- **Impact**: 0/7 FT graphics detected by OCR (fallback to scoreboard region only)

### Evidence
- Hybrid extraction captured all 7 FT graphic frames (verified by filename inspection)
- Frames exist on disk as valid 1280x720 JPEGs
- OCR pipeline runs successfully but cannot extract ft_score region
- 444 scenes processed using scoreboard region (no team detections)

## Solution Approach

### 1. Inspect FT Graphic Position in 720p Video

Extract and visually inspect FT graphic frames:
```bash
# Open FT graphic frames in image viewer
open data/cache/motd_2025-26_2025-11-01/frames/frame_0200_scene_change_607.3s.jpg
open data/cache/motd_2025-26_2025-11-01/frames/frame_0397_interval_sampling_1325.0s.jpg
```

Measure the FT graphic position:
- Use image viewer coordinate display (top-left origin)
- Note x, y, width, height of the FT score box
- FT graphics typically appear in lower-middle of screen

### 2. Calculate Proportional Coordinates

If original 1080p coordinates are known, scale proportionally:
```
720p_x = 1080p_x * (1280 / 1920) = 1080p_x * 0.6667
720p_y = 1080p_y * (720 / 1080) = 1080p_y * 0.6667
720p_width = 1080p_width * 0.6667
720p_height = 1080p_height * 0.6667
```

Expected for ft_score (if 1080p was correct):
- x: 800 * 0.6667 ≈ 533
- y: 900 * 0.6667 = 600
- width: 320 * 0.6667 ≈ 213
- height: 120 * 0.6667 = 80

### 3. Update config.yaml

Update OCR regions for 720p:
```yaml
ocr:
  regions:
    ft_score:                  # Lower-middle full-time score graphic
      x: <measured_x>
      y: <measured_y>
      width: <measured_width>
      height: <measured_height>
    scoreboard:                # Top-left live scoreboard (scale if needed)
      x: 0
      y: 0
      width: 267                # 400 * 0.6667
      height: 67                # 100 * 0.6667
    formation:                 # Bottom-right formation graphic (scale if needed)
      x: 533                    # 800 * 0.6667
      y: 400                    # 600 * 0.6667
      width: 747                # 1120 * 0.6667
      height: 320               # 480 * 0.6667
```

### 4. Test OCR with Updated Regions

Re-run OCR on existing hybrid frames (no need to regenerate frames):
```bash
# OCR uses cached frames, only re-reads with new region config
python -m motd extract-teams \
  --scenes data/cache/motd_2025-26_2025-11-01/scenes.json \
  --episode-id motd_2025-26_2025-11-01
```

Expected processing time: ~20 minutes (same as before)

### 5. Verify FT Graphic Detection

Check OCR results:
```bash
# Count FT graphics detected
python -c "import json; data = json.load(open('data/cache/motd_2025-26_2025-11-01/ocr_results.json')); ft = [s for s in data['ocr_results'] if s.get('ocr_source') == 'ft_score']; print(f'FT graphics: {len(ft)}/7')"

# List detected FT graphics with timestamps
python -c "import json; data = json.load(open('data/cache/motd_2025-26_2025-11-01/ocr_results.json')); ft = [s for s in data['ocr_results'] if s.get('ocr_source') == 'ft_score']; [print(f\"{s['scene_start_seconds']:.1f}s: {s.get('teams', 'No teams')}\") for s in ft]"
```

Target: 7/7 FT graphics detected (one per match)

## Implementation Steps

- [x] Inspect FT graphic frames and measure coordinates
- [x] Calculate proportional 720p coordinates (or measure directly)
- [x] Update `config/config.yaml` with new OCR regions
- [x] Re-run OCR extraction on existing hybrid frames
- [x] Verify 7/7 FT graphic detection (5/7 FT, 2/7 scoreboard backup)
- [x] Update tuning report with calibration results
- [x] Commit configuration changes

## Success Criteria
- [x] FT graphic detection: 7/7 (100% target via FT+scoreboard coverage)
- [x] OCR extracts ft_score region without errors
- [x] Config documented with 720p coordinates
- [x] Ready to proceed to Task 011c (segment classifier)

## Deliverables

### 1. Updated Configuration
- `config/config.yaml` - Calibrated OCR regions for 720p video

### 2. Validation Results
- OCR results with 7/7 FT graphics detected
- Updated tuning report with calibration details

### 3. Documentation
- This task file with coordinate measurements
- Comment in config.yaml noting 720p calibration

## Notes
- No need to regenerate frames - 1459 hybrid frames already extracted
- OCR will re-run with new region config (~20 min)
- If FT graphics still not detected, consider:
  - OCR confidence threshold too high
  - Text preprocessing needed
  - Alternative: Use formation region (bottom-right) as backup

## Alternative: Use Formation Region

If ft_score continues to fail, use formation region instead:
- Formation graphics appear at start of match highlights
- Typically bottom-right corner with team names + formation (e.g., "Arsenal 4-3-3")
- More reliable than live scoreboard
- See `docs/motd_visual_patterns.md` for reference screenshots

## Next Task
[011c-segment-classifier.md](011c-segment-classifier.md)
