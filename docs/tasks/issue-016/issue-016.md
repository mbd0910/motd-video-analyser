# Issue #016: Tidy up scripts directory

**GitHub Issue:** [#16](https://github.com/mbd0910/motd-video-analyser/issues/16)

## Overview

Delete unused one-off scripts from `scripts/` directory, keep 3 useful debugging tools, and improve them for ongoing use.

## Critical Thinking

### Problem Analysis
The `scripts/` directory accumulated 14 one-off scripts during development (Tasks 009-011). Most are historical reconnaissance or debugging tools that are no longer needed. However, three scripts provide ongoing value for manual debugging when working on the project.

### Decision: Keep 3 Scripts
1. `test_fixture_matcher.py` - Useful for verifying fixture data for new episodes
2. `test_ocr_region.py` - Useful when BBC changes video resolution
3. `visualize_ocr_regions.py` - Useful for calibration verification

### Improvements Planned
- Add CLI arguments (remove hardcoded values)
- Read config from `config.yaml` instead of duplicating
- Rename for clarity (`debug_*` prefix)
- Add `scripts/README.md` for documentation

---

## Phase 0: Setup

- [x] Create feature branch `feature/issue-16-tidy-scripts`
- [x] Create task file
- [x] Add bi-directional link to GitHub issue

## Phase 1: Delete Unused Scripts

- [x] Delete `analyze_match_boundaries.py`
- [x] Delete `analyze_reconnaissance.py`
- [x] Delete `debug_ocr_frame.py`
- [x] Delete `generate_short_names.py`
- [x] Delete `generate_short_names_v2.py`
- [x] Delete `generate_short_names_v3.py`
- [x] Delete `generate_short_names_v4.py`
- [x] Delete `test_ocr.py`
- [x] Delete `test_scene_501.py`
- [x] Delete `test_team_matcher.py`
- [x] Delete `scripts/__pycache__/`

## Phase 2: Improve Kept Scripts

- [x] Rename and improve `test_fixture_matcher.py` → `debug_fixtures.py`
- [x] Rename and improve `test_ocr_region.py` → `debug_ocr_region.py`
- [x] Rename and improve `visualize_ocr_regions.py` → `visualize_regions.py`

## Phase 3: Documentation

- [x] Add `scripts/README.md` documenting the debugging tools

## Phase 4: Finalise

- [x] Run tests to ensure nothing broke (206 passed, 2 xfailed)
- [ ] Code review (see [issue-workflow.md](/.claude/commands/issue-workflow.md))
- [ ] Squash merge to main

---

## Notes & Decisions

- Kept scripts renamed with `debug_` prefix to clarify their purpose as debugging tools
- All scripts improved to read from `config/config.yaml` instead of hardcoding values
- CLI arguments added to all scripts for flexibility
