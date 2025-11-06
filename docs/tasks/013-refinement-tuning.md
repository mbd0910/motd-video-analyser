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
  - OCR missing teams? → Adjust ROI regions
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
```

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
- Team detection accuracy >90%
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
