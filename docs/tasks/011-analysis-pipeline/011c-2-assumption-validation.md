# Task 011c-2: Assumption Validation

## Quick Context

**Parent Task:** [011c-segment-classifier](011c-segment-classifier.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [FT Graphic](../../domain/README.md#ft-graphic), [Scoreboard](../../domain/README.md#scoreboard)
**Business Rules:** [FT Graphic Validation](../../domain/business_rules.md#rule-1-ft-graphic-validation)

**Why This Matters:** Validating classification rules BEFORE implementing them prevents building a classifier based on incorrect assumptions. This task uses the ground truth dataset from 011c-1 to test specific heuristics (duration ranges, keyword detection, sequencing patterns) and measure their effectiveness. Only validated rules proceed to implementation in 011c-3, saving hours of debugging and iteration.

**Prerequisites:** 011c-1 must be complete with all 39 scenes labeled and pattern analysis showing at least 2-3 promising signals.

See [Visual Patterns](../../domain/visual_patterns.md) for episode structure and [Business Rules](../../domain/business_rules.md) for validation requirements.

---

## Objective

Validate specific classification assumptions (FT graphic detection, duration ranges, transcript keywords, sequencing patterns) against the ground truth dataset to determine which rules should be implemented in the segment classifier.

## Prerequisites

- [x] Task 011c-1 complete (ground truth dataset with 39 labeled scenes)
- [x] Pattern analysis shows at least 2-3 promising signals
- [ ] Understanding of [FT Graphic Validation](../../domain/business_rules.md#rule-1-ft-graphic-validation)
- [ ] Config file structure: `config/config.yaml` (to be updated with validated thresholds)

## Estimated Time

30 minutes

## Deliverables

1. **FT graphic validation results** - Verify 7 FT graphics detected correctly
2. **Updated `config/config.yaml`** - Segment duration thresholds from ground truth
3. **Validation report** - Document which rules work, which don't, and confidence levels

## Implementation Steps

### 1. FT Graphic + OCR Validation (10 mins)

**Goal:** Verify our anchor signal (FT graphics mark match end) is reliable

- [ ] Load `data/cache/motd_2025-26_2025-11-01/ocr_results.json`
- [ ] Filter for scenes with FT graphics: `ft_graphic: true`
- [ ] Validate expectations:
  - **Exactly 7 FT graphics** (one per match)
  - **Timestamps match visual_patterns.md** match end times (±10s tolerance)
  - **All FT scenes labeled as "highlights"** in ground truth
- [ ] Check OCR-to-highlights correlation:
  - Count ground truth "highlights" scenes with OCR
  - Count ground truth "highlights" scenes without OCR
  - Calculate precision: What % of OCR scenes are highlights?
  - Calculate recall: What % of highlights have OCR?
- [ ] Document findings:
  ```markdown
  ## FT Graphic Validation Results
  - FT graphics detected: X/7 (expected 7)
  - Timestamp accuracy: X/7 within ±10s of visual_patterns
  - OCR→highlights precision: XX%
  - OCR→highlights recall: XX%
  - **Decision:** FT graphics are [reliable/unreliable] anchor signal
  ```
- [ ] **Commit:** `test: Validate FT graphic detection and OCR-to-highlights correlation`

**Success criteria:** All 7 FT graphics detected, timestamps within ±10s, precision >90%

---

### 2. Duration Range Analysis (15 mins)

**Goal:** Determine actual duration ranges per segment type from ground truth

- [ ] Calculate duration statistics per segment type:
  - For each of 7 types (intro, studio_intro, highlights, interviews, studio_analysis, interlude, outro)
  - Extract durations from labeled scenes
  - Compute: min, max, median, mean, standard deviation
- [ ] Compare against task file assumptions:
  | Segment Type | Task Assumption | Actual (from ground truth) | Validated? |
  |--------------|-----------------|---------------------------|-----------|
  | Studio intro | 7-11s | min-max s | YES/NO |
  | Interviews | 45-90s | min-max s | YES/NO |
  | Studio analysis | 2-5 mins | min-max s | YES/NO |
  | Highlights | 5-10 mins | min-max s | YES/NO |
- [ ] Update `config/config.yaml` with validated thresholds:
  ```yaml
  segment_classification:
    studio_intro:
      min_duration_seconds: X  # From ground truth
      max_duration_seconds: X  # From ground truth

    highlights:
      min_duration_seconds: X
      max_duration_seconds: X

    interviews:
      min_duration_seconds: X
      max_duration_seconds: X

    studio_analysis:
      min_duration_seconds: X
      max_duration_seconds: X
  ```
- [ ] Document decision:
  - Which duration ranges are discriminative? (minimal overlap between types)
  - Which are too broad? (high overlap = weak signal)
  - **Recommendation:** Use duration as primary, secondary, or tertiary signal?
- [ ] **Commit:** `config: Update segment duration thresholds from ground truth analysis`

**Success criteria:** At least 2 segment types have non-overlapping duration ranges

---

### 3. Transcript Keyword Analysis (10 mins)

**Goal:** Test if transcript keywords appear in expected segment types

- [ ] Load `data/cache/motd_2025-26_2025-11-01/transcript.json`
- [ ] For each segment type, check keyword presence:

  **Studio intro keywords:** `["let's look at", "coming up", "now", "next"]`
  - Get transcript segments overlapping studio_intro scenes from ground truth
  - Count how many contain keywords
  - Calculate precision: What % of keyword matches are studio_intro?

  **Interview keywords:** `["speak to", "join us", "after the game", "thoughts on"]`
  - Get transcript segments overlapping interview scenes
  - Count keyword presence
  - Calculate precision

  **Studio analysis keywords:** `["alright", "right", "moving on", "what did you make"]`
  - Get transcript segments overlapping studio_analysis scenes
  - Count keyword presence
  - Calculate precision

- [ ] Document findings:
  ```markdown
  ## Transcript Keyword Validation

  | Segment Type | Keywords Tested | Precision | Recall | Decision |
  |--------------|----------------|-----------|---------|----------|
  | Studio intro | 4 keywords | XX% | XX% | Use/Skip |
  | Interviews | 4 keywords | XX% | XX% | Use/Skip |
  | Studio analysis | 4 keywords | XX% | XX% | Use/Skip |

  **Recommendation:** Transcript keywords are [strong/moderate/weak] signal
  ```
- [ ] **Commit:** `test: Validate transcript keyword effectiveness for segment classification`

**Success criteria:** At least 1 segment type has >70% keyword precision

---

### 4. Sequencing Pattern Validation (5 mins)

**Goal:** Verify matches follow expected structure

- [ ] For each of 7 matches, check sequence from ground truth labels:
  - Expected: studio_intro → highlights → interviews → studio_analysis
  - Verify all 7 matches follow this pattern
- [ ] Document violations:
  - Any match where sequence differs?
  - Any segments skipped? (e.g., no interviews for match X)
  - Any segments out of order?
- [ ] Calculate pattern confidence:
  - X/7 matches follow expected sequence = XX% reliability
- [ ] **Decision:** Can sequencing be used as validation/boosting signal?
- [ ] **Commit:** `docs: Validate match segment sequencing patterns (X/7 matches conform)`

**Success criteria:** ≥6/7 matches follow expected sequence

---

## Validation Report

After completing steps 1-4, create summary report:

### `docs/ground_truth/validation_report.md`

```markdown
# Segment Classification: Assumption Validation Report

**Date:** [DATE]
**Dataset:** 39 labeled scenes from motd_2025-26_2025-11-01

## Summary

| Signal | Strength | Use in Classifier? | Priority |
|--------|----------|-------------------|----------|
| FT graphic detection | [Strong/Moderate/Weak] | YES/NO | 1st/2nd/3rd |
| OCR presence (scoreboards) | [Strong/Moderate/Weak] | YES/NO | 1st/2nd/3rd |
| Duration ranges | [Strong/Moderate/Weak] | YES/NO | 1st/2nd/3rd |
| Transcript keywords | [Strong/Moderate/Weak] | YES/NO | 1st/2nd/3rd |
| Sequencing pattern | [Strong/Moderate/Weak] | YES/NO | 1st/2nd/3rd |

## Detailed Findings

[Copy validation results from steps 1-4]

## Recommendations for 011c-3

**Rules to implement:**
1. [Rule name] - [Priority] - [Confidence threshold]
2. [Rule name] - [Priority] - [Confidence threshold]
...

**Rules to skip:**
- [Rule name] - [Reason: e.g., low precision, high overlap]

**Visual recognition needed?**
- YES/NO - [Rationale]

## Decision

- [ ] **Continue to 011c-3** - At least 2-3 validated rules
- [ ] **Add visual recognition** - Heuristics weak, need image classification
- [ ] **Pivot to Task 013** - Defer to ML approach
```

- [ ] **Commit:** `docs: Create assumption validation report for segment classification`

---

## Success Criteria

- [ ] FT graphic detection validated (7/7 detected, timestamps accurate)
- [ ] At least 2-3 classification signals validated as effective
- [ ] Config file updated with actual duration thresholds from ground truth
- [ ] Validation report created with clear recommendation
- [ ] Decision documented: proceed to 011c-3, add visual recognition, or pivot?

## Next Steps

**If ≥3 signals validated (strong confidence):**
→ Proceed to [011c-3: Classifier Implementation](011c-3-classifier-implementation.md)

**If 2 signals validated (moderate confidence):**
→ Proceed to 011c-3 with caveat: May need visual recognition in future iteration

**If <2 signals validated (weak confidence):**
→ Pause and discuss:
  - Try visual recognition pilot (classify 10 scenes with simple image model)
  - Defer to Task 013 (ML approach with vision model)
  - Redefine segment types (current definitions may not be observable)

## Notes

- **Precision vs Recall tradeoff:** Better to have low recall (miss some scenes) with high precision (correct when we classify) than high recall with low precision (many errors)
- **Visual recognition consideration:** If heuristics are weak, simple image classification (studio vs pitch) could be added before 011c-3
- **Config thresholds:** Use ±10% margin around ground truth ranges to avoid overfitting to single episode
- **Keyword case-insensitivity:** Transcript may have inconsistent capitalization

## Related Tasks

- [011c-1: Ground Truth Dataset Creation](011c-1-ground-truth-dataset.md) - Created the labeled dataset
- [011c-3: Classifier Implementation](011c-3-classifier-implementation.md) - Implements validated rules
- [011b-2: Frame Extraction Fix](011b-2-frame-extraction-fix.md) - Produced OCR results being validated
