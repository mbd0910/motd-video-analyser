# Issue #7: Fix Spurious Scoreboard OCR Detections

**GitHub Issue:** [#7](https://github.com/mbd0910/motd-video-analyser/issues/7)
**Branch:** `feature/issue-7-scoreboard-validation`
**Status:** Complete

## Problem Statement

The OCR detection pipeline produces false positive results because scoreboard detections have **no validation** (unlike FT graphics which require "FT" text).

**Example:** Brighton detected at 39s during intro montage - not actual match footage.

## Investigation Findings

### Real Scoreboard Format (from frame at 127s - Liverpool vs Forest)
```
BBC LIV 0|0 FOR
```
- BBC branding on left
- 3-character team codes (LIV, FOR)
- Score with pipe separator (0|0)

### Intro Frame at 39s (Spurious Detection)
- MOTD intro montage showing club badges
- No actual scoreboard graphic present
- Top-left region contains text fragments: "The", "CL", "UB", "BALL"
- Fuzzy matching picks up partial matches against team codes

### Code Flow Analysis
1. `SceneProcessor.process()` runs OCR with fallback strategy
2. `OCRReader.extract_with_fallback()` tries FT region first, falls back to scoreboard
3. If scoreboard region returns text → `TeamMatcher.match_multiple()` fuzzy matches
4. **FT graphics validated** via `validate_ft_graphic()` (requires FT indicator + score)
5. **Scoreboards NOT validated** - any fuzzy match is accepted!

---

## Implementation Plan (TDD Approach)

### Phase 0: Setup
- [x] Create feature branch `feature/issue-7-scoreboard-validation`
- [x] Update task file with refined plan

### Phase 1: RED - Write Failing Tests

**File:** `tests/unit/ocr/test_scoreboard_validation.py`

- [x] Create test file with 18 test cases (expanded from original 13)
- [x] Tests initially FAILED (method didn't exist)

### Phase 2: GREEN - Implement Validation

**File:** `src/motd/ocr/reader.py`

- [x] Load team codes from `data/teams/premier_league_2025_26.json` in `__init__`
- [x] Add `validate_scoreboard()` method
- [x] Requirements for valid scoreboard:
  1. **Exactly 2 distinct 3-character team codes** (dynamic from JSON)
  2. **Score pattern (lenient):** `\b\d+\s*[-–—|]?\s*\d+\b`

### Phase 3: Integration

**File:** `src/motd/ocr/scene_processor.py`

- [x] Call `validate_scoreboard()` for scoreboard sources in `_process_single_frame()`
- [x] Renumbered pipeline steps 1-7 (was 1-6 with step 4b)

### Phase 4: Verification

- [x] Re-run OCR on Nov 22 episode
- [x] Verify Brighton 39s detection eliminated (**CONFIRMED: 0 detections in first 100s**)
- [x] Verify legitimate scoreboards still detected (first valid: 127s Liverpool vs Forest)

**Results:**
| Metric | Before | After |
|--------|--------|-------|
| Scenes with teams | 305 | 193 |
| Detections < 100s | 1 (false positive) | 0 |
| FT graphics | - | 7 (correct) |
| Expected teams | 14/14 | 14/14 |
| Unexpected detections | - | 0 |

### Phase 5: Final

- [x] Code review
- [x] Squash merge to main

---

## Key Design Decisions

### Why exactly 2 team codes (not 1)?
Scoreboard format always shows both teams (`LIV 0|0 FOR`). Unlike FT graphics (where one team may be non-bold with low OCR confidence), scoreboard codes are uniform style and should be reliably detected.

### Why lenient score pattern (not pipe-only)?
OCR frequently misreads `|` as `I`, `l`, `1`. Using the same lenient pattern as FT validation (`\d+\s*[-–—|]?\s*\d+`) is more robust. The team codes alone filter intro montage false positives.

### Why load team codes dynamically?
Ensures consistency with project's source of truth (`data/teams/premier_league_2025_26.json`). Includes primary codes (ARS, LIV) and alternates (BRI, FOR, AST).

---

## Test Cases

### Should PASS (Valid Scoreboards)
- `"BBC LIV 0|0 FOR"` → Pipe separator
- `"LIV 0-0 FOR"` → Hyphen separator (lenient)
- `"LIV 0 0 FOR"` → Space only (lenient)
- `"BBC BRI 2|1 BRE"` → Non-zero scores
- `"LIV 0|0 NFO"` → Primary code for Forest
- `"LIV 0|0 FOR"` → Alternate code for Forest

### Should FAIL (Reject)
- `"The CL UB BALL"` → No score pattern, no exact codes
- `"Brighton Club Football"` → Full name, not 3-char code
- `"0-0"` → Score but no team codes
- `"BBC LIV FOR"` → Team codes but no score
- `"LIV 0|0"` → Only 1 team code (need exactly 2)
- `"BBC SPORT"` → No teams, no score
- `[]` → Empty results

---

## Files to Modify

| File | Change |
|------|--------|
| `tests/unit/ocr/test_scoreboard_validation.py` | **NEW** - TDD tests |
| `src/motd/ocr/reader.py` | Add `validate_scoreboard()` + load team codes |
| `src/motd/ocr/scene_processor.py` | Call validation for scoreboard sources |

---

## Notes & Decisions

- **2025-12-12:** Investigation complete. Root cause: scoreboard detections bypass validation.
- **2025-12-16:** Refined plan: TDD approach, exactly 2 team codes, lenient score pattern, dynamic team codes from JSON.
