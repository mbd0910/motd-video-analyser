# Task 011c-1: Ground Truth Dataset Creation

## Quick Context

**Parent Task:** [011c-segment-classifier](011c-segment-classifier.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Scene](../../domain/README.md#scene), [Visual Patterns](../../domain/visual_patterns.md)
**Business Rules:** N/A (research and labeling task)

**Why This Matters:** Ground truth labeling enables validation-driven development. Instead of guessing which classification rules will work, we validate them against real data first. This prevents building a classifier based on incorrect assumptions and saves hours of debugging. The labeled dataset also becomes a reusable test set for future ML approaches (Task 013).

**Key Insight:** Visual_patterns.md already documents all segment boundaries with timestamps (manual reconnaissance from earlier tasks). We'll map those to scene IDs in our current processed data, then strategically sample 39 scenes for labeling to validate all segment types.

See [Visual Patterns](../../domain/visual_patterns.md) for detailed episode structure and ground truth timestamps.

---

## Objective

Create a labeled dataset of 39 strategic scenes covering all 7 segment types, then analyze patterns to determine which classification heuristics (duration, keywords, sequencing) will work before implementing code.

## Prerequisites

- [x] Task 011b complete (frame extraction, OCR, FT validation working)
- [x] Processed data available: `data/cache/motd_2025-26_2025-11-01/scenes.json`, `ocr_results.json`, `transcript.json`
- [x] Visual patterns documented: [visual_patterns.md](../../domain/visual_patterns.md) with ground truth timestamps
- [ ] Understanding of [Segment Types](../../domain/README.md#segment-types) (7 types: intro, studio_intro, highlights, interviews, studio_analysis, interlude, outro)

## Estimated Time

60 minutes (30 mins labeling, 30 mins analysis)

## Deliverables

1. **`docs/ground_truth/scene_mapping.md`** - Maps visual_patterns.md timestamps to scene IDs
2. **`docs/ground_truth/labeling_template.md`** - 39 scenes with user labels
3. **`docs/ground_truth/analysis.md`** - Pattern analysis findings

## Implementation Steps

### 1. Create Scene Mapping (10 mins)

- [x] Create `docs/ground_truth/` directory
- [x] Load `data/cache/motd_2025-26_2025-11-01/scenes.json`
- [x] Map key timestamps from visual_patterns.md to scene IDs:
  - Intro ends: 00:00:50
  - Match 1-7: studio_intro start, highlights start, interviews start, studio_analysis start
  - Interlude: 52:01-52:47
  - Outro: 82:57-83:59
- [x] Create mapping document with table:
  | Segment | Timestamp | Scene ID | Notes |
  |---------|-----------|----------|-------|
  | Match 1 Studio Intro | 00:00:50 | scene_XXX | Host introducing match |
- [x] **Commit:** `docs: Map visual_patterns timestamps to scene IDs for ground truth labeling`

### 2. Create Labeling Template (15 mins)

- [x] Select 39 strategic scenes for labeling:
  - **Intro**: 2 scenes (beginning + end of intro sequence)
  - **Studio Intro**: 7 scenes (one per match)
  - **Highlights**: 8 scenes (1-2 per match, prioritize OCR presence)
  - **Interviews**: 5 scenes (matches 1-5)
  - **Studio Analysis**: 7 scenes (one per match)
  - **Interlude**: 2 scenes (MOTD 2 promo)
  - **Outro**: 2 scenes (league table review)
  - **Transitions** (for comparison): 6 "SECOND HALF" scenes
- [x] For each scene, extract from data:
  - scene_id
  - timestamp (MM:SS format)
  - duration (seconds)
  - frames_available (count)
  - has_ocr (yes/no)
  - ocr_teams (if OCR present)
  - transcript_snippet (first 60 chars of overlapping text)
  - frame_files (list of frame filenames for visual reference)
- [x] Create template with user-fillable fields:
  ```markdown
  ### Scene XXX - [MM:SS] (duration)
  **Pre-filled data:**
  - Frames available: X
  - Has OCR: YES/NO
  - OCR teams: [teams if applicable]
  - Transcript: "..."
  - Frame files: [list]

  **Your labels:**
  - Segment type: ___________ (intro/studio_intro/highlights/interviews/studio_analysis/interlude/outro)
  - Confidence: ___________ (high/medium/low)
  - Visual cues: ___________ (what made it obvious?)
  - Notes: ___________
  ```
- [x] **Commit:** `docs: Create ground truth labeling template with 39 strategic scenes`

### 3. User Labeling Session (30 mins - user time)

- [x] User fills in template for all 38 scenes (39 targeted, 38 actual)
- [x] User views frames in `data/cache/motd_2025-26_2025-11-01/frames/` as needed to verify
- [x] User documents visual cues used to determine segment type
- [x] User notes confidence level for each label
- [x] User identifies any ambiguous or edge cases
- [x] **Commit:** `docs: Complete ground truth labels for segment classification`

**Guidance for user:**
- High confidence: Immediately obvious from frame/transcript/OCR
- Medium confidence: Required checking multiple signals
- Low confidence: Uncertain, could be multiple types
- Visual cues examples: "scoreboard visible", "wide studio shot", "interview backdrop with sponsor logos", "host at desk"

### 4. Pattern Analysis (15 mins)

- [x] Load user-labeled data
- [x] Analyze duration patterns per segment type:
  - Calculate min, max, median, average duration for each type
  - Compare against task file assumptions:
    - Studio intro: claimed 7-11s
    - Interviews: claimed 45-90s
    - Studio analysis: claimed 2-5 mins
- [x] Analyze transcript keyword presence:
  - Studio intro: Check for "let's look at", "coming up", "now", "next"
  - Interviews: Check for "speak to", "join us", "after the game"
  - Studio analysis: Check for "alright", "right", "moving on", "what did you make"
- [x] Validate sequencing assumption:
  - For each match, verify order: studio_intro → highlights → interviews → studio_analysis
  - Document any violations
- [x] Analyze OCR correlation:
  - Do all "highlights" labels have OCR present?
  - Do non-highlights labels lack OCR?
- [x] Assess transition scenes:
  - Are they a distinct segment type or just boundaries?
  - Can they be auto-detected (duration + position)?
- [x] Document findings in `docs/ground_truth/analysis.md` with:
  - Duration ranges per segment type (actual vs. assumed)
  - Keyword effectiveness (do they appear where expected?)
  - Sequencing validation (does pattern hold?)
  - OCR correlation (precision/recall)
  - Transition assessment (separate type or boundary marker?)
  - **Recommendation:** Which rules should we implement in 011c-2?
- [x] **Commit:** `docs: Analyze ground truth patterns and validate classification assumptions`

## Success Criteria

- [x] All 39 scenes labeled with segment type and confidence level (38 actual)
- [x] Pattern analysis identifies which heuristics will work
- [x] At least 2-3 classification signals validated (OCR presence, FT graphics, sequencing)
- [x] Decision documented:
  - ✅ Continue to 011c-2 (assumption validation)
  - 3 strong signals validated: OCR, FT graphics, sequencing pattern

## Next Steps

**If assumptions validated (2-3+ signals work):**
→ Proceed to [011c-2: Assumption Validation](011c-2-assumption-validation.md)

**If heuristics look weak (<2 signals work):**
→ Consider visual recognition approach (pitch vs studio detection) or defer to Task 013 (ML approach)

**If segment types need refinement:**
→ Update [Segment Types](../../domain/README.md#segment-types) glossary and revise labeling template

## Notes

- **Transition scenes included for comparison only** - not a primary segment type
- **OCR presence is a strong signal but not perfect** - some highlights scenes may lack OCR if no scoreboard visible
- **Transcript may have gaps** - music-only segments (intro, transitions) won't have transcript
- **Low confidence labels are valuable** - they reveal ambiguous cases that classifier may struggle with
- **User's visual cues are gold** - they inform what signals to prioritize in classifier

## Related Tasks

- [011b-2: Frame Extraction Fix & FT Validation](011b-2-frame-extraction-fix.md) - Produced the processed data we're labeling
- [011c-2: Assumption Validation](011c-2-assumption-validation.md) - Next task (validates specific rules)
- [011c-3: Classifier Implementation](011c-3-classifier-implementation.md) - Final implementation (uses validated rules)
