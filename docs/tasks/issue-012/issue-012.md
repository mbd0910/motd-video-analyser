# Issue #12: Update Documentation for LLM Workflow

**GitHub Issue:** [#12](https://github.com/mbd0910/motd-video-analyser/issues/12)
**Branch:** `feature/issue-12-llm-docs`
**Status:** In Progress

## Overview

Update all documentation to reflect the LLM-based analysis workflow (Issue #6). The documentation still references OCR/rule-based detection as the primary approach; it should now position the LLM workflow as primary and OCR/venue/clustering as advisory hints.

**Key Deliverable:** Documentation that accurately reflects current workflow state.

## Critical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary approach | LLM workflow | Issue #6 pivot - rule-based struggled with nuanced boundaries |
| OCR/venue/clustering | Advisory hints | Still run, but produce hints for LLM prompt, not final analysis |
| Historical context | One brief sentence | "LLM replaced rule-based approach, which struggled with boundaries" |
| Documentation style | Current state only | No "we used to do X" sections - per user preference |

---

## Phase 0: Setup

- [x] Create branch: `feature/issue-12-llm-docs`
- [x] Create this task file
- [x] Initial commit with task file
- [x] Add comment to GitHub issue with task file link

## Phase 1: Update Core Documentation

### 1.1 CLAUDE.md
- [x] Update Project Context to mention LLM workflow
- [x] Update "What This Project Does" section
- [x] Add `generate-llm-prompt` to Common Commands
- [x] Reframe OCR/transcription as advisory hint sources

### 1.2 algorithm.md
- [x] Complete rewrite to brief LLM workflow
- [x] Document 4-step workflow (run pipeline → generate prompt → Claude analysis → save results)
- [x] Add advisory hints table
- [x] Link to analysis_schema.md for output format

### 1.3 README.md
- [x] Remove "Multi-Strategy Detection" section (lines 44-72)
- [x] Promote LLM workflow to primary position in "How It Works"
- [x] Update "What happens" description under Usage
- [x] Keep Quick Start commands, reframe context

## Phase 2: Update Technical Documentation

### 2.1 architecture.md
- [x] Update pipeline diagram in Section 1
- [x] Simplify Section 4.5 (Running Order Detection) - now produces hints
- [x] Simplify Section 4.6 (Match Boundary Detection) - retitle to advisory hints
- [x] Remove/replace Section 4.7 (Segment Classification) - now LLM-based
- [x] Update Section 9 (Performance) with `generate-llm-prompt` step

### 2.2 docs/domain/README.md
- [x] Update intro to clarify workflows produce hints for LLM
- [x] Reframe Workflow 1 as "OCR Hint Extraction"
- [x] Update Workflow 2 (Fixture Matching) context
- [x] Remove Workflow 3 (Segment Classification) - now LLM-based

## Phase 3: Testing, Code Review & Merge

Follow standard `/code-review main` and `/issue-workflow` merge process.

---

## Notes & Decisions

*(Capture architectural decisions during implementation)*
