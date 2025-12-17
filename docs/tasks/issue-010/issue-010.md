# Issue #10: Fix Stage 4 Analysis Failures

**GitHub Issue:** https://github.com/mbd0910/motd-video-analyser/issues/10
**Branch:** `feature/issue-10-fix-stage4-failures`

## Overview

3 out of 13 episodes failed Stage 4 (Running Order Analysis) during overnight batch run:
- `2025-11-09`: NoneType comparison crash in `_detect_match_start()`
- `2025-12-03`: Position constraint violation (9 matches, limit was 7)
- `2025-12-07`: NoneType comparison crash in `_detect_match_end()`

## Critical Thinking

### Root Cause Analysis

**Bug 1: NoneType comparisons**
- `highlights_end` and `highlights_start` are typed as `float | None` in `MatchBoundary` model
- When previous match has `highlights_end = None`, it's passed as `search_start` to boundary detection functions
- Line 386: `if search_start <= s.get('start', 0) < highlights_start` crashes

**Bug 2: Position constraint**
- `MatchBoundary.position` has `le=7` constraint
- Midweek fixtures episodes (like 2025-12-03) can have 9 matches

### Design Decision: Empty Range vs Fallback

**Rejected approach:** Use 0.0 as fallback for `search_start` (would search entire episode, potentially wrong matches)

**Chosen approach:** Return `None` when search window is undefined
- If `search_start` or `highlights_start` is `None`, return `None` immediately
- Honest signal: "we can't detect this boundary"
- Caller handles gracefully

## Phase 0: Setup

- [x] Create feature branch
- [x] Create task file
- [x] Add bi-directional link to GitHub issue

## Phase 1: TDD - Write Failing Tests

- [x] Test: `_detect_match_start()` returns `None` when `search_start` is `None`
- [x] Test: `_detect_match_start()` returns `None` when `highlights_start` is `None`
- [x] Test: `_detect_match_end()` handles `highlights_end = None` gracefully
- [x] Test: `MatchBoundary` accepts position 8, 9, 10
- [x] Verify tests fail before implementation

## Phase 2: Implementation

- [x] Update `MatchBoundary.position` constraint from `le=7` to `le=10`
- [x] Add null guard to `_detect_match_start()` - return `None` if window undefined
- [x] Add null guard to `_detect_match_start_venue()` - same pattern
- [x] Add null guard to `_detect_match_start_clustering()` - same pattern
- [x] Add null guard to `_detect_match_end()` - return naive fallback if `highlights_end` is `None`
- [x] Verify all new tests pass (12/12 passed)
- [x] Verify existing tests still pass (186 unit tests passed)

## Phase 3: Validation

- [x] Re-run failed episodes:
  ```bash
  python -m motd run data/videos/motd_2025-26_2025-11-09.mp4
  python -m motd run data/videos/motd_2025-26_2025-12-03.mp4
  python -m motd run data/videos/motd_2025-26_2025-12-07.mp4
  ```
- [x] Verify all 3 complete Stage 4 successfully

## Final Phase: Code Review & Merge

See [Issue Workflow](.claude/commands/issue-workflow.md) for standard code review and merge process.

## Files to Modify

- `src/motd/pipeline/models.py` - Update position constraint (line 248)
- `src/motd/analysis/running_order_detector.py` - Add null guards
- `tests/unit/analysis/test_running_order_detector.py` - Add new tests

## Notes & Decisions

- **Empty range over fallback**: Returning `None` is more honest than guessing with potentially wrong data
- **Position limit 10**: Allows for midweek double-headers (Tue+Wed combined = up to 10 matches)
