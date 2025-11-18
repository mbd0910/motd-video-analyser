# Task 012: Manual Validation Tools (Epic)

## Objective
Build tools to manually validate and correct automated results, establishing ground truth for tuning.

## Prerequisites
- [011-analysis-pipeline-epic.md](011-analysis-pipeline-epic.md) completed
- Have automated results from test video

## Epic Overview
Split into sub-tasks:
1. Create manual labeling tool (interactive CLI)
2. Create validation comparator (automated vs manual)
3. Generate accuracy reports
4. Use results to tune thresholds

## Key Deliverables

### Manual Labeler (`src/motd_analyzer/validation/manual_labeler.py`)
- Interactive tool to review each scene
- Prompt for corrections:
  - Scene type (studio/highlights/interview/analysis)
  - Team names (if OCR missed them)
  - Notes for later reference
- Save corrections to `manual_labels.json`

### Validation Comparator (`src/motd_analyzer/validation/comparator.py`)
- Load automated results
- Load manual labels
- Calculate accuracy metrics:
  - Segment classification accuracy
  - Team detection accuracy
  - Timestamp accuracy
- Generate validation report

## Commands
```bash
# Manual labeling
python -m motd_analyzer label-scenes data/cache/test/scenes.json

# Compare results
python -m motd_analyzer validate \
  --auto data/output/analysis.json \
  --manual data/cache/test/manual_labels.json
```

## Success Criteria
- [ ] Manual labeling tool is usable
- [ ] Can correct automated results
- [ ] Validation report shows accuracy metrics
- [ ] Metrics help identify where to improve

## Estimated Time
2-3 hours

## Notes
- Don't need to label everything - sample 20-30 scenes is enough
- Focus on scenes where automation was uncertain (low confidence)
- Use this data to tune thresholds in Phase 6

## Reference
See [roadmap.md Phase 5](../roadmap.md#phase-5-manual-validation-tools-est-4-6-hours) for code examples.

## Next Task
[013-refinement-tuning.md](013-refinement-tuning.md)
