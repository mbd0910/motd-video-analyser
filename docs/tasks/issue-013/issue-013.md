# Issue #13: Delete deprecated OCR/rule-based code

**GitHub Issue:** [#13](https://github.com/mbd0910/motd-video-analyser/issues/13)

## Overview

Delete the deprecated rule-based running order detection code and replace Stage 4 of the pipeline with automatic LLM prompt generation. The new pipeline will be:

1. Scene Detection → 2. OCR/Team Extraction → 3. Transcription → **4. Generate LLM Prompt**

This removes ~150KB of unused code and makes `python -m motd run <video>` a complete end-to-end pipeline.

## Critical Thinking

### Background

Issue #6 pivoted from OCR/rule-based analysis to LLM-based analysis. The old code was marked as "deprecated but not deleted". Issue #13 is the follow-up to actually delete that code. However, the code was never properly isolated - it's still fully integrated into the CLI.

### Key Decisions

1. **Command name discrepancy**: Issue mentions `detect-running-order` but actual command is `analyze-running-order`. Confirmed with user to delete `analyze-running-order`.

2. **Stage 4 replacement**: Instead of removing Stage 4, replace it with "Generate LLM Prompt" functionality. This makes `python -m motd run <video>` a complete pipeline.

3. **Scope expansion**: Issue doesn't mention several related files that also need deletion:
   - `src/motd/cli/running_order_output.py`
   - `src/motd/cli/diagnostics.py`
   - Several test files

4. **Test safety**: Verified that sentence extraction tests (`test_sentence_extraction.py`) are only for deprecated code - the LLM pipeline uses `TranscriptFormatter` with its own deduplication logic.

5. **Keep venues data**: User decided to keep `data/venues/` as historical reference data.

---

## Phase 0: Setup

- [x] Create feature branch: `feature/issue-13-delete-deprecated-code`
- [x] Create task file
- [x] Initial commit with task file

## Phase 1: Delete deprecated source files

- [x] Delete `src/motd/analysis/` directory (entire directory)
- [x] Delete `src/motd/cli/running_order_output.py`
- [x] Delete `src/motd/cli/diagnostics.py`

## Phase 2: Clean up models.py

- [x] Remove `BoundaryValidation` model
- [x] Remove `MatchBoundary` model
- [x] Remove `RunningOrderResult` model
- [x] Keep: `Scene`, `TeamMatch`, `OCRResult`, `ProcessedScene`

## Phase 3: Update __main__.py

- [x] Remove deprecated imports (lines 26, 28, 29-32, 33)
- [x] Delete `run_analysis()` function
- [x] Delete `analyze-running-order` command
- [x] Add `run_llm_prompt_generation()` function (new Stage 4)

## Phase 4: Update orchestrator.py

- [x] Change return type to `BuiltPrompt`
- [x] Rename `_run_stage_4_analysis()` → `_run_stage_4_llm_prompt()`
- [x] Update stage labels
- [x] Update docstrings

## Phase 5: Delete deprecated test files

- [x] Delete `tests/unit/analysis/` directory
- [x] Delete `tests/cli/` directory
- [x] Delete `tests/test_venue_matcher.py`

## Phase 6: Update documentation

- [x] Update `docs/algorithm.md`

## Phase 7: Testing & Code Review

- [x] Run pytest - 211 passed, 12 failed (pre-existing scoreboard integration test failures, not related to this PR)
- [x] Verify CLI commands work
- [ ] Code review via `/code-review main`

## Notes & Decisions

- The deprecated code is ~150KB total
- LLM tests (test_llm_*.py) are kept - they test the active pipeline
- Sentence extraction in deprecated code is completely separate from LLM TranscriptFormatter
- `data/venues/` kept as historical reference data (user request)
