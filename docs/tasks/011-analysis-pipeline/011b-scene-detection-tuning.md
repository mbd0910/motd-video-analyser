# Task 011b: Hybrid Frame Extraction for FT Graphic Capture

## Objective
Implement hybrid frame extraction combining PySceneDetect scene changes with regular interval sampling to guarantee capture of FT (Full Time) graphics and improve boundary detection.

## Prerequisites
- [x] Task 011a complete (reconnaissance identified FT graphic detection issue)

## Estimated Time
60-90 minutes

## Problem Statement

From 011a reconnaissance:
- **0/7 FT graphics detected** by OCR (expected 7)
- All OCR is from `scoreboard` source only
- Scene boundaries don't align well with segment boundaries
  - Example: Match 2 intro is one 92-second scene (should be ~11 seconds)

**Root Cause Analysis**:
The issue is NOT PySceneDetect sensitivity. The problem is:
1. FT graphics appear for only 2-3 seconds
2. OCR `--smart-filtering` removes scenes <2 seconds
3. PySceneDetect alone may miss brief graphics that don't trigger scene changes

**Impact**: FT graphics are key boundary markers for highlights→interviews transition. Missing them forces us to use timing heuristics instead.

## Hybrid Approach (Selected Strategy)

Instead of tuning PySceneDetect parameters, implement a **hybrid frame extraction** strategy:

### Strategy Components

1. **PySceneDetect Scene Changes** (content-aware)
   - Keep current threshold: 20.0
   - Detects major visual transitions
   - ~810 scenes for 84-minute video

2. **Regular Interval Sampling** (guaranteed coverage)
   - Extract frames every 5 seconds
   - Ensures FT graphics captured (appear for 2-3s)
   - ~1008 samples for 84-minute video (84 min × 60s / 5s)

3. **Smart Deduplication** (avoid duplicates)
   - If PySceneDetect frame within 1 second of interval sample → keep one
   - Reduces redundant OCR processing
   - Expected: ~800-900 unique frames after deduplication

### Why 5-Second Intervals?

- **Guarantees FT graphic capture**: FT graphics appear for 2-3 seconds
- **Manageable frame count**: ~800-900 frames vs 160-240 (current) or 5040 (1 FPS)
- **Processing time**: ~8-10 minutes for OCR (acceptable)
- **Can adjust**: If 5s misses critical moments, can reduce to 3s in future

### Expected Results

| Metric | Current (PySceneDetect only) | Hybrid (5s intervals) |
|--------|------------------------------|----------------------|
| Frames for OCR | 160-240 | 800-900 |
| FT graphics captured | 0/7 (0%) | 7/7 (100%) expected |
| Processing time | ~2-3 min | ~8-10 min |
| Coverage guarantee | Gaps | Every 5 seconds |
| Boundary alignment | Scene-dependent | Time-guaranteed |

## Implementation Steps

### 1. Backup Current Data
- [ ] Copy `data/cache/motd_2025-26_2025-11-01/scenes.json` to `scenes_original.json`
- [ ] Copy `data/cache/motd_2025-26_2025-11-01/frames/` to `frames_original/`
- [ ] Copy `data/cache/motd_2025-26_2025-11-01/ocr_results.json` to `ocr_results_original.json`

### 2. Implement Hybrid Frame Extraction

Add to `src/motd/scene_detection/detector.py`:

```python
def hybrid_frame_extraction(
    video_path: str,
    scenes: list[dict],
    interval: float = 5.0,
    dedupe_threshold: float = 1.0
) -> list[dict]:
    """
    Hybrid frame extraction combining scene changes and interval sampling.

    Args:
        video_path: Path to video file
        scenes: PySceneDetect scene list
        interval: Regular sampling interval (seconds)
        dedupe_threshold: Frames within this many seconds are duplicates

    Returns:
        Deduplicated list of frames to extract with metadata
    """
```

Implementation details:
- [ ] Add `hybrid_frame_extraction()` function
- [ ] Combine PySceneDetect scene start times with interval samples
- [ ] Deduplicate within threshold (default 1.0s)
- [ ] Return sorted list with source metadata (scene_change vs interval_sampling)

### 3. Update Configuration

Add to `config/config.yaml`:

```yaml
ocr:
  # Hybrid frame extraction strategy
  sampling:
    use_hybrid: true              # Enable hybrid extraction
    interval: 5.0                 # Regular sampling interval (seconds)
    dedupe_threshold: 1.0         # Frames within 1s = duplicate
    include_scene_changes: true   # Include PySceneDetect frames

  # ... existing config ...

  filtering:
    skip_intro_seconds: 50
    motd2_interlude_start: 3121
    motd2_interlude_end: 3167
    # REMOVED: min_scene_duration (now handled by hybrid approach)
```

- [ ] Add `ocr.sampling` section
- [ ] Remove `ocr.filtering.min_scene_duration` (replaced by hybrid approach)

### 4. Update OCR Extraction Command

Modify `extract-teams` command to use hybrid extraction:

- [ ] Update `src/motd/__main__.py` OCR command
- [ ] Call `hybrid_frame_extraction()` if `config.ocr.sampling.use_hybrid == True`
- [ ] Pass hybrid frame list to OCR processing
- [ ] Log frame source breakdown (scene_change vs interval_sampling)

### 5. Test Hybrid Extraction

- [ ] Run hybrid extraction on test video:
  ```bash
  python -m motd detect-scenes data/videos/motd_2025-26_2025-11-01.mp4 \
    --output data/cache/motd_2025-26_2025-11-01/scenes.json
  ```
- [ ] Check frame count (expect ~800-900 after deduplication)
- [ ] Verify interval samples at expected times (e.g., 5s, 10s, 15s, ...)

### 6. Re-run OCR with Hybrid Frames

- [ ] Run OCR with hybrid frame extraction:
  ```bash
  python -m motd extract-teams data/videos/motd_2025-26_2025-11-01.mp4 \
    --output data/cache/motd_2025-26_2025-11-01/ocr_results.json
  ```
- [ ] Log processing: total frames, scene_change frames, interval_sampling frames
- [ ] Monitor processing time (expect ~8-10 minutes)

### 7. Verify FT Graphic Capture

Expected FT graphic times (from motd_visual_patterns.md):
- Match 1: ~611s (00:10:11)
- Match 2: ~1329s (00:22:09)
- Match 3: ~2125s (00:35:25)
- Match 4: ~2886s (00:48:06)
- Match 5: ~3649s (01:00:49)
- Match 6: ~4304s (01:11:44)
- Match 7: ~4845s (01:20:45)

Verification:
- [ ] Check OCR results for `ft_graphic` source detections
- [ ] Count FT graphics: `jq '[.ocr_results[] | select(.ocr_source == "ft_graphic")] | length' ocr_results.json`
- [ ] Target: 7/7 FT graphics detected
- [ ] If <7/7: Check which matches missing, adjust interval if needed

### 8. Compare Results

Create comparison table:
- [ ] Frame counts: original vs hybrid
- [ ] FT graphics: original (0/7) vs hybrid (target 7/7)
- [ ] Processing time: original vs hybrid
- [ ] OCR coverage: scenes with detections
- [ ] Boundary alignment: sample spot-checks at match transitions

### 9. Write Tuning Report

Create `docs/scene_detection_tuning_report.md`:
- [ ] Hybrid approach rationale
- [ ] Implementation details
- [ ] Results: frame counts, FT graphics captured, processing time
- [ ] Comparison to original approach
- [ ] Recommendations for future tuning (3s vs 5s intervals)
- [ ] Decision: keep hybrid approach

## Deliverables

### 1. Updated Code
- `src/motd/scene_detection/detector.py` - `hybrid_frame_extraction()` function
- `src/motd/__main__.py` - Updated `extract-teams` command
- `config/config.yaml` - Hybrid sampling configuration

### 2. Scene Detection Tuning Report
Document (`docs/scene_detection_tuning_report.md`) with:
- Hybrid approach explanation
- Implementation details
- Results (frame count, FT graphics found, processing time)
- Comparison to original
- Decision and rationale

### 3. Updated Cache
- `data/cache/motd_2025-26_2025-11-01/ocr_results.json` - With FT graphics
- `data/cache/motd_2025-26_2025-11-01/frames/` - Hybrid extracted frames
- Backups of original data preserved

## Success Criteria
- [ ] Hybrid frame extraction implemented and tested
- [ ] FT graphic detection: 7/7 (100% target)
- [ ] Frame count reasonable: 800-900 frames
- [ ] Processing time acceptable: <15 minutes
- [ ] Tuning report written with comparison
- [ ] Ready to proceed to 011c (segment classifier)

## Testing Commands

```bash
# Backup current data
cp data/cache/motd_2025-26_2025-11-01/scenes.json \
   data/cache/motd_2025-26_2025-11-01/scenes_original.json
cp -r data/cache/motd_2025-26_2025-11-01/frames \
   data/cache/motd_2025-26_2025-11-01/frames_original
cp data/cache/motd_2025-26_2025-11-01/ocr_results.json \
   data/cache/motd_2025-26_2025-11-01/ocr_results_original.json

# Test hybrid extraction (after implementation)
python -m motd extract-teams data/videos/motd_2025-26_2025-11-01.mp4

# Check FT graphic count
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '[.ocr_results[] | select(.ocr_source == "ft_graphic")] | length'

# Check total frames processed
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '.ocr_results | length'

# Check frame source breakdown
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '[.ocr_results[] | .frame_source] | group_by(.) | map({source: .[0], count: length})'
```

## Notes
- Hybrid approach is **superior to PySceneDetect tuning** for this use case
- 5-second intervals balance coverage and processing time
- Can reduce to 3-second intervals if validation shows gaps
- Deduplication prevents redundant OCR processing
- This approach is **reusable for all future episodes**

## Alternative Considered (Not Pursued)

### Option: Tune PySceneDetect Parameters
Lower threshold to 15.0, min duration to 1.0:
- **Pros**: No code changes needed
- **Cons**: May create 1500-2000 scenes (too many), still no guarantee of FT capture
- **Decision**: Rejected in favor of hybrid approach

### Option: 1 FPS Sampling
Extract every frame (25 FPS) or every second (1 FPS):
- **Pros**: Maximum coverage
- **Cons**: 5040 frames = ~50 minutes processing time (excessive)
- **Decision**: Rejected - overkill

## Next Task
[011c-segment-classifier.md](011c-segment-classifier.md)
