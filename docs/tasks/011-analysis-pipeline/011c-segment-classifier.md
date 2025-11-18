# Task 011c: Segment Classifier (Epic)

**Status:** Split into 3 sub-tasks
**Estimated Time:** 2-3 hours total (across 3 sub-tasks)

## Sub-Tasks

1. **[011c-1: Ground Truth Dataset Creation](011c-1-ground-truth-dataset.md)** - 60 mins
   - Create labeled dataset of 39 strategic scenes
   - Analyze patterns to validate classification assumptions
   - Deliverable: Ground truth labels + pattern analysis

2. **[011c-2: Assumption Validation](011c-2-assumption-validation.md)** - 30 mins
   - Validate specific rules (FT graphics, duration, keywords, sequencing)
   - Update config with validated thresholds
   - Deliverable: Validation report + decision on which rules to implement

3. **[011c-3: Classifier Implementation](011c-3-classifier-implementation.md)** - 90 mins
   - Implement segment classifier using validated rules only
   - Test on ground truth (target >85% accuracy)
   - Deliverable: Working classifier + accuracy report

---

## Quick Context

**Parent Task:** [011-analysis-pipeline](README.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Scene](../../domain/README.md#scene), [OCR Scoreboard](../../domain/README.md#scoreboard)
**Business Rules:** [Segment Classification Hierarchy](../../domain/business_rules.md#rule-5-segment-classification-hierarchy)

**Why This Matters:** Segment classification enables answering the core research question: "Do some teams get more analysis than others?" Total airtime alone isn't sufficient - we need to distinguish between highlights (match footage) and studio analysis (pundit discussion) to measure quality of coverage, not just quantity.

**Key Insight:** Each match typically has all 4 segment types in sequence:
1. Studio intro (7-11s) - Preview
2. Highlights (5-10min) - Match footage
3. Interviews (45-90s) - Player/manager quotes
4. Studio analysis (2-5min) - Pundit discussion

Duration varies by match importance - "big six" matches get longer analysis, lower-table matches get minimal studio time.

See [Visual Patterns](../../domain/visual_patterns.md) for detailed episode structure and timing examples.

---

## Overview

This epic implements segment classification through a **validation-driven approach**:
- **011c-1** creates ground truth → validates assumptions
- **011c-2** tests specific rules → identifies what works
- **011c-3** implements only validated rules → avoids wasted effort

**Traditional approach (avoided):**
1. Implement all rules from task file
2. Test on data
3. Debug why it doesn't work
4. Discover assumptions were wrong
5. Rewrite classifier

**Our approach:**
1. Label ground truth first (011c-1)
2. Validate which rules actually work (011c-2)
3. Implement only validated rules (011c-3)
4. Achieve >85% accuracy immediately

---

## Key Findings from Research

**Data available:**
- 1,229 scenes total (vs. 810 originally estimated)
- 394 scenes with OCR (32.1% coverage across all 7 matches)
- 1,773 transcript segments with word-level timing
- FT graphic detection working reliably (from 011b)

**Transition discovery:**
- 39 "SECOND HALF" transition scenes documented in visual_patterns.md
- Duration: 0.08s - 22.64s (highly variable)
- **Decision:** Use as boundary markers, NOT separate segment type
- Rationale: Too brief/inconsistent for meaningful analysis

**Segment types (7 total):**
1. `intro` - Episode opening (00:00-00:50)
2. `studio_intro` - Host introducing next match
3. `highlights` - Match footage with scoreboard
4. `interviews` - Post-match player/manager interviews
5. `studio_analysis` - Pundit discussion
6. `interlude` - MOTD2 promo/ads (52:01-52:47)
7. `outro` - League table review, closing montage

---

## Objective

Implement a robust multi-signal classifier to categorize each scene into one of 7 segment types, achieving >85% accuracy on ground truth dataset.

## Prerequisites

- [x] Task 011b complete (frame extraction, OCR, FT validation working)
- [x] Processed data available: scenes.json, ocr_results.json, transcript.json
- [x] Visual patterns documented: [visual_patterns.md](../../domain/visual_patterns.md)
- [ ] Understanding of [Segment Types](../../domain/README.md#segment-types)

## Target Accuracy

>85% segment classification accuracy on ground truth dataset (validated in 011f on full episode)

## Workflow

### Phase 1: Ground Truth Creation (011c-1)
**Goal:** Create labeled dataset and validate assumptions

**Input:** Raw data (scenes, OCR, transcript)
**Output:** 39 labeled scenes + pattern analysis
**Decision Point:** Do assumptions hold? Continue to 011c-2 or pivot?

### Phase 2: Assumption Validation (011c-2)
**Goal:** Test specific rules against ground truth

**Input:** Labeled dataset from 011c-1
**Output:** Validation report listing which rules work
**Decision Point:** ≥2-3 rules validated? Continue to 011c-3 or add visual recognition?

### Phase 3: Classifier Implementation (011c-3)
**Goal:** Build classifier with validated rules

**Input:** Validation report from 011c-2
**Output:** Working classifier + accuracy report
**Decision Point:** Accuracy >85%? Proceed to 011d or iterate?

---

## Classification Signals Available

Based on research, these signals are available for classification:

**Strong signals (high confidence):**
1. **FT graphic detection** - Reliably marks end of highlights
2. **Scoreboard OCR presence** - 394 scenes with team OCR
3. **Sequencing patterns** - Matches follow predictable structure

**Moderate signals (medium confidence):**
4. **Duration ranges** - Segment types have characteristic lengths
5. **Transcript keywords** - Certain phrases indicate segment type

**Weak signals (low confidence):**
6. **Position in episode** - Intro always first, outro always last
7. **Scene frame count** - More frames = longer, more important

**Future enhancements (Task 013):**
- Visual recognition (studio vs pitch detection)
- Audio features (crowd noise, music, commentary patterns)

---

## Segment Type Definitions

### 1. `intro`
Episode opening sequence (MOTD theme, graphics)
- **Duration**: ~50 seconds (consistent)
- **Signals**: First scenes of episode, distinctive music
- **Visual**: MOTD branding, spinning logos, host introduction

### 2. `studio_intro`
Host introducing next match from studio
- **Duration**: 7-20 seconds typically
- **Signals**: Short duration + team mentions + before highlights
- **Visual**: Wide studio shot, host at desk

### 3. `highlights`
Match footage with scoreboards and FT graphics
- **Duration**: 5-10 minutes typically
- **Signals**: Scoreboard OCR + FT graphic at end
- **Visual**: Football pitch, players, scoreboard graphics

### 4. `interviews`
Post-match player/manager interviews
- **Duration**: 45-90 seconds typically
- **Signals**: After FT graphic + interview keywords + before studio analysis
- **Visual**: Interview backdrop with sponsor logos, name captions

### 5. `studio_analysis`
Post-match pundit discussion
- **Duration**: 2-5 minutes typically
- **Signals**: After interviews + transition keywords + team discussion
- **Visual**: Wide studio shot, pundits discussing

### 6. `interlude`
MOTD2 promo and upcoming football adverts
- **Duration**: ~46 seconds (52:01-52:47)
- **Signals**: Mid-episode position, promotional content
- **Visual**: Graphics showing upcoming matches/shows

### 7. `outro`
League table review and closing montage
- **Duration**: ~1 minute (82:57-83:59)
- **Signals**: End of episode, league table graphics
- **Visual**: League table, closing montage, end credits

---

## Success Criteria (Epic-Level)

- [ ] Ground truth dataset created (39 labeled scenes)
- [ ] Pattern analysis validates at least 2-3 classification signals
- [ ] Assumption validation report documents which rules work
- [ ] Config file updated with validated thresholds
- [ ] SegmentClassifier implemented with validated rules only
- [ ] Unit tests passing (>80% coverage)
- [ ] Ground truth accuracy >85%
- [ ] Full dataset classified (1,229 scenes)
- [ ] Spot-check validation >80% correct
- [ ] Ready for Task 011d (match boundary detection)

---

## Deliverables (Across All Sub-Tasks)

### Documentation
- `docs/ground_truth/scene_mapping.md` - Timestamp → scene_id mapping
- `docs/ground_truth/labeling_template.md` - 39 scenes with labels
- `docs/ground_truth/analysis.md` - Pattern analysis findings
- `docs/ground_truth/validation_report.md` - Rule validation results

### Code
- `src/motd/analysis/__init__.py`
- `src/motd/analysis/segment_classifier.py`
- `tests/unit/analysis/test_segment_classifier.py`

### Configuration
- Updated `config/config.yaml` with validated segment classification thresholds

### Data
- `data/cache/motd_2025-26_2025-11-01/classified_scenes.json` - Full dataset classified

---

## Edge Cases to Handle

- [ ] **Intro sequence (00:00-00:50)**: Classify as `intro` type
- [ ] **MOTD 2 interlude (52:01-52:47)**: Classify as `interlude` type
- [ ] **Outro/league table (82:57+)**: Classify as `outro` type
- [ ] **Transition scenes (<2s)**: May be part of highlights or separate
- [ ] **VAR reviews**: Remain part of highlights
- [ ] **Formation graphics**: Part of highlights
- [ ] **Missing OCR**: Fallback to duration + transcript + sequencing
- [ ] **Missing transcript**: Fallback to OCR + duration

---

## Notes

- **Validation-driven approach prevents wasted effort** - Don't code until rules are validated
- **User labeling is critical** - Your visual cues inform which signals to prioritize
- **Start simple, iterate** - Implement 2-3 validated rules first, then add more
- **Prioritize precision over recall** - Better to be unsure than wrong
- **Low confidence (<0.6) = flag for manual review**
- **Visual recognition is optional** - Only add if heuristics are weak
- **011f will validate on full episode** - Current task only tests on single episode

---

## Next Task

[011d: Match Boundary Detection](011d-match-boundary-detector.md) - Uses classified scenes to detect match boundaries

---

## Related Tasks

- [011b-2: Frame Extraction Fix & FT Validation](011b-2-frame-extraction-fix.md) - Produced the data we're classifying
- [011d: Match Boundary Detection](011d-match-boundary-detector.md) - Consumes classified scenes
- [011f: Validation & Accuracy Testing](011f-validation-accuracy.md) - Validates classifier on full episode
- [013: ML Enhancement](../013-ml-enhancements/) - Future ML approach (if needed)
