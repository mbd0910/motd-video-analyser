# Issue #002: Simplify Interlude Detection

**GitHub Issue:** [#2](https://github.com/mbd0910/motd-video-analyser/issues/2)

## Overview

Replace fragile team name fuzzy matching in interlude detection with scoreboard/FT graphic absence check. This is more reliable because:
- Women's football news mentions team names but never shows Premier League graphics
- Absence of match graphics is binary, not fuzzy

## Critical Thinking

**Problem:** Current team name check (even with strict substring) can false-positive on:
- Women's teams with identical names (Manchester United Women)
- Any mention of team name in news/commentary

**Solution:** Check for absence of scoreboards/FT graphics in validation window instead.
- If match graphics exist → it's a match, not interlude
- If no graphics → interlude is valid (combined with keyword check)

**Decision:** Remove team name check entirely (simpler code, stronger signal from graphics check).

---

## Phase 0: Setup

- [x] Create branch: `feature/issue-002-simplify-interlude`
- [x] Create task file

## Phase 1: TDD - Write Tests First

- [x] Add test: interlude with team name mentioned but NO scoreboards → should detect
- [x] Add test: window with scoreboard present → should reject

## Phase 2: Implementation

- [x] Remove team name validation from `_detect_interlude()` (lines ~1286-1298)
- [x] Add scoreboard/FT absence check in validation window
- [x] Use `self.ocr_results` (already available on detector instance)

## Phase 3: Verification

- [x] All existing interlude tests pass (203/203)
- [x] New TDD tests pass (15 interlude tests total)
- [x] Manual: Episode 01 + 02 interludes detected correctly

## Phase 4: Test Infrastructure (Added)

Refactored tests to eliminate cache dependency:

- [x] Created `tests/fixtures/episodes/` with minimal episode JSON files (~400KB each)
- [x] Created `tests/fixtures/patterns/interlude_patterns.json` with 7 synthetic patterns
- [x] Added `TestInterludePatterns` class with parameterized tests
- [x] Updated fixtures to load from `tests/fixtures/` instead of `data/cache/`
- [x] All 203 tests pass with no cache dependency

**Benefits:**
- Tests work in CI/CD without cache files
- Minimal fixtures are ~400KB vs ~130MB full cache
- Synthetic patterns document expected behaviour explicitly

## Code Review & Merge

See [issue-workflow.md](/.claude/commands/issue-workflow.md) for standard process.

---

## Notes & Decisions

- Chose to remove team name check entirely rather than keep as secondary filter
- Scoreboard/FT absence is sufficient validation combined with keyword presence
- Created minimal episode fixtures with just the fields needed (segments + OCR results)
- Added parameterized pattern tests for explicit edge case documentation
