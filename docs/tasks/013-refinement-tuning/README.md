# Task 013: Refinement & Tuning

## Objective
Use validation results to tune thresholds and improve accuracy before batch processing.

## Prerequisites
- [012-validation-tools-epic.md](012-validation-tools-epic.md) completed
- Have validation report from test video

## Steps

### 1. Review Validation Report
- Identify common failure patterns
- Which component needs improvement?
  - Scene detection missing transitions? → Adjust threshold
  - OCR missing teams? → Try multi-frame extraction (see below) or adjust ROI regions
  - Classification incorrect? → Refine rules

### 2. Tune Parameters
Edit `config/config.yaml` based on findings:

```yaml
scene_detection:
  threshold: 25.0  # Lowered from 30 if missing scenes

ocr:
  regions:
    scoreboard:
      width: 450  # Increased if scoreboard was cut off

# Multi-frame extraction (if OCR accuracy <90%)
frame_extraction:
  num_frames: 2  # Extract 2 frames per scene (start + middle)
  # Note: Increases processing time but improves accuracy when
  # scoreboard appears mid-scene. See Task 007 for details.
```

### OCR-Specific Tuning

**If team detection accuracy is <90%**, consider multi-frame extraction:

1. **Enable multi-frame in config** (as shown above, set `num_frames: 2` or `3`)
2. **Update CLI/pipeline** to pass `num_frames` to frame extractor
3. **Implement consensus logic** in OCR reader to combine results from multiple frames:
   - If same team detected in 2+ frames → High confidence
   - If different teams in different frames → Use fixture matching as tiebreaker
   - If team only detected in 1 frame → Flag for manual review

**Trade-offs**:
- ✅ **Pro**: 5-15% accuracy improvement when scoreboard visibility is inconsistent
- ❌ **Con**: 2-3x more frames to process and store
- ❌ **Con**: Requires consensus logic implementation

**Decision point**: If accuracy is already >90% with single frame, don't add this complexity.

**Reference**: Task 007 (lines 107-146) contains `extract_multiple_frames_per_scene()` implementation. Task 009 Notes section contains detailed decision framework.

### 3. Re-run and Re-validate
```bash
# Clear cache to force re-processing
rm -rf data/cache/test/

# Run again with new config
python -m motd_analyzer process data/videos/your_video.mp4

# Validate again
python -m motd_analyzer validate \
  --auto data/output/analysis.json \
  --manual data/cache/test/manual_labels.json
```

### 4. Iterate Until Targets Met
Repeat until:
- Team detection accuracy >90% (or multi-frame extraction evaluated if <90%)
- Segment classification accuracy >85%
- You're confident in the results

## Decision Point

**Are you ready for batch processing?**
- ✅ YES → Proceed to [014-batch-processing-epic.md](014-batch-processing-epic.md)
- ❌ NO → Continue tuning, or consider alternative approaches (see [tech-tradeoffs.md](../tech-tradeoffs.md))

## Estimated Time
2-4 hours (may need multiple iterations)

## Reference
See [roadmap.md Phase 6](../roadmap.md#phase-6-refinement--tuning-est-4-8-hours)

## Next Task
[014-batch-processing-epic.md](014-batch-processing-epic.md)
