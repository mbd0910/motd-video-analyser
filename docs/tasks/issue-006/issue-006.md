# Issue #6: LLM-Based Transcript Analysis (Semi-Automated)

**GitHub Issue:** [#6](https://github.com/mbd0910/motd-video-analyser/issues/6)
**Branch:** `feature/issue-6-llm-transcript-analysis`
**Status:** In Progress

## Overview

Replace complex OCR/rule-based analysis with LLM-based transcript analysis. Focus on **semi-automated workflow**: generate an optimised transcript file for copy-paste into Claude web UI.

**Key Deliverable:** `python -m motd generate-llm-prompt <episode_id>` command.

## Critical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Workflow | Semi-automated (copy-paste) | API automation is lower priority than fixtures/manifest automation |
| Transcript format | Plain text with timestamps | LLMs handle this well; simpler than JSON |
| Include OCR hints | Yes, as advisory data | FT graphics + first scoreboard timestamps help anchor Claude |
| Deduplication | Yes | Remove Whisper "stutter" duplicates |

## Output Schema (v1)

See [plan file](/Users/michael/.claude/plans/eager-hugging-trinket.md) for full schema.

**Match segments:** studio_intro → lineups → highlights → post_match_interviews → studio_analysis
**Episode segments:** intro, league_table, next_motd_promo, outro

---

## Phase 0: Setup

- [x] Update GitHub issue #6 with planning decisions
- [x] Create branch: `feature/issue-6-llm-transcript-analysis`
- [x] Create this task file

## Phase 1: Transcript Processing Module

**File:** `src/motd/llm/transcript_formatter.py`

- [x] Create `TranscriptFormatter` class
- [x] Implement `load_transcript(cache_path)` - load from transcript.json
- [x] Implement `deduplicate_segments(segments)` - remove consecutive duplicates
- [x] Implement `format_as_text(segments)` - convert to timestamped text
- [x] Add unit tests (17 tests)

## Phase 2: OCR Hints Extraction

**File:** `src/motd/llm/ocr_hints.py`

- [x] Create `OCRHintsExtractor` class
- [x] Implement `extract_ft_graphics(ocr_results)` - find FT graphic timestamps
- [x] Implement `extract_first_scoreboards(ocr_results)` - first scoreboard per match
- [x] Implement `format_hints_section()` - format as markdown for prompt
- [x] Add unit tests (18 tests)

## Phase 3: Prompt Template

**File:** `src/motd/llm/prompt_builder.py`

- [x] Create `PromptBuilder` class
- [x] Load fixtures for episode date from episode manifest
- [x] Build prompt sections (header, fixtures, task, schema, hints, transcript)
- [x] Implement `build_prompt()` - assemble all sections
- [x] Add unit tests (13 tests)

## Phase 4: CLI Command

**File:** `src/motd/__main__.py`

- [x] Add `generate-llm-prompt` command
- [x] Arguments: episode_id, --output, --include-hints/--no-hints, --force
- [x] Print summary (token estimate, path, copy-paste instructions)

## Phase 5: Validation & Testing

- [x] Test on 2025-11-22 episode
- [x] Verify deduplication removes 12 known duplicates ✓
- [x] Check token count (~22k tokens) ✓
- [ ] Manual test in Claude web UI (pending user validation)

## Phase 6: Documentation

- [x] Update README with new workflow
- [ ] Document prompt template structure (deferred - schema may iterate)
- [ ] Signpost deprecated code (separate cleanup issue - #TBD)

## Code Review

Follow standard `/code-review main` workflow before merge.

---

## Notes & Decisions

*(Capture learnings, deviations, architecture decisions here)*

- **2025-12-12:** Planning complete. Semi-automated approach chosen over full API integration.
- **2025-12-12:** Implementation complete. 48 unit tests, CLI command working.
  - TranscriptFormatter: Deduplicates Whisper stutters (12 removed on Nov 22 episode)
  - OCRHintsExtractor: Extracts 7 FT graphics + 7 first scoreboards as advisory hints
  - PromptBuilder: Generates ~22k token prompt with fixtures, instructions, schema, hints, transcript
  - CLI: `python -m motd generate-llm-prompt <episode_id>` with --no-hints and --force options
