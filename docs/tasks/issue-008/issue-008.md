# Issue #8: End-to-End Validation of LLM Transcript Analysis

**GitHub Issue:** [#8](https://github.com/mbd0910/motd-video-analyser/issues/8)
**Branch:** `feature/issue-8-llm-validation`
**Status:** In Progress
**Depends on:** Issue #7 (CLOSED)

## Overview

Validate the complete LLM-based transcript analysis workflow from Issue #6 with clean OCR data (post-Issue #7 fix).

**Key Deliverable:** Confirmed working LLM prompt that produces accurate segment detection in Claude web UI.

## Pre-conditions Verified

- [x] Issue #7 fix merged (scoreboard validation)
- [x] OCR results re-run with fix (Dec 16 10:05)
- [x] 7 FT graphics detected (one per match)
- [x] 186 scoreboards detected (no false positives)
- [x] No spurious Brighton detection at 39s in intro

---

## Phase 0: Setup

- [x] Create branch: `feature/issue-8-llm-validation`
- [x] Create this task file
- [ ] Initial commit

## Phase 1: Generate Fresh LLM Prompt

- [ ] Run `python -m motd generate-llm-prompt motd_2025-26_2025-11-22 --force`
- [ ] Verify prompt includes 7 FT graphic hints
- [ ] Verify prompt includes first scoreboard hints (7 matches)
- [ ] Note token count for reference

## Phase 2: Manual Test in Claude Web UI

- [ ] Copy prompt to clipboard
- [ ] Paste into Claude web UI
- [ ] Receive JSON response from Claude

## Phase 3: User Validation

User manually checks:
- [ ] All 7 matches detected in correct order
- [ ] Segment boundaries look reasonable
- [ ] JSON output is parseable
- [ ] No spurious OCR hints in prompt

## Phase 4: Close Issues

- [ ] Update Issue #6 task file - mark manual test complete
- [ ] Close Issue #8 with validation results
- [ ] Close Issue #6 (code complete, validation passed)

---

## Notes & Decisions

*(Capture learnings, deviations, observations here)*
