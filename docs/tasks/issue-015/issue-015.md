# Issue #015: Documentation Deprecation/Deletion

> **Last reviewed:** 2025-12-18

**GitHub Issue:** [#15](https://github.com/mbd0910/motd-video-analyser/issues/15)

## Overview

Clean up outdated documentation to ensure all markdown files reflect current state. Add "Last reviewed" headers to kept files. Condense historical task files.

## Phase 0: Setup
- [x] Create feature branch
- [x] Create this task file

## Phase 1: Delete Deprecated Files
- [x] Delete `docs/roadmap.md` (1,479 lines - superseded by README)
- [x] Delete `docs/prd.md` (378 lines - superseded by domain docs)
- [x] Delete `docs/project-setup.md` (44 lines - original brief)
- [x] Delete `docs/analysis_reconnaissance_report.md` (534 lines)
- [x] Delete `docs/scene_detection_tuning_report.md` (520 lines)
- [x] Delete `.claude/commands/task-workflow.md` (replaced by issue-workflow)
- [x] Delete `docs/tasks/README.md` (describes old task system)
- [x] Delete `docs/validation/` directory (4 files)
- [x] Delete `docs/ground_truth/` directory (4 files)

## Phase 2: Update future-enhancements.md
- [x] Add "Future Directions" section with high-level ideas

## Phase 3: Condense Completed Tasks
- [x] Condense `001-environment-setup/README.md`
- [x] Condense `002-create-project-structure/README.md`
- [x] Condense `003-install-python-dependencies/README.md`
- [x] Condense `004-create-team-and-fixture-data/README.md`
- [x] Condense `005-create-config-file/README.md`
- [x] Condense `006-implement-scene-detector/README.md`
- [x] Condense `007-implement-frame-extractor/README.md`
- [x] Condense `008-scene-detection-testing/` (merge subtasks into README)
- [x] Condense `009-ocr-implementation/` (merge subtasks into README)
- [x] Condense `010-transcription/` (merge subtasks into README)
- [x] Condense `011-analysis-pipeline/` (merge subtasks into README)
- [x] Condense `012-classifier-integration/` (merge subtasks into README)
- [x] Create `docs/tasks/completed/SUMMARY.md`

## Phase 4: Update BACKLOG.md
- [x] Simplify to redirect to GitHub Issues

## Phase 5: Add "Last Reviewed" Headers
- [x] Add headers to all kept files (18 files updated)

## Phase 6: Rewrite business_rules.md
- [x] Remove obsolete Rules 4-5 (not implemented in code)
- [x] Keep Rules 1-3 (FT validation, manifest constraint, opponent inference)
- [x] Add "LLM Analysis Context" section
- [x] Reduce from ~460 lines to ~150 lines

## Notes & Decisions

- Historical task workflow preserved in condensed form (approach + key decisions only)
- Code samples removed from all task files
- "Last reviewed" date added to enable staleness detection
