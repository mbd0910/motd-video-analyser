# Issue #14: Process All Episodes with LLM Analysis

**GitHub Issue:** https://github.com/mbd0910/motd-video-analyser/issues/14
**Branch:** `feature/issue-14-llm-analysis`
**Status:** In Progress

## Overview

Prepare infrastructure for LLM analysis of 13 MOTD episodes, including:
1. Directory structure for analysis output
2. Validation script for JSON schema
3. **Fix discovered:** Whisper timestamp hallucination during non-speech audio

## Discovery: Whisper Timestamp Bug

During initial testing, we discovered that Whisper produces incorrect timestamps for segments following non-speech audio (e.g., title music).

### Example (motd_2025-26_2025-10-25)

```
Segment 0: [9.23-10.81]  "Welcome to Match of the Day."  ✓ Correct
Segment 1: [11.37-53.52] "It's been a terrific day..."   ✗ Wrong start time
```

Word-level analysis revealed:
```
[11.37-11.89]  It's        ← HALLUCINATED (misheard music)
[51.86-51.98]  been        ← ACTUAL speech starts here
[51.98-52.08]  a
[52.08-52.34]  terrific
```

**Root cause:** Whisper hallucinates words during music/non-speech, causing the segment start time to be ~40 seconds too early.

**Impact:** 11 of 13 episodes have at least one segment with >20 second duration for short text.

### Fix

Use word-level timestamps to detect hallucination gaps. If gap between first and second word exceeds threshold (5s), use second word's start time as segment start.

---

## Phase 0: Setup

- [x] Create feature branch
- [x] Create task file
- [x] Create 13 analysis directories under `data/analysis/`
- [x] Create validation script `scripts/validate_analysis.py`
- [x] Add batch command to GitHub issue comment

## Phase 1: Fix Whisper Timestamp Hallucination

- [x] Update `TranscriptFormatter` to use word-level timestamps
- [x] Add gap detection logic (threshold: 5 seconds)
- [x] Add unit tests for the fix (6 new tests, 23 total)
- [x] Delete existing transcript_for_llm.txt files
- [x] Regenerate prompts for all 13 episodes

## Phase 2: Manual LLM Analysis (User Responsibility)

For each episode:
1. Open `data/cache/{episode_id}/transcript_for_llm.txt`
2. Paste into fresh Claude conversation
3. Save JSON response to `data/analysis/{episode_id}/analysis.json`
4. Validate with `python scripts/validate_analysis.py`

## Phase 3: Commit & Merge

- [ ] Commit all analysis JSON files
- [ ] Run code review
- [ ] Squash merge to main

---

## Files Modified

| File | Change |
|------|--------|
| `data/analysis/motd_2025-26_*/` | Created 13 directories |
| `scripts/validate_analysis.py` | New validation script |
| `src/motd/llm/transcript_formatter.py` | Fix timestamp hallucination |
| `tests/test_transcript_formatter.py` | New tests for fix |

## Notes & Decisions

### Word-level timestamp strategy

Using word-level timestamps when available. If gap between word[0].end and word[1].start > 5 seconds, use word[1].start as segment start time. This handles the common case of hallucinated words during title music.

Threshold of 5 seconds chosen because:
- Normal speech gaps are <2 seconds
- Title music sequences are typically 30-50 seconds
- Gives buffer for natural pauses without over-correcting
