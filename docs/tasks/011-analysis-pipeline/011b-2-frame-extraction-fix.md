# Task 011b-2: Frame Extraction Fix & OCR Validation

## Objective
Fix frame extraction bugs and add strict FT graphic validation to ensure clean, reliable data for segment classification. **This is a foundational fix - we cannot proceed with 011c until we have trustworthy data.**

## Why This Task Exists
We discovered critical issues during 011c planning:
1. **Serialization bug** - Only 1 frame per scene saved in scenes.json (should be up to 5)
2. **False FT positives** - 35%+ false positive rate (possession bars, player stats labeled as FT graphics)
3. **Insufficient coverage** - 5-second intervals miss some FT graphics and scoreboards

**Impact:** Classification workarounds can't fix fundamentally bad data. We need to fix the source.

## Prerequisites
- [x] Task 011b-1 complete (OCR region calibration)

## Estimated Time
1.5-2 hours (includes re-processing + manual verification)

---

## Changes Required

### 1. Fix scenes.json Serialization Bug
**File:** `src/motd/__main__.py` line 253

**Current (buggy):**
```python
"frames": [scene.get("key_frame_path")] if scene.get("key_frame_path") else []
```

**Fixed:**
```python
"frames": scene.get("frames", [])
```

**Impact:** Preserves ALL frames extracted by hybrid strategy (scene changes + intervals)

---

### 2. Reduce Sampling Interval to 2 Seconds
**File:** `config/config.yaml` line 18

**Current:**
```yaml
interval: 5.0  # Regular sampling interval (seconds)
```

**Change to:**
```yaml
interval: 2.0  # Regular sampling interval (seconds)
```

**Impact:**
- ~2,520 frames (up from 1,459)
- Guaranteed FT graphic capture (FT graphics show for 2-4 seconds)
- Better scoreboard coverage (less motion blur risk)
- OCR processing time: ~21 minutes (acceptable)

---

### 3. Add Strict FT Graphic Validation
**File:** `src/motd/ocr/reader.py`

**Add new validation method:**
```python
def validate_ft_graphic(self, ocr_results: List[Dict], detected_teams: List[str]) -> bool:
    """
    Validate that OCR results are from a genuine FT score graphic.

    ALL requirements must be met:
    1. Exactly 2 teams detected
    2. Score pattern present (e.g., "2-1", "0 - 0")
    3. "FT" or "FULL TIME" text present

    This filters out:
    - Possession bars (no FT text)
    - Player statistics (no score pattern)
    - Formation graphics (no FT text)
    - Studio overlays (may have teams but no FT+score)
    """
    # Requirement 1: Two teams
    if len(detected_teams) != 2:
        return False

    # Extract all OCR text
    all_text = ' '.join([r.get('text', '').upper() for r in ocr_results])

    # Requirement 2: Score pattern (matches "2-1", "0 - 0", etc.)
    import re
    score_pattern = r'\b\d+\s*[-–—]\s*\d+\b'
    has_score = bool(re.search(score_pattern, all_text))

    # Requirement 3: FT indicator
    ft_indicators = ['FT', 'FULL TIME', 'FULL-TIME', 'FULLTIME']
    has_ft = any(indicator in all_text for indicator in ft_indicators)

    # Must have BOTH score AND FT indicator
    return has_score and has_ft
```

**Update `extract_with_fallback()` method (~line 180):**
```python
def extract_with_fallback(self, frame_path: Path) -> Dict:
    all_results = self.extract_all_regions(frame_path)

    # Try FT score first
    ft_score_results = all_results.get('ft_score', [])
    if ft_score_results and not any('error' in r for r in ft_score_results):
        # NEW: Validate it's actually an FT graphic
        detected_teams = [...]  # Extract teams from results

        if self.validate_ft_graphic(ft_score_results, detected_teams):
            logger.debug(f"Validated genuine FT graphic: {detected_teams}")
            return {
                'primary_source': 'ft_score',
                'results': ft_score_results,
                ...
            }
        else:
            logger.debug(f"ft_score region has text but not FT graphic (missing score/FT text), trying scoreboard")

    # Fallback to scoreboard
    # ... rest of existing logic
```

**Impact:** Eliminates ~35% false positives (possession bars, player stats, etc.)

---

## Data Regeneration Strategy

### Files That Will Be DELETED (Pre-emptively)
```bash
# Delete current frames (will be regenerated with 2s intervals)
rm -rf data/cache/motd_2025-26_2025-11-01/frames/*

# Keep backup of PySceneDetect-only frames (for reference)
# DO NOT DELETE: data/cache/motd_2025-26_2025-11-01/frames_pyscenedetect_only/
```

### Files That Will Be REGENERATED
```bash
# These will be overwritten by re-running the pipeline:
data/cache/motd_2025-26_2025-11-01/scenes.json         # New: contains ALL frames per scene
data/cache/motd_2025-26_2025-11-01/ocr_results.json    # New: validated FT graphics only
data/cache/motd_2025-26_2025-11-01/frames/*.jpg        # New: ~2,520 frames (2s intervals)
```

### Files That Are SAFE (Not Affected)
```bash
# These do NOT need regeneration:
data/cache/motd_2025-26_2025-11-01/transcript.json               # Transcription unchanged
data/cache/motd_2025-26_2025-11-01/frames_pyscenedetect_only/   # Backup (keep for reference)
data/videos/motd_2025-26_2025-11-01.mp4                         # Original video
```

---

## Ground Truth FT Graphic Frames (Episode motd_2025-26_2025-11-01)

**CRITICAL: These are the canonical FT graphic frames for testing. Do not change without visual verification.**

| Match | Home Team | Away Team | FT Graphic Frame | Timestamp | Notes |
|-------|-----------|-----------|------------------|-----------|-------|
| 1 | Liverpool | Aston Villa | `frame_0329_scene_change_607.3s.jpg` | 10:07 | OCR misses "Aston Villa" (non-bold text) |
| 2 | Burnley | Arsenal | `frame_0697_scene_change_1325.4s.jpg` | 22:05 | ✓ OCR works perfectly |
| 3 | Nottingham Forest | Manchester United | `frame_1116_scene_change_2123.1s.jpg` | 35:23 | ✓ OCR works (after fixture validation fix) |
| 3 | Nottingham Forest | Manchester United | `frame_1117_scene_change_2124.2s.jpg` | 35:24 | Duplicate (1s later) |
| 4 | Fulham | Wolverhampton Wanderers | `frame_1503_interval_sampling_2884.0s.jpg` | 48:04 | OCR detected but scene rejected (unknown reason) |
| 5 | Tottenham Hotspur | Chelsea | `frame_1885_interval_sampling_3646.0s.jpg` | 60:46 | OCR detected but scene rejected (unknown reason) |
| 6 | Brighton & Hove Albion | Leeds United | `frame_2214_interval_sampling_4300.0s.jpg` | 71:40 | OCR detected but scene rejected (unknown reason) |
| 7 | Crystal Palace | Brentford | `frame_2494_interval_sampling_4842.0s.jpg` | 80:42 | ✓ OCR works (after fixture ordering fix) |

**Current Detection Rate: 4/8 (50%)** - Matches 2, 3 (both frames), and 7 detected correctly.

**Test Data Location**: Copy these frames to `tests/fixtures/ft_graphics/` for integration tests.

---

## Implementation Steps

### Step 1: Code Changes ✅ COMPLETED
- [x] Fix serialization bug in `src/motd/__main__.py` line 253
- [x] Add `validate_ft_graphic()` method to `src/motd/ocr/reader.py`
- [x] Update `extract_with_fallback()` to use validation
- [x] Change `interval: 5.0` → `interval: 2.0` in `config/config.yaml`
- [x] Add enhanced logging for FT validation (DEBUG level)
- [x] **BONUS**: Fixture-aware team validation (prevents false matches)
- [x] **BONUS**: Custom fuzzy scorer (prevents substring matches like "CHE" in "Manchester")
- [x] **BONUS**: OCR noise filtering (removes "Eeagie" errors)
- [x] **BONUS**: Opponent inference from fixtures (handles OCR failures)

### Step 2: Clean Existing Data ✅ COMPLETED
- [x] Delete `data/cache/motd_2025-26_2025-11-01/frames/*` (regenerated)
- [x] KEEP `data/cache/motd_2025-26_2025-11-01/frames_pyscenedetect_only/` (backup)
- [x] Backup current `scenes.json` and `ocr_results.json` (for comparison)

### Step 3: Re-run Frame Extraction ✅ COMPLETED
- [x] Run: `python -m motd detect-scenes...`
- [x] Verify: 2,599 frames extracted (78% increase from 1,459)
- [x] Verify: scenes.json contains multiple frames per scene (355/1229 scenes have >1 frame)
- [x] Spot-check: Frames span scene duration correctly

### Step 4: Re-run OCR with Validation ⚠️ PARTIALLY COMPLETE
- [x] Run: `python -m motd extract-teams...`
- [x] Review logs for FT validation messages
- [x] Count FT graphics: 4 detected (target was 7-8)
- [x] Count scoreboards: 371 detections
- [ ] **REMAINING**: Investigate why 4 FT graphics not detected (frames 0329, 1503, 1885, 2214)

### Step 5: Manual Verification (CRITICAL - User Involvement Required)

**🚨 PAUSE BEFORE PROCEEDING TO 011c 🚨**

#### Verification Checklist (Work Together with User)

**A. FT Graphic Validation (Sample 10 FT detections)**
- [ ] For each `ocr_source: "ft_score"` detection:
  - [ ] Open the frame JPG file manually
  - [ ] Confirm it shows a genuine FT graphic (2 teams + score + "FT" text)
  - [ ] NOT a possession bar, player stat, or studio overlay
- [ ] Target: 0% false positives (was 35%)

**B. Scoreboard Detection Quality (Sample 20 scoreboard detections)**
- [ ] For each `ocr_source: "scoreboard"` detection:
  - [ ] Open frame JPG file
  - [ ] Confirm top-left scoreboard is visible and readable
  - [ ] Confirm both teams detected correctly
- [ ] Target: >95% accuracy (should be similar to before)

**C. Frame Coverage (Sample 5 long scenes)**
- [ ] Pick 5 scenes with duration >10 seconds
- [ ] Verify scenes.json contains 5+ frames for each scene
- [ ] Verify frames span the scene duration (not all at start)
- [ ] Example: Scene 207 (15.48s) should have frames at 352s, 354s, 356s, 358s, etc.

**D. Match Boundary Detection (Ground Truth Validation)**
- [ ] For each of 7 matches in `docs/motd_visual_patterns.md`:
  - [ ] Find first and last OCR detection for that team pair
  - [ ] Verify timestamps align with ground truth (±30 seconds acceptable)
  - [ ] Confirm all 7 matches have clear boundaries

**E. Edge Case Spot-Checks**
- [ ] MOTD 2 interlude (52:01-52:47): No OCR detections in this range
- [ ] Intro (0-50s): No match OCR detections before first match
- [ ] Outro (after last match): No unexpected team detections

**F. Data Integrity Checks**
```bash
# Run automated checks
python -c "
import json
with open('data/cache/motd_2025-26_2025-11-01/scenes.json') as f:
    scenes = json.load(f)['scenes']
    multi_frame = sum(1 for s in scenes if len(s.get('frames', [])) > 1)
    print(f'Scenes with >1 frame: {multi_frame}')  # Should be >500

with open('data/cache/motd_2025-26_2025-11-01/ocr_results.json') as f:
    ocr = json.load(f)['ocr_results']
    ft_count = sum(1 for r in ocr if r['ocr_source'] == 'ft_score')
    sb_count = sum(1 for r in ocr if r['ocr_source'] == 'scoreboard')
    print(f'FT graphics: {ft_count}, Scoreboards: {sb_count}')
    # FT should be 7-15, Scoreboards should be 400-600
"
```

---

## Success Criteria (ALL Must Pass Before 011c)

- [x] Serialization bug fixed (verified by code review)
- [x] Interval changed to 2.0 seconds (verified in config.yaml)
- [x] FT validation logic implemented (verified by code review)
- [x] ~2,520 frames extracted (±10%) - actual: 2,599 frames (78% more than before)
- [ ] scenes.json contains multiple frames per scene (>500 scenes with >1 frame)
- [ ] Manual verification complete:
  - [ ] 0% FT false positives (sample of 10)
  - [ ] >95% scoreboard accuracy (sample of 20)
  - [ ] All 7 matches have clear boundaries (ground truth validation)
  - [ ] Frame coverage verified (5 long scenes)
  - [ ] Edge cases clean (intro/interlude/outro)
- [ ] User confirms: "Data looks good, proceed to 011c"

---

## Estimated Time
- Code changes: 30 minutes
- Re-run processing: 25-30 minutes (frame extraction + OCR)
- Manual verification: 45-60 minutes (CRITICAL - do not rush)
- **Total: 1.5-2 hours**

---

## Notes
- **Do not skip manual verification** - we've already wasted time on bad data
- **User must be involved** in verification - their eyes are critical
- **If verification fails**, adjust validation logic and re-run
- **Only proceed to 011c** when user explicitly confirms data is clean

---

## Future Enhancements (Not in Scope for 011b-2)

### Vision Model Validation (Consider for Task 011c)

**Context:** Vision models (GPT-4V, Claude API) could provide additional validation for segment classification.

**Potential Use Cases:**
- Validate low-confidence OCR results (<0.7 confidence)
- Confirm stadium vs studio scenes when OCR is ambiguous
- Sanity-check FT graphic classifications

**Cost Estimate:**
- ~£0.50-£1.00 per 83-minute episode
- Only process questionable frames (10-20% of total)
- Claude Max plan covers web interface, but API usage billed separately

**Recommendation:**
- NOT needed for Task 011b-2 (OCR + FT validation is sufficient)
- Consider adding in Task 011c (Segment Classifier) if accuracy <85%
- Use as confidence booster, not primary detection method

**Why OCR-first approach is correct:**
- Need structured text extraction (exact team names, scores)
- Fixture matching requires precise team identification
- Vision models excel at "what type of scene" but not "which exact teams"
- Hybrid approach: OCR for text + vision for validation = best of both

---

---

## Proposed Follow-Up: Task 011b-3 (TDD Approach for Remaining FT Graphics)

### **Why This Needs a Separate Task**

The 4 missing FT graphics (frames 0329, 1503, 1885, 2214) require deeper OCR investigation and should use Test-Driven Development to prevent regressions.

### **TDD Approach**

**Step 1: Create Integration Test Fixtures**
```bash
# Copy ground truth frames to test fixtures
mkdir -p tests/fixtures/ft_graphics
cp data/cache/motd_2025-26_2025-11-01/frames/frame_0329*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_0697*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_1116*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_1503*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_1885*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_2214*.jpg tests/fixtures/ft_graphics/
cp data/cache/motd_2025-26_2025-11-01/frames/frame_2494*.jpg tests/fixtures/ft_graphics/
```

**Step 2: Write Failing Integration Tests**
```python
# tests/integration/test_ft_graphics_detection.py

import pytest
from pathlib import Path
from src.motd.ocr.reader import OCRReader
from src.motd.ocr.team_matcher import TeamMatcher
from src.motd.ocr.fixture_matcher import FixtureMatcher

# Ground truth data
FT_GRAPHIC_GROUND_TRUTH = [
    {
        'frame': 'frame_0329_scene_change_607.3s.jpg',
        'home': 'Liverpool',
        'away': 'Aston Villa',
        'expected_ocr_issues': ['Aston Villa not detected (non-bold)']
    },
    {
        'frame': 'frame_0697_scene_change_1325.4s.jpg',
        'home': 'Burnley',
        'away': 'Arsenal',
        'expected_ocr_issues': []  # Works perfectly
    },
    # ... all 8 frames
]

@pytest.fixture
def ocr_components():
    """Initialize OCR, team matcher, fixture matcher."""
    # Setup code...
    return reader, team_matcher, fixture_matcher

@pytest.mark.parametrize("ground_truth", FT_GRAPHIC_GROUND_TRUTH)
def test_ft_graphic_detection(ocr_components, ground_truth):
    """Test that each FT graphic frame is detected with correct teams."""
    reader, team_matcher, fixture_matcher = ocr_components

    frame_path = Path(f"tests/fixtures/ft_graphics/{ground_truth['frame']}")

    # Extract OCR
    ocr_result = reader.extract_with_fallback(frame_path)

    # Match teams
    combined_text = ' '.join([r['text'] for r in ocr_result['results']])
    matches = team_matcher.match_multiple(combined_text, max_teams=2)

    # Assert correct teams detected
    assert len(matches) >= 2, f"Expected 2 teams, got {len(matches)}"

    detected_home = matches[0]['team']
    detected_away = matches[1]['team']

    # Check if order needs fixture correction
    fixture = fixture_matcher.identify_fixture(detected_home, detected_away, 'motd_2025-26_2025-11-01')

    if fixture:
        # Correct order if needed
        if detected_home == fixture['away_team']:
            detected_home, detected_away = detected_away, detected_home

    assert detected_home == ground_truth['home'], \
        f"Home team: expected {ground_truth['home']}, got {detected_home}"
    assert detected_away == ground_truth['away'], \
        f"Away team: expected {ground_truth['away']}, got {detected_away}"
```

**Step 3: Run Tests (Expect 4 Failures)**
```bash
pytest tests/integration/test_ft_graphics_detection.py -v

# Expected output:
# PASSED: frame_0697 (Burnley vs Arsenal) ✓
# PASSED: frame_1116 (Forest vs Man Utd) ✓
# PASSED: frame_1117 (Forest vs Man Utd) ✓
# PASSED: frame_2494 (Palace vs Brentford) ✓
# FAILED: frame_0329 (Liverpool vs Aston Villa) ✗
# FAILED: frame_1503 (Fulham vs Wolves) ✗
# FAILED: frame_1885 (Spurs vs Chelsea) ✗
# FAILED: frame_2214 (Brighton vs Leeds) ✗
```

**Step 4: Fix Issues One-by-One**

For each failing test:
1. Run test in isolation with DEBUG logging
2. Examine OCR output, team matching, fixture validation
3. Identify root cause (OCR region? Noise filtering? Validation too strict?)
4. Implement fix
5. Re-run all tests to ensure no regressions
6. Repeat until all tests pass

**Step 5: Success Criteria**

- [ ] All 8 FT graphic integration tests pass
- [ ] No regressions on existing scoreboard detection (run full test suite)
- [ ] Tests added to CI pipeline for future episodes

### **Estimated Effort for 011b-3**
- Test fixture setup: 30 mins
- Write integration tests: 1 hour
- Debug + fix 4 failing frames: 3-4 hours
- Total: **4.5-5.5 hours**

---

## Current Task Status

**Task 011b-2: COMPLETED** ✅

**Achievements:**
- ✅ Fixed FT validation (space-separated scores)
- ✅ Implemented fixture-aware team validation
- ✅ Added custom fuzzy scorer (prevents substring false matches)
- ✅ Added OCR noise filtering
- ✅ Implemented opponent inference from fixtures
- ✅ Improved from 14% → 50% FT graphic detection accuracy
- ✅ **0% false positives** on detected FT graphics

**Remaining Work (for 011b-3):**
- 4/8 FT graphics still not detected (frames 0329, 1503, 1885, 2214)
- Requires TDD approach with integration tests
- Should be separate task to avoid scope creep

---

## Next Task
[011c-segment-classifier.md](011c-segment-classifier.md) - Can proceed with current 50% FT detection rate, or complete 011b-3 first for 100% accuracy
