# Business Rules

**Purpose:** This document codifies the core business logic and validation rules used throughout the MOTD Analyser pipeline. These rules are implemented in code but documented here for clarity and reference.

**Last Updated:** 2025-11-18 (condensed to focus on business logic, not implementation details)

---

## Table of Contents

1. [Rule 1: FT Graphic Validation](#rule-1-ft-graphic-validation)
2. [Rule 2: Episode Manifest Constraint](#rule-2-episode-manifest-constraint)
3. [Rule 3: Opponent Inference from Fixtures](#rule-3-opponent-inference-from-fixtures)
4. [Rule 4: 100% Running Order Accuracy Requirement](#rule-4-100-running-order-accuracy-requirement)
5. [Rule 5: Segment Classification Hierarchy](#rule-5-segment-classification-hierarchy)

---

## Rule 1: FT Graphic Validation

### Source Code
**File:** [src/motd/ocr/reader.py:180-234](../../src/motd/ocr/reader.py#L180-L234)
**Method:** `validate_ft_graphic()`

### Definition

A frame contains a valid FT (full-time) graphic if **ALL** requirements are met:

1. **≥1 team detected** via OCR (2 teams preferred, 1 team + fixture inference allowed)
2. **Score pattern present** - Matches `\b\d+\s*[-–—|]?\s*\d+\b` (e.g., "2-1", "3 | 0", "2 0")
3. **"FT" text present** - One of: `FT`, `FULL TIME`, `FULL-TIME`, `FULLTIME`

**Score pattern flexibility:** BBC uses pipe `|` as separator, but OCR may read it as hyphen, space, en-dash, or em-dash. Regex handles all variants.

### Why This Rule Exists

FT graphics are the gold standard for team detection, but we must filter out false positives:

**Filtered Out:**
- **Possession bars** - Have numbers ("65% 35%") but no "FT" text
- **Player statistics** - Have numbers/names but no score pattern
- **Formation graphics** - Have team names but no scores or "FT"
- **Half-time scores** - Show "HT" instead of "FT"

**Allowed Through:**
- Clean FT graphics with both teams, score, and "FT" label ✓
- FT graphics with only 1 team (triggers opponent inference) ✓

### Validation Scenarios

**Valid Cases:**
- 2 teams + score (e.g., "2 | 0") + "FT" text → **Pass**
- 1 team + score + "FT" text → **Pass** (triggers opponent inference per Rule 3)

**Invalid Cases:**
- Teams + numbers but no "FT" → **Fail** (possession bar: "Liverpool 65 35 Aston Villa")
- Team + numbers but no score pattern → **Fail** (player stats: "Liverpool Salah 11")
- Teams but no score/FT → **Fail** (formation graphic)
- Teams + score + "HT" → **Fail** (half-time, not full-time)

### Measured Accuracy

**Task 011b-2 ground truth validation:**
- **False Positive Rate:** <5% (very few non-FT graphics pass all 3 requirements)
- **False Negative Rate:** ~12% (valid FT graphics rejected due to OCR failures)
  - Common cause: Non-bold team name not detected (away team in lighter font)
  - Mitigation: Opponent inference (Rule 3) recovers ~70% of these cases

### Edge Cases

**Pipe Character Variants:**
BBC uses `|` but OCR may read as: hyphen `-`, space, letter `I/l`, em-dash `—`. Regex handles all.

**Multiple Scores in Frame:**
If FT graphic overlaid on replay showing different score, validation passes if ANY score pattern matches.

**No Teams Detected:**
If OCR finds score + "FT" but no teams → Validation fails (need ≥1 team for match identification).

---

## Rule 2: Episode Manifest Constraint

### Source Code
**File:** [src/motd/ocr/fixture_matcher.py:98-140](../../src/motd/ocr/fixture_matcher.py#L98-L140)
**Methods:** `get_expected_fixtures()`, `get_expected_teams()`

### Definition

All OCR-detected teams MUST be validated against the episode's `expected_matches` list before being accepted.

**Episode Manifest Structure:**
```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "expected_matches": [
    "2025-11-01-liverpool-astonvilla",
    "2025-11-01-burnley-arsenal",
    ...
  ]
}
```

**Data File:** `data/episodes/episode_manifest.json`

### Why This Rule Exists

**Problem:** MOTD shows content from matches NOT in the current episode.

**Common False Positive Sources:**
1. Replays from other matches ("Remember this goal from last week...")
2. MOTD2 promos (clips from Sunday's episode with different fixtures)
3. FA Cup/Champions League highlights (midweek matches)
4. Historical clips ("The last time these teams met...")
5. Upcoming fixtures preview (graphics showing next week's matches)

**Without Episode Manifest:**
- OCR detects "Manchester United" (valid PL team)
- Pipeline accepts it → Running order corrupted (8 matches detected instead of 7)
- Downstream analysis fails (can't map 8 matches to 7 expected fixtures)

**With Episode Manifest:**
- OCR detects "Manchester United"
- Validation checks: Is Man Utd in expected_matches? → No (playing on Sky Sports this week)
- Action: Flag as potential false positive, require FT validation + fixture pairing

### Validation Flow

1. Load expected matches for episode → 7 fixture IDs
2. Extract expected team names → 14 teams (7 matches × 2 teams)
3. Check if OCR team in expected list:
   - **Yes:** Boost confidence +10% (team SHOULD appear in episode)
   - **No:** Flag as potential false positive (replay/promo)

### Confidence Boost Mechanism

Teams in `expected_matches` receive +10% confidence boost:
- Base OCR confidence: 0.85
- After boost: min(0.85 + 0.10, 1.0) = 0.95 (capped at 1.0)

**Why boost confidence?**
- Expected teams more likely correct (they SHOULD appear)
- Helps distinguish similar names ("Manchester City" vs "Manchester United")
- Prioritizes expected teams in ambiguous cases

### Search Space Reduction

**Without Manifest:** OCR fuzzy-matches against all 20 PL teams
**With Manifest:** OCR fuzzy-matches against only 14 expected teams (30% reduction)

**Example:**
OCR reads "LIVRPOOL" (typo or OCR error)
- Without manifest: Could match Liverpool (0.87) or Everton (0.45) - ambiguous
- With manifest: Only Liverpool in expected_teams → Clear winner

### Edge Cases

**Unexpected Team Detected:**
- **Barcelona:** Reject immediately (not a PL team)
- **Man Utd (PL team, not in episode):** Check if FT validation passes
  - If yes: Flag as unexpected but valid (MOTD2 promo/replay)
  - If no: Reject (likely commentary mention, crowd banner)
- **Tottenham (PL team, not in manifest but actually in episode):** Human review required - likely manifest error

---

## Rule 3: Opponent Inference from Fixtures

### Source Code
**File:** [src/motd/ocr/scene_processor.py](../../src/motd/ocr/scene_processor.py) (opponent inference logic)
**Related:** [src/motd/ocr/fixture_matcher.py](../../src/motd/ocr/fixture_matcher.py) (fixture lookup)

### Definition

If OCR detects **exactly 1 team** in an FT graphic AND FT validation passes (score + "FT" present), infer the opponent from the episode's fixture list.

**Trigger Conditions:**
1. FT validation passes (Rule 1) ✓
2. Exactly 1 team detected via OCR
3. Detected team exists in expected_matches ✓

**Inference Process:**
1. Load expected fixtures for episode
2. Find fixture containing detected team (as home or away)
3. Extract opponent (the other team in that fixture)
4. Add opponent with confidence 0.75, tagged as `inferred_from_fixture`

### Why This Rule Exists

**Problem:** OCR frequently fails to read non-bold team names.

**BBC FT Graphic Typography:**
- **Home team (bold text):** OCR reads reliably (95%+ accuracy)
- **Away team (regular text):** OCR struggles on light backgrounds (60-70% accuracy)

**Example:**
```
┌─────────────────────────────┐
│  Liverpool    2              │  ← Bold (OCR reads)
│  Aston Villa  0    FT        │  ← Regular (OCR often misses)
└─────────────────────────────┘
```

OCR reads: "Liverpool 2 0 FT" but misses "Aston Villa"

**Without Opponent Inference:**
- Frame rejected (ideally wants 2 teams)
- Valid FT graphic wasted
- Running order gaps (missing match boundary)

**With Opponent Inference:**
- Frame accepted (1 team + score + FT = valid)
- Lookup: Liverpool in which fixture? → liverpool-astonvilla
- Infer: Opponent = Aston Villa
- Result: Both teams identified (1 via OCR, 1 via inference)

### Confidence Levels

**OCR-Detected Team:** 0.85-0.95 (high - directly read from frame), source: `ocr`
**Inferred Opponent:** 0.75 (lower - derived, not observed), source: `inferred_from_fixture`

**Why lower confidence?**
- Not directly validated by OCR
- Assumes episode manifest correct
- Assumes fixture pairing accurate
- Potential error if same team in multiple fixtures (rare)

### Example Scenarios

**Successful Inference:**
- OCR: "Liverpool 2 0 FT" (missing Aston Villa)
- Fixtures: liverpool-astonvilla
- Result: Infer "Aston Villa" as opponent (confidence 0.75)

**Inference Fails:**
- OCR: "Manchester United" (not in expected_matches)
- Result: Cannot infer opponent → Reject frame

**No Inference Needed:**
- OCR: "Liverpool 2 0 Aston Villa FT" (both teams detected)
- Result: Both teams via OCR (confidence 0.92, 0.89)

### Measured Impact

**Task 011b-2 results:**
- **Before opponent inference:** 35% of FT graphics rejected (single team detected)
- **After opponent inference:** 12% of FT graphics rejected (irreparable OCR failures)
- **Recovery rate:** ~70% of single-team detections successfully paired
- **Accuracy:** Ground truth confirms 95%+ accuracy for inferences

### Edge Cases

**Same Team in Multiple Fixtures:**
Rare case (replays/postponements) - same team twice in one episode. Inference ambiguous - fallback to score validation or timestamp context.

**Weakly Detected Second Team:**
If OCR detects 2 teams but second has confidence <0.70, treat as undetected and infer from fixtures (0.75 confidence > 0.62 weak OCR).

---

## Rule 4: 100% Running Order Accuracy Requirement

### Source
**Task:** [011d-implement-match-boundary-detector.md](../tasks/011-analysis-pipeline/011d-implement-match-boundary-detector.md)
**Requirement:** "100% running order accuracy (7/7 matches correct order)"

### Definition

Match boundary detection MUST achieve **100% running order accuracy** before proceeding to downstream analysis (Task 011e+).

**Running Order Accuracy:**
- All matches correctly identified AND sequenced
- Example: 7/7 matches = 100% ✓
- Example: 6/7 matches = 86% ✗ (insufficient)

**100% Threshold:**
- All matches in episode detected
- All matches in correct editorial sequence
- No false positives (extra matches)
- No false negatives (missing matches)

### Why 100% Required

**Business Context:**
Running order is the **editorial sequence** MOTD chose - NOT chronological by kickoff. Reflects editorial decisions about match importance.

**Research Questions Depending on Running Order:**
1. "Are certain teams consistently shown first?" (primacy bias)
2. "Are certain teams consistently shown last?" (recency bias)
3. "Does running order correlate with match excitement?"
4. "Do 'big six' teams get preferential placement?"

**Why < 100% is Unacceptable:**

**Example: 86% Accuracy (6/7 correct)**
- 1 wrong boundary: Match 3 ends 2 minutes too early, Match 4 starts 2 minutes too early
- **Impact:** Match 3 loses 2 min (highlights truncated), Match 4 gains 2 min (wrong content)
- **Cascading:** 1 wrong boundary = 2 matches corrupted
- **Result:** If Match 3 = Liverpool, Match 4 = Arsenal → Airtime calculations wrong for BOTH

**Scale:**
- 1 wrong boundary = 2 matches affected
- 7 matches × 14% error = 2-3 matches corrupted
- **28-43% of episode data unreliable**

### Validation Criteria

1. Load ground truth running order (manually verified by watching episode)
2. Compare against pipeline output (automated detection)
3. Check: Does each position match expected fixture ID?
4. Calculate accuracy: correct_matches / total_matches
5. Require: accuracy == 1.0 (100%)

If < 100%: **HALT PIPELINE.** Fix boundary detection before proceeding to Task 011e.

### Common Failure Modes

**Missing Match Boundary:**
- Detected: 6 matches (should be 7)
- Cause: FT graphic missed (short visibility, OCR failure)
- Impact: 2 matches merged into 1

**False Positive Boundary:**
- Detected: 8 matches (should be 7)
- Cause: Replay FT graphic detected (MOTD2 promo)
- Impact: Match incorrectly split into 2

**Correct Count, Wrong Order:**
- Detected: 7 matches, positions swapped
- Cause: FT graphic timestamps close together
- Impact: Running order analysis invalid

### Remediation Process

If accuracy < 100%:
1. **Identify failure mode:** Compare ground truth vs detected (which position mismatched?)
2. **Review FT detections:** Which FT graphics detected/missed? Check frame sampling.
3. **Adjust parameters:**
   - Lower FT validation threshold (if missing matches)
   - Increase frame sampling rate (if short FT graphics missed)
   - Refine fixture validation (if false positives)
4. **Re-run and re-validate:** Repeat until 100% achieved

### Exception: Partial Episodes

If episode cut short (e.g., 5 of 7 matches shown due to broadcast overrun):
- Update ground truth to reflect actual matches
- Update expected_matches in episode manifest
- Validate against revised ground truth (5/5 = 100%)

**Do NOT lower accuracy threshold** - always require 100% of EXPECTED matches.

---

## Rule 5: Segment Classification Hierarchy

### Source
**Task:** [011c-implement-segment-classifier.md](../tasks/011-analysis-pipeline/011c-implement-segment-classifier.md)
**Classification Logic:** Multi-signal decision tree

### Definition

Classify scenes into 4 segment types (`studio_intro`, `highlights`, `interviews`, `studio_analysis`) using hierarchical signals prioritized by reliability:

**Signal Priority (Highest to Lowest):**
1. **OCR Scoreboard Detection** (definitive) - If scoreboard present → `highlights`
2. **Transcript Team Mentions** (strong) - Frequency indicates highlights vs analysis
3. **Duration Pattern** (weak, tie-breaker) - Typical lengths for each type

### Why This Hierarchy

**Scoreboard is Definitive:**
- Scoreboard ONLY appears during match footage
- Never in studio segments, interviews, or analysis
- If scoreboard detected → 100% certainty it's `highlights`

**Transcript is Strong but Ambiguous:**
- High mentions (>5/min): Could be highlights OR studio analysis
- Medium mentions (2-5/min): Could be interviews OR analysis
- Low mentions (<2/min): Could be studio intro OR interviews

**Duration is Weak:**
- Segments vary significantly by match importance
- Studio intro: usually 7-11s, but can be 5-15s
- Interviews: usually 45-90s, but can be 30-120s
- Studio analysis: usually 2-5 min, but controversial matches get 7-10 min

### Classification Logic

**Step 1: Check Scoreboard (Highest Priority)**
- Sample 3-5 frames from scene (first, middle, last)
- If scoreboard detected (OCR confidence ≥0.70) → **HIGHLIGHTS** (definitive)

**Step 2: Analyze Transcript (Strong Signal)**
- Count team mentions in scene transcript
- Calculate mentions per minute

**Step 3: Apply Duration Pattern (Tie-Breaker)**
- High mentions (>5/min):
  - Duration >5 min → **HIGHLIGHTS** (scoreboard missed, but long + high mentions)
  - Duration 2-5 min → **STUDIO_ANALYSIS**
- Medium mentions (2-5/min):
  - Duration 45-90s → **INTERVIEWS**
  - Duration ≥2 min → **STUDIO_ANALYSIS**
- Low mentions (<2/min):
  - Duration 7-11s → **STUDIO_INTRO**
  - Duration 45-90s → **INTERVIEWS** (brief quote)
  - Duration <15s → **STUDIO_INTRO**

**Default Fallback:** If no clear match → **STUDIO_ANALYSIS** (most common non-highlights segment)

### Signal Thresholds

**OCR Scoreboard:**
- Detected in ≥1 sample frame
- Sample rate: 3-5 frames per scene
- Confidence: ≥0.70

**Transcript Team Mentions:**
- High: >5 mentions/minute
- Medium: 2-5 mentions/minute
- Low: <2 mentions/minute

**Duration:**
- Studio intro: 7-11 seconds
- Interviews: 45-90 seconds
- Studio analysis: 2-5 minutes
- Highlights: 5-10 minutes

### Example Classifications

**Clear Highlights:**
- 7-minute scene, scoreboard detected → **HIGHLIGHTS** (scoreboard definitive)

**Studio Analysis:**
- 3-minute scene, no scoreboard, high mentions (12 total = 4/min) → **STUDIO_ANALYSIS**

**Studio Intro:**
- 9-second scene, no scoreboard, low mentions (2 total) → **STUDIO_INTRO**

**Interview:**
- 65-second scene, no scoreboard, medium mentions (4 total = ~4/min) → **INTERVIEWS**

### Edge Cases

**Scoreboard Detected but Duration <60s:**
Flag as potential error - highlights never this short. Likely false positive scoreboard (crowd banner, replay overlay).

**High Mentions + Long Duration + No Scoreboard:**
9+ minutes, 7 mentions/min, no scoreboard → Likely highlights with scoreboard OCR failure. Duration + mentions = definitive.

**Ambiguous Signals:**
100-second scene, low mentions (1.8/min), no scoreboard → No clear match. Default to **STUDIO_ANALYSIS** (fallback).

---

## Related Documentation

- [Domain Glossary](README.md#glossary) - Terminology definitions
- [Visual Patterns](visual_patterns.md) - MOTD episode structure
- [Task 011c](../tasks/011-analysis-pipeline/011c-implement-segment-classifier.md) - Segment classifier implementation
- [Task 011d](../tasks/011-analysis-pipeline/011d-implement-match-boundary-detector.md) - Match boundary detection

---

**Last Updated:** 2025-11-18 (condensed during domain documentation initiative)
