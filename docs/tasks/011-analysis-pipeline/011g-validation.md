# Task 011f: Execution, Validation & FT Graphic Investigation

## Objective
Run the complete analysis pipeline on the test video, validate results against ground truth, investigate any FT graphic detection issues, and document accuracy metrics.

## Prerequisites
- [x] Task 011e complete (pipeline orchestrator working)
- [x] All analysis components implemented and tested

## Estimated Time
2-3 hours

## Validation Phases

### Phase 1: Initial Execution (30 min)
### Phase 2: Running Order Validation (15 min) - **CRITICAL**
### Phase 3: Segment Classification Validation (45-60 min)
### Phase 4: FT Graphic Investigation (30-45 min)
### Phase 5: Final Validation Report (15-30 min)

---

## Phase 1: Initial Execution

### Steps
- [ ] Run full pipeline on test video
- [ ] Verify command completes without errors
- [ ] Check output file is created
- [ ] Quick sanity check of JSON structure

### Commands
```bash
# Run pipeline
python -m motd process data/videos/motd_2025-26_2025-11-01.mp4 \
  --output data/output/analysis.json

# Check output exists
ls -lh data/output/analysis.json

# Quick preview
python -m json.tool data/output/analysis.json | head -50
```

### Success Criteria
- [ ] Pipeline runs without errors
- [ ] analysis.json created
- [ ] JSON is valid and well-formed
- [ ] File size is reasonable (>10KB)

### If Errors Occur
- [ ] Check logs for specific error messages
- [ ] Verify all cached data exists (scenes, OCR, transcript)
- [ ] Check component unit tests all passed
- [ ] Debug specific failing component before proceeding

---

## Phase 2: Running Order Validation (**CRITICAL**)

**This is the most important validation - if running order is wrong, everything downstream is useless.**

### Ground Truth (from motd_visual_patterns.md)
```python
EXPECTED_RUNNING_ORDER = [
    {
        "order": 1,
        "teams": ["Liverpool", "Aston Villa"],
        "start_time": "00:00:50"
    },
    {
        "order": 2,
        "teams": ["Burnley", "Arsenal"],
        "start_time": "00:14:25"
    },
    {
        "order": 3,
        "teams": ["Forest", "Manchester United"],  # or "Nottingham Forest"
        "start_time": "00:26:27"
    },
    {
        "order": 4,
        "teams": ["Fulham", "Wolves"],  # or "Wolverhampton Wanderers"
        "start_time": "00:41:49"
    },
    {
        "order": 5,
        "teams": ["Spurs", "Chelsea"],  # or "Tottenham Hotspur"
        "start_time": "00:52:47"  # Note: 1 second difference in doc (52:48)
    },
    {
        "order": 6,
        "teams": ["Brighton", "Leeds"],  # or "Brighton & Hove Albion", "Leeds United"
        "start_time": "1:04:54"
    },
    {
        "order": 7,
        "teams": ["Palace", "Brentford"],  # or "Crystal Palace"
        "start_time": "1:14:40"
    }
]
```

### Validation Script

Create `scripts/validate_running_order.py`:
```python
import json
from pathlib import Path

def normalize_team_name(name: str) -> str:
    """Normalize team names for comparison."""
    normalization = {
        "Nottingham Forest": "Forest",
        "Wolverhampton Wanderers": "Wolves",
        "Tottenham Hotspur": "Spurs",
        "Brighton & Hove Albion": "Brighton",
        "Leeds United": "Leeds",
        "Crystal Palace": "Palace"
    }
    return normalization.get(name, name)

def validate_running_order(analysis_path: Path) -> bool:
    """Validate running order matches ground truth."""

    with open(analysis_path) as f:
        analysis = json.load(f)

    expected = EXPECTED_RUNNING_ORDER  # From above

    if len(analysis["matches"]) != 7:
        print(f"✗ Expected 7 matches, got {len(analysis['matches'])}")
        return False

    all_correct = True

    for i, match in enumerate(analysis["matches"]):
        expected_match = expected[i]

        # Check running order
        if match["running_order"] != expected_match["order"]:
            print(f"✗ Match {i+1}: Wrong running order")
            all_correct = False

        # Check teams (normalize names)
        actual_teams = [normalize_team_name(t) for t in match["teams"]]
        expected_teams = [normalize_team_name(t) for t in expected_match["teams"]]

        if set(actual_teams) != set(expected_teams):
            print(f"✗ Match {i+1}: Expected {expected_teams}, got {actual_teams}")
            all_correct = False
        else:
            print(f"✓ Match {i+1}: {' vs '.join(actual_teams)}")

    if all_correct:
        print("\n✓✓✓ Running order validation PASSED (7/7 correct)")
    else:
        print("\n✗✗✗ Running order validation FAILED")

    return all_correct
```

### Manual Validation Steps
- [ ] Run validation script
- [ ] **If any failures**: Stop and debug match boundary detector
- [ ] **User manual check**: Open video and verify first 3 matches visually
- [ ] **Target**: 100% accuracy (7/7 matches correct)

### Success Criteria
- [ ] **All 7 matches in correct order**
- [ ] **All team names correct** (allowing for name variants)
- [ ] Running order validation script passes
- [ ] User confirms first 3 matches manually

### If Running Order Wrong
**DO NOT PROCEED** - Fix match boundary detector first:
1. Review match boundary detection logs
2. Check OCR fixture matches
3. Check team mention detection in studio intros
4. Re-run 011c with fixes
5. Re-validate until 100% accurate

---

## Phase 3: Segment Classification Validation

### Sampling Strategy
- [ ] Select 20-30 scenes across all segment types
- [ ] Include scenes from different matches
- [ ] Include edge cases (boundaries, transitions)

### Sample Scenes to Validate

```python
VALIDATION_SAMPLES = [
    # Match 1: Liverpool vs Aston Villa
    {"scene_id": 125, "expected": "studio_intro", "timestamp": "00:00:50"},
    {"scene_id": 154, "expected": "highlights", "timestamp": "00:02:34"},  # Scoreboard
    {"scene_id": 220, "expected": "highlights", "timestamp": "00:03:40"},  # FT graphic
    {"scene_id": 228, "expected": "interviews", "timestamp": "00:10:11"},
    {"scene_id": 234, "expected": "studio_analysis", "timestamp": "00:11:04"},

    # Match 2: Burnley vs Arsenal
    {"scene_id": 243, "expected": "studio_intro", "timestamp": "00:14:25"},
    {"scene_id": 277, "expected": "highlights", "timestamp": "00:16:57"},  # Scoreboard
    {"scene_id": 312, "expected": "highlights", "timestamp": "00:19:42"},  # FT graphic
    {"scene_id": 316, "expected": "interviews", "timestamp": "00:22:09"},
    {"scene_id": 320, "expected": "studio_analysis", "timestamp": "00:22:57"},

    # Match 3: Forest vs Man United
    {"scene_id": 393, "expected": "highlights", "timestamp": "00:29:53"},  # Scoreboard
    {"scene_id": 419, "expected": "studio_analysis", "timestamp": "00:36:39"},

    # Match 4: Fulham vs Wolves
    {"scene_id": 486, "expected": "highlights", "timestamp": "00:44:46"},  # Scoreboard

    # Match 5: Spurs vs Chelsea
    {"scene_id": 612, "expected": "highlights", "timestamp": "00:57:52"},  # Scoreboard

    # Match 6: Brighton vs Leeds
    {"scene_id": 690, "expected": "studio_analysis", "timestamp": "1:12:30"},

    # Match 7: Palace vs Brentford
    {"scene_id": 709, "expected": "highlights", "timestamp": "1:16:49"},  # Scoreboard
    {"scene_id": 770, "expected": "studio_analysis", "timestamp": "1:21:50"},
]
```

### Validation Script

Create `scripts/validate_segments.py`:
```python
def validate_segment_classification(analysis_path: Path, classified_scenes_path: Path) -> float:
    """Validate segment classifications against samples."""

    with open(classified_scenes_path) as f:
        classified_scenes = json.load(f)

    scenes_by_id = {s["id"]: s for s in classified_scenes}

    correct = 0
    total = len(VALIDATION_SAMPLES)

    for sample in VALIDATION_SAMPLES:
        scene = scenes_by_id.get(sample["scene_id"])
        if not scene:
            print(f"✗ Scene {sample['scene_id']} not found")
            continue

        actual = scene["segment_type"]
        expected = sample["expected"]

        if actual == expected:
            print(f"✓ Scene {sample['scene_id']}: {actual} (confidence: {scene['confidence']:.2f})")
            correct += 1
        else:
            print(f"✗ Scene {sample['scene_id']}: Expected {expected}, got {actual} (confidence: {scene['confidence']:.2f})")

    accuracy = (correct / total) * 100
    print(f"\nSegment Classification Accuracy: {accuracy:.1f}% ({correct}/{total})")

    return accuracy
```

### Manual Spot-Checking
- [ ] For 5-10 scenes, open video at timestamp and verify classification
- [ ] Check scene boundaries make sense
- [ ] Verify highlights have scoreboard/FT graphics
- [ ] Verify interviews follow highlights
- [ ] Verify studio analysis follows interviews

### Success Criteria
- [ ] Automated validation: >85% accuracy
- [ ] Manual spot-checks: >90% agreement
- [ ] No systematic errors (e.g., all intros misclassified)
- [ ] Confidence scores correlate with accuracy

### If Accuracy < 85%
1. Analyze failure patterns
   - Which segment types are confused?
   - Are rules too strict/loose?
2. Review classification logs for failed scenes
3. Adjust classification rules in 011b
4. Re-run and re-validate
5. Iterate until target accuracy achieved

---

## Phase 4: FT Graphic Investigation

**User mentioned that scene detection sometimes misses FT graphics. This is important because FT graphics are a key boundary marker for highlights→interviews transition.**

### Investigation Steps

- [ ] **Step 1: Check OCR Results**
  - How many scenes have `ft_graphic: true` in ocr_results.json?
  - Expected: 7 (one per match)
  - If missing: Which matches?

```bash
# Count FT graphic detections
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '[.[] | select(.ft_graphic == true)] | length'

# List all FT graphic detections
cat data/cache/motd_2025-26_2025-11-01/ocr_results.json | \
  jq '[.[] | select(.ft_graphic == true) | {scene_id: .scene_id, teams: .teams}]'
```

- [ ] **Step 2: Check Scene Detection**
  - For FT graphic timestamps from motd_visual_patterns.md, check if scene exists
  - Expected FT graphic timestamps:
    - Match 1: ~00:10:11 (scene 220-221)
    - Match 2: ~00:22:09 (scene 312)
    - Match 3: ~00:35:25 (scene 401?)
    - Match 4: ~00:48:06
    - Match 5: ~1:00:49
    - Match 6: ~1:11:44
    - Match 7: ~1:20:45

```python
# For each expected FT timestamp, find nearest scene
def find_scene_at_timestamp(scenes: List[Dict], timestamp_seconds: float) -> Optional[Dict]:
    """Find scene at or near timestamp."""
    for scene in scenes:
        if scene["start_time"] <= timestamp_seconds <= scene["end_time"]:
            return scene
    return None
```

- [ ] **Step 3: Check Key Frames**
  - For FT graphic timestamps, check if key frame was extracted
  - If scene exists but no key frame → Scene detection issue
  - If key frame exists but OCR missed it → OCR issue

- [ ] **Step 4: Document Findings**
  - Create table: Match | Expected Time | Scene Exists? | Key Frame? | OCR Detected?
  - For each miss, document why
  - Possible causes:
    - Scene too short (filtered by duration threshold)
    - FT graphic transition too quick (<2 seconds)
    - Key frame extracted before/after FT graphic appears
    - OCR region doesn't cover FT graphic location

### Investigation Report Template

```markdown
# FT Graphic Detection Investigation

## Summary
- Total matches: 7
- FT graphics detected: X/7
- Missing: Y matches

## Detailed Findings

| Match | Teams | Expected Time | Scene ID | Key Frame | OCR Detected | Status |
|-------|-------|---------------|----------|-----------|--------------|--------|
| 1 | Liverpool vs Villa | 00:10:11 | 220 | ✓ | ✓ | OK |
| 2 | Burnley vs Arsenal | 00:22:09 | 312 | ✓ | ✓ | OK |
| 3 | Forest vs Man Utd | 00:35:25 | ? | ? | ✗ | MISSING |
| ... | ... | ... | ... | ... | ... | ... |

## Root Causes
[Document why FT graphics were missed]

## Recommendations
1. [e.g., Adjust scene detection threshold]
2. [e.g., Extract additional key frames near transitions]
3. [e.g., Expand OCR region to cover lower screen]
4. [Defer to Task 013 if complex fixes needed]
```

### Success Criteria
- [ ] All 7 FT graphic timestamps checked
- [ ] Root cause identified for any misses
- [ ] Recommendations documented
- [ ] If fix is simple: Implement in Task 013
- [ ] If fix is complex: Defer to Task 013 with detailed notes

---

## Phase 5: Final Validation Report

### Create Final Report

`docs/task_011_validation_report.md`:

```markdown
# Task 011: Analysis Pipeline Validation Report

**Date:** [YYYY-MM-DD]
**Video:** motd_2025-26_2025-11-01.mp4

## Executive Summary
- Pipeline Status: [PASS / FAIL]
- Running Order Accuracy: X/7 (target: 7/7)
- Segment Classification Accuracy: X% (target: >85%)
- FT Graphic Detection: X/7

## Running Order Validation
[Results from Phase 2]

| Match # | Teams | Expected | Detected | Status |
|---------|-------|----------|----------|--------|
| 1 | Liverpool vs Villa | ✓ | ✓ | PASS |
| ... | ... | ... | ... | ... |

**Result:** [PASS / FAIL]

## Segment Classification Validation
[Results from Phase 3]

### Accuracy by Segment Type
- studio_intro: X% (Y/Z)
- highlights: X% (Y/Z)
- interviews: X% (Y/Z)
- studio_analysis: X% (Y/Z)
- **Overall: X%** (Y/Z)

### Failure Analysis
[List misclassified scenes with reasoning]

**Result:** [PASS / FAIL]

## FT Graphic Investigation
[Results from Phase 4]

[Include findings table]

**Recommendations for Task 013:**
1. ...
2. ...

## Airtime Calculations
[Spot-check 2-3 matches against manual timings]

| Match | Expected Total | Calculated Total | Difference | Status |
|-------|----------------|------------------|------------|--------|
| 1 | ~791s | 785s | -6s | OK |
| ... | ... | ... | ... | ... |

## Edge Cases Discovered
[Document any unexpected patterns or edge cases]

## Overall Assessment
- [ ] Task 011 Success Criteria Met
- [ ] Running order: 100% accurate
- [ ] Segment classification: >85% accurate
- [ ] Pipeline runs end-to-end successfully
- [ ] Output matches PRD schema
- [ ] Caching works correctly
- [ ] Ready for Task 012 (Validation Tools)

## Recommendations for Task 012/013
1. [Build validation UI to improve ground truth]
2. [Tune classification rules for specific failure patterns]
3. [Investigate FT graphic detection improvements]
```

### Success Criteria
- [ ] Validation report completed
- [ ] All 5 phases documented
- [ ] Accuracy metrics calculated
- [ ] Failure patterns analyzed
- [ ] Recommendations for next tasks
- [ ] User review and sign-off

---

## Deliverables

### 1. Validation Scripts
- `scripts/validate_running_order.py`
- `scripts/validate_segments.py`
- `scripts/investigate_ft_graphics.py`

### 2. Validation Report
- `docs/task_011_validation_report.md`

### 3. Final Analysis Output
- `data/output/analysis.json` (validated and ready for use)

---

## Overall Success Criteria for Task 011

- [ ] **Phase 1**: Pipeline runs without errors
- [ ] **Phase 2**: Running order 100% accurate (7/7 matches) ✓✓✓ CRITICAL
- [ ] **Phase 3**: Segment classification >85% accurate
- [ ] **Phase 4**: FT graphic investigation complete with recommendations
- [ ] **Phase 5**: Validation report written
- [ ] User manual review and approval
- [ ] analysis.json matches PRD schema
- [ ] Caching works (re-run is instant)
- [ ] All subtasks 011a-011f complete
- [ ] Ready for Task 012 (Validation Tools)

---

## Testing Commands

```bash
# Phase 1: Run pipeline
python -m motd process data/videos/motd_2025-26_2025-11-01.mp4

# Phase 2: Validate running order
python scripts/validate_running_order.py data/output/analysis.json

# Phase 3: Validate segments
python scripts/validate_segments.py data/output/analysis.json \
  data/cache/motd_2025-26_2025-11-01/classified_scenes.json

# Phase 4: Investigate FT graphics
python scripts/investigate_ft_graphics.py \
  data/cache/motd_2025-26_2025-11-01/ocr_results.json \
  data/cache/motd_2025-26_2025-11-01/scenes.json

# Test caching (should be <1 second)
time python -m motd process data/videos/motd_2025-26_2025-11-01.mp4
```

---

## Notes
- This is the **most important validation** - be thorough
- Running order accuracy is non-negotiable (100%)
- Segment classification can be refined in Task 013 if needed
- FT graphic investigation informs future improvements
- User involvement is key for manual validation
- Document everything - this informs Task 012 ground truth

## Next Task
[012-validation-tools-epic.md](../012-validation-tools/README.md)
