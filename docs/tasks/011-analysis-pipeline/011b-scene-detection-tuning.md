# Task 011b: Scene Detection Tuning & FT Graphic Investigation

## Objective
Improve scene detection to capture FT (Full Time) graphics and better align scene boundaries with segment boundaries.

## Prerequisites
- [x] Task 011a complete (reconnaissance identified FT graphic detection issue)

## Estimated Time
30-60 minutes

## Problem Statement

From 011a reconnaissance:
- **0/7 FT graphics detected** by OCR (expected 7)
- All OCR is from `scoreboard` source only
- Scene boundaries don't align well with segment boundaries
  - Example: Match 2 intro is one 92-second scene (should be ~11 seconds)
- Current PySceneDetect settings may be too conservative:
  ```yaml
  threshold: 25.0
  min_scene_duration: 3.0
  ```

**Impact**: FT graphics are key boundary markers for highlights→interviews transition. Missing them forces us to use timing heuristics instead.

## Approach

### Option 1: Tune PySceneDetect Parameters (Recommended)

Test with more sensitive settings:
```yaml
scene_detection:
  detector_type: content
  threshold: 15.0  # Lower from 25.0 (more sensitive)
  min_scene_duration: 1.0  # Lower from 3.0 (allow shorter scenes)
```

### Option 2: Alternative Detector

If Option 1 doesn't work, try:
```yaml
scene_detection:
  detector_type: adaptive  # Instead of content
  threshold: 3.0
  min_scene_duration: 1.0
```

### Option 3: 1 FPS Sampling (If Options 1-2 fail)

Extract 1 frame per second (~5040 frames for 84-minute video)
- **Pros**: Guaranteed FT graphic capture
- **Cons**: 6.2x more OCR processing

## Implementation Steps

### 1. Backup Current Data
- [ ] Copy `data/cache/motd_2025-26_2025-11-01/scenes.json` to `scenes_original.json`
- [ ] Copy `data/cache/motd_2025-26_2025-11-01/frames/` to `frames_original/`

### 2. Test Option 1: Lower Threshold
- [ ] Update `config/config.yaml` with new settings
- [ ] Re-run scene detection: `python -m motd detect-scenes`
- [ ] Check results:
  - How many scenes? (manageable if <2000)
  - Are FT graphics captured? (check around expected times)
  - Do boundaries align better?

### 3. Check FT Graphic Timestamps

Expected FT graphic times (from motd_visual_patterns.md):
- Match 1: ~611s (00:10:11)
- Match 2: ~1329s (00:22:09)
- Match 3: ~2125s (00:35:25)
- Match 4: ~2886s (00:48:06)
- Match 5: ~3649s (01:00:49)
- Match 6: ~4304s (01:11:44)
- Match 7: ~4845s (01:20:45)

Script to check:
```python
# Look for scenes within ±5 seconds of FT times
ft_times = [611, 1329, 2125, 2886, 3649, 4304, 4845]
for scene in scenes:
    for ft_time in ft_times:
        if abs(scene["start_seconds"] - ft_time) < 5:
            print(f"Scene {scene['scene_id']}: {scene['start_time']} (near FT at {ft_time}s)")
```

### 4. Re-run OCR (If Needed)
- [ ] If new scenes look good, re-run OCR:
  ```bash
  python -m motd extract-teams data/videos/motd_2025-26_2025-11-01.mp4 \
    --output data/cache/motd_2025-26_2025-11-01/ocr_results.json \
    --smart-filtering
  ```
- [ ] Check: Are FT graphics now detected? (target: 7/7)

### 5. Compare Results
- [ ] Old scenes: 810 total, 0 FT graphics
- [ ] New scenes: ??? total, ??? FT graphics
- [ ] Duration distribution changes?
- [ ] Boundary alignment improvements?

### 6. Decision Point

**If improved (FT graphics found):**
- [ ] Keep new scenes.json and frames
- [ ] Update reconnaissance report with findings
- [ ] Proceed to 011c with better data

**If not improved:**
- [ ] Revert to original scenes.json
- [ ] Document findings
- [ ] Proceed to 011c with timing heuristics (as planned in 011a)
- [ ] Consider Option 3 (1 FPS) for Task 013 (refinement)

## Deliverables

### Scene Detection Tuning Report
Brief document (`docs/scene_detection_tuning_report.md`) with:
- Settings tested
- Results (scene count, FT graphics found)
- Comparison to original
- Decision and rationale

### Updated Cache (If Keeping New Scenes)
- `scenes.json` with improved detection
- `frames/` with new key frames
- `ocr_results.json` with re-run OCR

## Success Criteria
- [ ] At least one tuning option tested
- [ ] FT graphic detection assessed (count found)
- [ ] Decision made: keep new scenes OR revert to original
- [ ] Tuning report written
- [ ] Ready to proceed to 011c (segment classifier)

## Notes
- This is a **quick investigation**, not a deep tuning session
- Goal: Determine if simple param changes help
- If not, document and move on
- Can revisit in Task 013 (refinement) if needed
- Don't spend more than 60 minutes on this

## Testing Commands

```bash
# Update config
vim config/config.yaml  # Set threshold=15.0, min_duration=1.0

# Re-run scene detection
python -m motd detect-scenes data/videos/motd_2025-26_2025-11-01.mp4 \
  --output data/cache/motd_2025-26_2025-11-01/scenes.json

# Check scene count
cat data/cache/motd_2025-26_2025-11-01/scenes.json | jq '.total_scenes'

# Check for scenes near FT times
python scripts/check_ft_scenes.py

# Re-run OCR (if keeping new scenes)
python -m motd extract-teams data/videos/motd_2025-26_2025-11-01.mp4 \
  --smart-filtering

# Check FT graphic detection
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '[.ocr_results[] | select(.ocr_source == "ft_graphic")] | length'
```

## Next Task
[011c-segment-classifier.md](011c-segment-classifier.md)
