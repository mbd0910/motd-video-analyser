# Task 009g: Validate and Tune OCR Results

## Objective
Manually validate OCR results against expected fixtures, calculate accuracy, and tune if needed to reach >95% target.

## Prerequisites
- Task 009f completed (OCR results generated)
- Output file: `data/cache/motd_2025-26_2025-11-01/ocr_results.json`

## Tasks

### 1. Manual Validation (30-45 min)
- [ ] Review OCR results JSON
- [ ] For each expected fixture (7 matches):
  - [ ] Find scenes where teams were detected
  - [ ] Open corresponding frame images
  - [ ] Visually verify: Were teams correctly identified?
  - [ ] Note false positives (wrong team detected)
  - [ ] Note false negatives (team missed)
- [ ] Create validation spreadsheet or notes

### 2. Calculate Accuracy Metrics (15-20 min)
- [ ] Count total team detections
- [ ] Count correct detections (true positives)
- [ ] Count incorrect detections (false positives)
- [ ] Count missed detections (false negatives)
- [ ] Calculate precision: TP / (TP + FP)
- [ ] Calculate recall: TP / (TP + FN)
- [ ] Calculate F1 score: 2 * (precision * recall) / (precision + recall)
- [ ] Per-fixture accuracy: Were both teams detected for each match?

### 3. Analyze Failure Patterns (20-30 min)
- [ ] Which frames had failures?
  - [ ] Formation graphics or scoreboards?
  - [ ] Specific teams that fail often?
  - [ ] OCR confidence scores for failures?
- [ ] Why did failures occur?
  - [ ] Motion blur?
  - [ ] Wrong OCR region?
  - [ ] Team name variation not in database?
  - [ ] Studio segment misclassified as match?
- [ ] Document patterns

### 4. Tune if Needed (30-60 min, if accuracy <95%)
- [ ] If accuracy >95%: Skip tuning, proceed to documentation
- [ ] If accuracy 90-95%: Consider whether tuning worth effort
- [ ] If accuracy <90%: Apply tuning strategies below

#### Tuning Strategies

**Strategy 1: Adjust OCR Regions**
- [ ] Check if video is actually 1920x1080: `ffprobe data/videos/motd_2025-26_2025-11-01.mp4`
- [ ] If different resolution, recalculate region coordinates
- [ ] Look at failed frames - is graphic outside current region?
- [ ] Update `config/config.yaml` with adjusted regions
- [ ] Re-run 009f with new config

**Strategy 2: Add Team Name Variations**
- [ ] Check failed matches - what text did OCR extract?
- [ ] Add variations to `data/teams/premier_league_2025_26.json` alternates
- [ ] Example: If OCR extracted "Man U" but not matched, add to alternates
- [ ] Re-run team matching (no need to re-run OCR)

**Strategy 3: Adjust Confidence Thresholds**
- [ ] Review confidence scores for correct vs incorrect detections
- [ ] If false positives have low confidence, raise threshold
- [ ] If true positives have low confidence, lower threshold
- [ ] Update `ocr.confidence_threshold` in config
- [ ] Re-run 009f

**Strategy 4: Multi-Frame Extraction (Advanced)**
- [ ] If accuracy still <90% after above strategies
- [ ] Task 007 supports extracting 2-3 frames per scene
- [ ] Update frame extractor call to use `num_frames=2`
- [ ] Modify OCR to use consensus across multiple frames
- [ ] Re-run scene detection + frame extraction + OCR
- [ ] **Note**: This adds 2-3x processing time

**Strategy 5: Alternative OCR Engine**
- [ ] If EasyOCR consistently fails
- [ ] Consider PaddleOCR (see `docs/tech-tradeoffs.md`)
- [ ] Requires implementation changes
- [ ] Defer to Task 013 (refinement phase)

### 5. Document Final Results (15-20 min)
- [ ] Record final accuracy metrics
- [ ] Document any tuning applied
- [ ] List known limitations
- [ ] Recommend next steps (if needed)
- [ ] Update task README with findings

## Validation Template

Use this structure to record findings:

```markdown
# OCR Validation Results - Task 009g

## Episode: motd_2025-26_2025-11-01
**Date:** 2025-11-11
**Validator:** [Your name]

## Expected Fixtures (7 matches)

| Match | Home Team | Away Team | Detected? | Frame(s) | Notes |
|-------|-----------|-----------|-----------|----------|-------|
| 1 | Brighton & Hove Albion | Leeds United | ✅/❌ | scene_XXX.jpg | |
| 2 | Burnley | Arsenal | ✅/❌ | scene_XXX.jpg | |
| 3 | Crystal Palace | Brentford | ✅/❌ | scene_XXX.jpg | |
| 4 | Fulham | Wolverhampton Wanderers | ✅/❌ | scene_XXX.jpg | |
| 5 | Nottingham Forest | Manchester United | ✅/❌ | scene_XXX.jpg | |
| 6 | Tottenham Hotspur | Chelsea | ✅/❌ | scene_XXX.jpg | |
| 7 | Liverpool | Aston Villa | ✅/❌ | scene_XXX.jpg | |

## Accuracy Metrics

- **Total team detections:** XXX
- **True positives (correct):** XXX
- **False positives (wrong team):** XXX
- **False negatives (missed):** XXX
- **Precision:** XX%
- **Recall:** XX%
- **F1 Score:** XX%
- **Per-fixture coverage:** X/7 matches had both teams detected

## Failure Analysis

### False Positives
| Frame | Detected (wrong) | Actual | Reason |
|-------|------------------|--------|--------|
| scene_XXX.jpg | West Ham | Brighton | [why] |

### False Negatives
| Frame | Missed Team | Reason |
|-------|-------------|--------|
| scene_XXX.jpg | Leeds United | [why] |

### Patterns Observed
- [e.g., "Scoreboards often motion-blurred, formation graphics much clearer"]
- [e.g., "Manchester teams confused due to partial OCR"]
- [e.g., "Studio graphics occasionally misidentified as team graphics"]

## Tuning Applied

### Iteration 1: [Description]
- **Change:** [what was changed]
- **Accuracy before:** XX%
- **Accuracy after:** XX%

### Iteration 2: [If needed]
- **Change:** [what was changed]
- **Accuracy before:** XX%
- **Accuracy after:** XX%

## Final Results

- **Final accuracy:** XX%
- **Target met:** ✅/❌ (target: >95%)
- **Recommendation:** [Continue to Task 010 / Need further tuning / etc.]

## Known Limitations

- [List any remaining issues]
- [Edge cases that still fail]

## Recommendations for Future

- [Suggestions for Task 013 refinement]
- [Ideas for improvement]
```

## Success Criteria
- [ ] Manual validation completed for all 7 expected fixtures
- [ ] Accuracy metrics calculated and documented
- [ ] If accuracy >95%: Task complete, ready for Task 010
- [ ] If accuracy <95%: Tuning attempted and documented
- [ ] Failure patterns analyzed and documented
- [ ] Validation results saved in permanent record
- [ ] Recommendations made for next steps

## Decision Points

### Accuracy >95%
✅ **Success!** Continue to Task 010 (transcription)

### Accuracy 90-95%
⚠️ **Good but not great.** Decision:
- Acceptable for MVP? → Continue to Task 010, revisit in Task 013
- Need improvement now? → Apply tuning strategies

### Accuracy <90%
❌ **Needs improvement.** Must apply tuning before proceeding:
1. Try Strategy 1-3 first (quick wins)
2. If still <90%, try Strategy 4 (multi-frame)
3. If still failing, defer to Task 013 and consider Strategy 5 (alternative OCR)

## Estimated Time
1-1.5 hours base + tuning time if needed:
- Manual validation: 30-45 min
- Accuracy calculation: 15-20 min
- Failure analysis: 20-30 min
- Tuning (if needed): 30-60 min per iteration
- Documentation: 15-20 min

## Output Files
- Validation notes/spreadsheet (create in `docs/validation/009g_ocr_validation.md`)
- Updated config if tuning applied
- Updated team data if variations added

## Next Task
[010-transcription-epic](../010-transcription/) - Audio transcription with faster-whisper

## Notes
- **Don't expect 100% accuracy** - 95% is excellent for OCR on sports graphics
- **Formation graphics should have higher accuracy** than scoreboards (clearer text)
- **Fixture-aware matching helps significantly** - reduces false positives
- **Document everything** - learnings from this validation inform future tasks
