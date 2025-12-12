# Issue #7: Fix Spurious Scoreboard OCR Detections

**GitHub Issue:** [#7](https://github.com/mbd0910/motd-video-analyser/issues/7)
**Branch:** `feature/issue-7-scoreboard-validation`
**Status:** Planning Complete

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

## Implementation Plan

### Phase 1: Add Scoreboard Validation

**File:** `src/motd/ocr/reader.py`

- [ ] Add `validate_scoreboard()` method mirroring FT validation pattern
- [ ] Requirements for valid scoreboard:
  1. Score pattern with pipe separator: `\b\d+\s*\|\s*\d+\b`
  2. At least one exact 3-character team code (ARS, LIV, FOR, etc.)

### Phase 2: Integration

**File:** `src/motd/ocr/scene_processor.py`

- [ ] Call `validate_scoreboard()` for scoreboard sources (currently only FT validated)

### Phase 3: Testing

**File:** `tests/unit/ocr/test_scoreboard_validation.py`

- [ ] Test valid scoreboards pass ("BBC LIV 0|0 FOR")
- [ ] Test invalid detections rejected ("The CL UB BALL")

### Phase 4: Verification

- [ ] Re-run OCR on Nov 22 episode with `--force`
- [ ] Verify Brighton 39s detection eliminated
- [ ] Verify legitimate scoreboards still detected

---

## Implementation Details

### Scoreboard Validation Method

```python
def validate_scoreboard(self, ocr_results: List[Dict], detected_teams: List[str]) -> bool:
    """
    Validate that OCR results are from a genuine scoreboard graphic.

    BBC scoreboards follow format: "BBC [CODE] [SCORE]|[SCORE] [CODE]"
    Example: "BBC LIV 0|0 FOR"

    Requirements:
    1. Score pattern with pipe separator (BBC format)
    2. At least one exact 3-character team code
    """
    all_text = ' '.join([r.get('text', '').upper() for r in ocr_results])

    # Check for BBC scoreboard score pattern (uses pipe separator)
    score_pattern = r'\b\d+\s*\|\s*\d+\b'
    has_score = bool(re.search(score_pattern, all_text))

    # Check for exact 3-character team codes
    valid_codes = {'ARS', 'AVL', 'BOU', 'BRE', 'BRI', 'BUR', 'CHE', 'CRY',
                   'EVE', 'FUL', 'LEE', 'LIV', 'MCI', 'MUN', 'NEW', 'NFO',
                   'SUN', 'TOT', 'WHU', 'WOL', 'FOR'}

    words = all_text.split()
    found_codes = [w for w in words if w in valid_codes]
    has_code = len(found_codes) >= 1

    return has_score and has_code
```

---

## Test Cases

### Should PASS (Valid Scoreboards)
- `"BBC LIV 0|0 FOR"` → Liverpool vs Forest
- `"BBC BRI 2|1 BRE"` → Brighton vs Brentford
- `"LIV 0 | 0 FOR"` → Score with spaces

### Should FAIL (Reject)
- `"The CL UB BALL"` → No score pattern, no exact codes
- `"Brighton Club Football"` → No score pattern
- `"0 0"` → No pipe separator (wrong format)
- `"BBC SPORT"` → No teams, no score

---

## Files to Modify

| File | Change |
|------|--------|
| `src/motd/ocr/reader.py` | Add `validate_scoreboard()` method |
| `src/motd/ocr/scene_processor.py` | Call validation for scoreboard sources |
| `tests/unit/ocr/test_scoreboard_validation.py` | New test file |

---

## Estimated Effort

- `validate_scoreboard()` implementation: ~20 mins
- Scene processor integration: ~10 mins
- Unit tests: ~30 mins
- Re-run OCR + verification: ~15 mins
- **Total: ~1.5 hours**

---

## Notes & Decisions

- **2025-12-12:** Investigation complete. Root cause: scoreboard detections bypass validation that FT graphics require.
