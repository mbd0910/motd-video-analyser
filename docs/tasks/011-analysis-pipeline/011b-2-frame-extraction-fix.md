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

## Implementation Steps

### Step 1: Code Changes
- [ ] Fix serialization bug in `src/motd/__main__.py` line 253
- [ ] Add `validate_ft_graphic()` method to `src/motd/ocr/reader.py`
- [ ] Update `extract_with_fallback()` to use validation
- [ ] Change `interval: 5.0` → `interval: 2.0` in `config/config.yaml`
- [ ] Add enhanced logging for FT validation (DEBUG level)

### Step 2: Clean Existing Data
- [ ] Delete `data/cache/motd_2025-26_2025-11-01/frames/*` (will regenerate)
- [ ] KEEP `data/cache/motd_2025-26_2025-11-01/frames_pyscenedetect_only/` (backup)
- [ ] Backup current `scenes.json` and `ocr_results.json` (for comparison)

### Step 3: Re-run Frame Extraction
- [x] Run: `python -m motd detect-scenes data/videos/motd_2025-26_2025-11-01.mp4 --output data/cache/motd_2025-26_2025-11-01/scenes.json`
- [x] Verify: ~2,520 frames extracted in `frames/` directory (actual: 2,599 frames)
- [ ] Verify: scenes.json contains multiple frames per scene (not just 1)
- [ ] Spot-check: 5-10 random scenes have expected frames

### Step 4: Re-run OCR with Validation
- [ ] Run: `python -m motd extract-teams --scenes data/cache/motd_2025-26_2025-11-01/scenes.json --output data/cache/motd_2025-26_2025-11-01/ocr_results.json`
- [ ] Review logs for FT validation messages
- [ ] Count genuine FT graphics detected (expect ~7-15)
- [ ] Count scoreboard detections (expect ~400-600)

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

## Next Task
[011c-segment-classifier.md](011c-segment-classifier.md) - **ONLY after user confirms data quality**
