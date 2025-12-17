# Issue #11: Source of Truth / Episode Completion

**GitHub Issue:** [#11](https://github.com/mbd0910/motd-video-analyser/issues/11)
**Branch:** `feature/issue-11-source-of-truth`
**Status:** In Progress

## Overview

Define where to store LLM analysis output and clean up stale data from the deprecated OCR/rule-based approach.

**Key Deliverable:** Storage location for LLM analysis results + cleanup of confusing legacy data.

## Critical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage location | `data/analysis/{episode_id}/analysis.json` | Consistent with existing cache structure |
| Pydantic models | Deferred | Not needed until code consumes the files |
| CLI tooling | Deferred | Manual copy-paste workflow for now |
| Validation | Deferred | Trust LLM output, manual spot-checking |

---

## Phase 0: Setup

- [x] Create branch: `feature/issue-11-source-of-truth`
- [x] Create this task file

## Phase 1: Delete Stale Data

Remove files from deprecated OCR/rule-based approach:

- [x] Delete `data/output/*/running_order.json` (not tracked - gitignored)
- [x] Delete `data/output/*/clustering_debug.json` (not tracked - gitignored)
- [x] Delete `data/ground_truth/episode_boundaries.json`
- [x] Commit deletion

## Phase 2: Define Storage Location

- [x] Create `data/analysis/.gitkeep` to establish directory
- [x] Commit

## Phase 3: Document JSON Schema

- [x] Create `docs/domain/analysis_schema.md` with expected JSON structure
- [x] Commit

## Phase 4: Update GitHub Issue

- [x] Add comment to issue #11 summarising decisions
- [x] Link to follow-up issues

## Phase 5: Create Follow-up Issues

- [x] Create issue #12: Update documentation for LLM workflow
- [x] Create issue #13: Delete deprecated code
- [x] Create issue #14: Process all episodes with LLM analysis

## Final Phase

- [ ] Code review (if needed)
- [ ] Squash merge to main

---

## Notes & Decisions

- **2025-12-17:** Issue #6 pivoted from OCR/rule-based to LLM-based analysis. The old `running_order.json` files are stale and cause confusion.
- **2025-12-17:** Decided to keep scope minimal - just define storage location and clean up. Pydantic models and CLI tooling can come later when there's actual code consuming the analysis files.
