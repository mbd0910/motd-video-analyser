# Task 013: Production-Ready CLI (Ground Truth Optional)

**Status:** TODO - Planning Phase

## Quick Context

**Prerequisites:** Task 012-01 complete (CLI command works for Episode 01 with hardcoded ground truth)
**Domain Concepts:** [Running Order](../../domain/README.md#running-order)

**Why This Matters:** Current CLI hardcodes ground truth timestamps for Episode 01 only. For production use on any MOTD episode, ground truth should be optional - cross-validation provides quality monitoring automatically.

---

## Problem

Current implementation (`src/motd/__main__.py` lines 753-762):
```python
GROUND_TRUTH_INTRO_TIMESTAMPS = {
    1: 61.0, 2: 865.0, 3: 1587.0, 4: 2509.0,
    5: 3168.0, 6: 3894.0, 7: 4480.0
}
```

**Issues:**
1. Only works for Episode 01 (`motd_2025-26_2025-11-01`)
2. Hardcoded in source control
3. Would require manual timestamp finding for every future episode (defeats automation purpose)
4. CLI fails or shows incorrect diffs for other episodes

---

## Objective

Make ground truth optional so CLI works for any MOTD episode without manual timestamp collection.

**Key Insight:** Cross-validation already provides quality monitoring! Venue vs clustering agreement is the real quality signal, not ground truth comparison.

---

## Design Options (To Decide During Implementation)

### Option A: Make Ground Truth Optional (Recommended)
```python
GROUND_TRUTH_INTRO_TIMESTAMPS: dict[str, dict] = {
    'motd_2025-26_2025-11-01': {...},  # Episode 01
    # Add more only if needed for algorithm tuning
}

# Display with ground truth if available, otherwise just show timestamps
ground_truth = GROUND_TRUTH_INTRO_TIMESTAMPS.get(episode_id)
if ground_truth:
    display_with_comparison(result, ground_truth)
else:
    display_without_comparison(result)
```

**Pros:** Simple, works for any episode, ground truth only for development
**Cons:** Ground truth still in source code (minor)

---

### Option B: External Ground Truth File
```python
# data/ground_truth/{episode_id}_intro_timestamps.json (optional, gitignored)
def load_ground_truth(episode_id: str) -> dict | None:
    path = f'data/ground_truth/{episode_id}_intro_timestamps.json'
    return json.load(open(path)) if Path(path).exists() else None
```

**Pros:** Not in source code, easy to add episodes without code changes
**Cons:** Extra file to manage

---

### Option C: Ground Truth via CLI Flag
```bash
# Production: No ground truth comparison
python -m motd analyze-running-order motd_2025-26_2025-11-01

# Development: With ground truth validation
python -m motd analyze-running-order motd_2025-26_2025-11-01 --validate
```

**Pros:** Clear intent separation, explicit opt-in for comparison
**Cons:** Requires flag plumbing

---

### Hybrid: Option A + B
- Dictionary in code for Episode 01 (development baseline)
- Load from `data/ground_truth/` if exists
- Fallback to no ground truth (works for any episode)

---

## Output Changes

### With Ground Truth (Current Behavior)
```
Match 1: Liverpool vs Aston Villa
  Match Start:       00:01:01.0 (+0.1s from ground truth)
  Validation:        ✓ validated (0.0s difference)
```

### Without Ground Truth (New Behavior)
```
Match 1: Liverpool vs Aston Villa
  Match Start:       00:01:01.0 (venue strategy)
  Validation:        ✓ validated (0.0s difference between venue and clustering)
```

**Key:** Cross-validation warnings always shown regardless of ground truth availability.

---

## Success Criteria

- [ ] CLI works for any episode ID (not just Episode 01)
- [ ] Ground truth comparison optional (only when available)
- [ ] Cross-validation warnings always displayed
- [ ] No manual work required for production use
- [ ] Existing Episode 01 validation still works

---

## Estimated Time

1-2 hours (simple refactor of display logic)

---

## Implementation Notes

**To decide during implementation:**
1. Which option (A/B/C/hybrid) best fits workflow?
2. Should ground truth be gitignored or checked in?
3. How to handle ground truth for future algorithm tuning episodes?

**Key principle:** Production use should require zero manual timestamp collection. Only add ground truth when needed for algorithm development/validation.

---

## Related Tasks

- [012-01: Match Start Detection](../012-classifier-integration/012-01-pipeline-integration.md) - Created CLI with hardcoded ground truth
- [012-02: Match End Detection](../012-classifier-integration/012-02-match-end-detection.md) - Will use same CLI, needs production-ready version
