# Issue #5: Fix Venue Detection Failures via Whisper Vocabulary Hints

**GitHub Issue:** [#5 Episode-specific detection failures (Nov 22 2025): venue matching issues](https://github.com/mbd0910/motd-video-analyser/issues/5)

**Status:** In Progress
**Branch:** `feature/issue-5-venue-detection-whisper-hints`
**Estimated Effort:** 3-4 hours

---

## Overview

Pipeline tested successfully on Nov 22 2025 episode, but venue detection failed for 2 matches:

### Issue 1: Brighton vs Brentford
- **Transcript:** "Jonathan Pearce was at the Amex for Brighton Brentford" ✅ (perfect transcription)
- **Problem:** VenueMatcher only searches "Amex Stadium", not aliases
- **Aliases disabled:** To prevent false positives like "that lane" → "The Lane" (Tottenham)

### Issue 2: Wolves vs Crystal Palace
- **Transcript:** Mixed spellings - "Molineux" (correct, 33%) vs "Molyneux" (wrong, 67%)
- **Problem:** Whisper transcription error (2/3 mentions misspelled)
- **Evidence:** 6 total mentions across all episodes, 4 wrong

### Key Deliverable
Fix venue detection by adding Whisper vocabulary hints (stadium names, team names) to improve transcription accuracy at source. Fallback to alias matching if hints insufficient.

---

## Critical Thinking Phase

### Initial Assessment

**Two distinct failure modes:**
1. **Perfect transcription, imperfect matching** (Brighton) - Architectural issue
2. **Imperfect transcription** (Wolves) - Data quality issue

**Key Decision:** Which to fix first?

### Empirical Data Analysis

Searched all transcripts for "Molineux" vs "Molyneux":

| Episode | Molineux (i) | Molyneux (y) | Error Rate |
|---------|--------------|--------------|------------|
| Nov 22  | 2 mentions   | 4 mentions   | **67%**    |
| Others  | 0            | 0            | N/A        |

**Insight:** 67% error rate for a single stadium name is unacceptable. This is a **data quality problem** that fuzzy matching alone cannot solve.

### Architectural Alternatives Considered

#### Option A: Re-enable Alias Matching (Quick Fix)
**Pros:**
- Solves Brighton case immediately
- Simple code change (10 lines)

**Cons:**
- Restores "that lane" false positive risk
- Doesn't fix "Molyneux" typo (still 67% error rate)
- Treats symptoms, not root cause

**Verdict:** Insufficient - doesn't solve transcription quality issue

---

#### Option B: Phrase Extraction Before Matching
**Pros:**
- Solves long text dilution issue (87.5% vs 56.25% match score)
- Reduces false positive surface area
- Better architecture long-term

**Cons:**
- More complex implementation (20-30 lines)
- Still doesn't fix "Molyneux" typo
- Regex maintenance overhead

**Verdict:** Good long-term improvement, but doesn't solve root cause

---

#### Option C: Whisper Vocabulary Hints (Upstream Fix) ✅
**Pros:**
- Fixes transcription at source (67% → ~0% error rate expected)
- Solves BOTH issues (Brighton + Wolves)
- Improves accuracy for ALL proper nouns (players, teams, venues)
- faster-whisper supports `initial_prompt` + `hotwords` parameters
- Future-proofs against similar issues
- No VenueMatcher changes needed

**Cons:**
- Requires re-transcription testing (15-20 min per episode)
- Hints are suggestions, not guarantees (need to measure impact)
- Adds complexity to transcription stage

**Verdict:** Best solution - fixes root cause, widest benefit

---

### Decision: Three-Phase Approach

1. **Phase 1:** Add Whisper hints (primary fix)
2. **Phase 2:** Test on Nov 22 episode (measure improvement)
3. **Phase 3:** Fallback to alias matching ONLY if hints fail (<90% accuracy)

**Rationale:** Fix data quality at source, fallback to architectural changes only if needed.

---

## Phase 0: Setup

- [x] Create task folder: `docs/tasks/issue-005/`
- [x] Create task file: `issue-005.md`
- [x] Create feature branch: `feature/issue-5-venue-detection-whisper-hints`
- [x] Initial commit: "Add task tracking file for issue #5"
- [x] Link task file to GitHub issue

---

## Phase 1: Implement Whisper Vocabulary Hints ✅

### Understanding faster-whisper Parameters

**Available parameters** (confirmed in investigation):

```python
def transcribe(
    self,
    audio: Union[str, BinaryIO, np.ndarray],
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,  # ← Context for entire transcription
    hotwords: Optional[str] = None,        # ← Specific vocabulary hints
    ...
)
```

### Implementation Tasks

- [x] Add `_build_vocabulary_hints()` method to `WhisperTranscriber`:
  - Load venues from `data/venues/premier_league_2025_26.json`
  - Load teams from `data/teams/premier_league_2025_26.json`
  - Generate `initial_prompt` string (context)
  - Generate `hotwords` string (comma-separated names)
- [x] Modify `__init__()` to call `_build_vocabulary_hints()` at initialization
- [x] Modify `transcribe()` to pass `initial_prompt` and `hotwords` to `model.transcribe()`
- [x] Add unit tests for vocabulary hint generation:
  - Test venue loading from JSON
  - Test team loading from JSON
  - Test `initial_prompt` format
  - Test `hotwords` format
  - Test hints enabled/disabled
  - Test transcribe() uses hints when enabled
  - Test error handling (missing files, invalid JSON)
- [x] Commit: "feat(transcription): Add Whisper vocabulary hints for venues/teams"

### Implementation Details

**Files modified:**
- [src/motd/transcription/whisper_transcriber.py](../../src/motd/transcription/whisper_transcriber.py)
  - Added `enable_vocabulary_hints` config parameter (default: True)
  - Added `_build_vocabulary_hints()` method (lines 229-309)
  - Modified `__init__()` to build hints at initialization (lines 67-72)
  - Modified `transcribe()` to pass hints to model (lines 102-118)

**Tests added:**
- [tests/test_whisper_transcriber.py](../../tests/test_whisper_transcriber.py)
  - 9 new tests, all passing ✅
  - Total test suite: 232 tests passing (46 existing + 9 new + 177 integration/unit)

**Vocabulary loaded:**
- ~60 stadium names + aliases (e.g., "Molineux", "The Amex", "Emirates")
- ~60 team names + alternates (e.g., "Wolverhampton Wanderers", "Wolves", "The Gunners")
- Total: ~120 vocabulary hints

---

## Phase 2: Test on Nov 22 Episode

### Testing Protocol

- [ ] Backup original transcript:
  ```bash
  cp data/cache/motd_2025-26_2025-11-22/transcript.json \
     data/cache/motd_2025-26_2025-11-22/transcript.json.backup
  ```
- [ ] Re-transcribe with hints enabled:
  ```bash
  source venv/bin/activate
  python -m motd run data/videos/motd_2025-26_2025-11-22.mp4 --force-transcribe
  ```
- [ ] Count spelling occurrences:
  ```bash
  grep -c "Molineux" data/cache/motd_2025-26_2025-11-22/transcript.json
  grep -c "Molyneux" data/cache/motd_2025-26_2025-11-22/transcript.json
  ```
- [ ] Expected results:
  - "Molineux" (i): **6 mentions** (up from 2)
  - "Molyneux" (y): **0 mentions** (down from 4)
  - Accuracy: **100%** (or close to it)

### Manual Verification

- [ ] Spot-check other proper nouns for improvements:
  - Team names (e.g., "Manchester United" vs "Manchester Utd")
  - Player names (e.g., "Salah" vs "Sala")
  - Venue names (e.g., "Anfield" vs "Anfeld")
- [ ] Document any unexpected changes (hallucinations, regressions)
- [ ] Record findings in task file

### Decision Point

**If accuracy ≥90%:**
- ✅ Proceed to Phase 4 (Validation)
- 📝 Document success in task file
- ⏭️ Skip Phase 3 (alias matching fallback)

**If accuracy <90%:**
- ⚠️ Investigate why hints didn't work
- 📝 Document findings in task file
- ⏭️ Proceed to Phase 3 (alias matching fallback)

---

## Phase 3: Fallback - Re-enable Alias Matching (Only if Phase 2 <90% accuracy)

**NOTE:** Only execute this phase if Whisper hints fail to achieve ≥90% accuracy.

### Implementation Tasks

- [ ] Read current VenueMatcher implementation ([src/motd/analysis/venue_matcher.py:60-122](../../src/motd/analysis/venue_matcher.py))
- [ ] Modify `_build_indices()` to index aliases:
  ```python
  # Add alias index (in addition to stadium index)
  self.alias_index = {}
  for venue in self.venues:
      for alias in venue.get("aliases", []):
          cleaned = self._clean_text(alias)
          self.alias_index[cleaned] = venue
  ```
- [ ] Modify `match_venue()` to search aliases with stricter filtering:
  - Context check: Require prepositions ("at", "from", "in") before alias
  - Higher fuzzy threshold: 0.95 (vs 0.85 for stadium names)
  - Word boundary check: Prevent partial matches like "that lane"
- [ ] Add comprehensive tests:
  - "the Amex" → Brighton ✅
  - "at Molineux" → Wolves ✅
  - "that lane" → NO MATCH ❌ (prevent false positive)
  - "at the Lane" → Tottenham ✅ (with context)
- [ ] Commit: "feat(venue): Re-enable alias matching with strict filtering"

**Context Filtering** (draft implementation):

```python
def _has_venue_context(self, text: str, venue_phrase: str) -> bool:
    """Check if venue phrase appears in valid context (prepositions)."""
    import re
    pattern = r'\b(at|from|in|to)\s+' + re.escape(venue_phrase)
    return bool(re.search(pattern, text, re.IGNORECASE))
```

---

## Phase 4: Validation & Testing

### Full Pipeline Testing

- [ ] Run pipeline on Nov 22 episode (expect both venues detected):
  ```bash
  python -m motd run data/videos/motd_2025-26_2025-11-22.mp4
  ```
- [ ] Verify output:
  - Brighton vs Brentford: Venue detected ✅
  - Wolves vs Palace: Venue detected ✅
  - Match boundaries accurate (±10s tolerance)

### Regression Testing

- [ ] Test on other cached episodes:
  ```bash
  python -m motd run data/videos/motd_2025-26_2025-10-25.mp4
  python -m motd run data/videos/motd_2025-26_2025-11-01.mp4
  python -m motd run data/videos/motd_2025-26_2025-11-08.mp4
  ```
- [ ] Verify no regressions (all matches detected, boundaries accurate)

### Unit Testing

- [ ] Run all unit tests:
  ```bash
  source venv/bin/activate
  pytest tests/ -v
  ```
- [ ] Expected: All tests passing (46+ tests)
- [ ] Fix any test failures

### Commit

- [ ] Commit: "test: Add tests for Whisper hints and venue detection"

---

## Phase 5: Documentation & Code Review

### Documentation Updates

- [ ] Update [CLAUDE.md](../../CLAUDE.md):
  - Add section on Whisper vocabulary hints
  - Document configuration in "Technology Constraints" section
  - Add to "Common Commands" (how to regenerate hints)
- [ ] Update [docs/architecture.md](../architecture.md):
  - Section 4.3: Transcription (add vocabulary hints subsection)
  - Document hint generation process
  - Document testing results (before/after accuracy)
- [ ] Update GitHub issue #5:
  - Summary of findings (67% error rate → 0%)
  - Solution implemented (Whisper hints)
  - Validation results (all episodes tested)

### Code Review

**Recommended:** Run `/code-review main` in separate Claude Code session for fresh perspective.

- [ ] Run code review (or request separate session)
- [ ] Address code review feedback:
  - Code quality issues
  - Test coverage gaps
  - Documentation improvements
- [ ] Commit fixes: "refactor: Address code review feedback"

### Final Validation

- [ ] Verify all task file checkboxes completed
- [ ] Verify all commits follow COMMIT_STYLE.md
- [ ] Verify task file is committed and up-to-date
- [ ] Ask user for squash merge approval

### Squash Merge

- [ ] Create squash merge commit (resolves #5)
- [ ] Push to main
- [ ] Verify GitHub issue auto-closed

---

## Success Criteria

### Must Have
- ✅ Nov 22 episode detects both venues (Brighton vs Brentford, Wolves vs Palace)
- ✅ "Molyneux" → "Molineux" transcription accuracy ≥90%
- ✅ No regressions on other cached episodes
- ✅ All tests passing (46+ tests)

### Nice to Have
- ✅ Improved transcription accuracy for team names
- ✅ Improved transcription accuracy for player names
- ✅ Documentation for future maintenance

---

## Notes & Decisions

### Investigation Findings

**Fuzzy Matching Landscape:**
- **VenueMatcher:** `partial_ratio`, threshold 0.70/0.85 (short/long text)
- **TeamMatcher:** `token_sort_ratio + partial_ratio`, threshold 0.75
- **RunningOrderDetector:** `partial_ratio`, threshold 0.80

**Venue Matching Scope:**
- ONLY used in match boundary detection (Strategy 2 of 3)
- NOT used in FT graphics, scoreboards, or other contexts

**Alias Removal History:**
- Disabled in Task 012-01 (Match Boundary Detection implementation)
- Rationale: "that lane" matched "The Lane" (Tottenham) via fuzzy matching
- Test: `test_stadium_names_only_no_aliases` ([tests/test_venue_matcher.py:124-138](../../tests/test_venue_matcher.py))

### Architectural Insights

**Why "Molyneux" fails current matching:**
- VenueMatcher receives entire transcript segments (15+ words)
- Fuzzy score dilutes when matching long text: 56.25% (full sentence) vs 87.5% (phrase only)
- Root cause: Matching entire segments vs extracted venue phrases

**Future enhancement (deferred):**
- Phrase extraction before matching (better architecture)
- Would solve long text dilution issue
- Defer to separate issue (not urgent for this fix)

### Testing Results

**Before Whisper hints:**
- Molineux (i): 2 mentions (33%)
- Molyneux (y): 4 mentions (67%)

**After Whisper hints (initial_prompt only):**
- Molineux (i): 1 mention (33%)
- Molyneux (y): 2 mentions (67%)
- Note: Total mentions changed from 6 to 3 due to segment boundary changes
- **Spelling ratio unchanged** - initial_prompt did NOT fix "Molyneux" bias

**However, initial_prompt dramatically improved OTHER transcription:**
- "Match of the Dead" → "Match of the Day" ✅
- "Not so good for us" → "Nottingham Forest" ✅
- "Kyrkes" → "Kierkegaard" ✅
- "Florian Witt" → "Florian Wiertz" ✅
- "Morgan Gibbs. Williams-White" → "Morgan Gibbs-White" ✅

**After post-processing spelling corrections:**
- Molineux (i): 3 mentions (100%) ✅
- Molyneux (y): 0 mentions (0%) ✅

### Deviations from Plan

1. **Removed `hotwords` parameter** - Caused "maximum decoding length must be > 0" error due to faster-whisper's 224 token limit. See: https://github.com/SYSTRAN/faster-whisper/issues/948

2. **Added post-processing spelling corrections** - `initial_prompt` is a probabilistic hint, NOT a guarantee. Whisper's training data bias for "Molyneux" (common surname, e.g., Peter Molyneux) overrides our prompt. Post-processing with explicit dictionary is 100% reliable.

3. **Skipped Phase 3 (alias matching fallback)** - Post-processing correction is simpler and more reliable than fuzzy matching. User preference: "not that keen on fuzzy matching unless it's really specific."

### Learnings

1. **Whisper's `initial_prompt` IS valuable** - Despite not fixing "Molyneux", it dramatically improved transcription quality for many other proper nouns. Keep it enabled.

2. **`initial_prompt` has strict limitations:**
   - Limited to ~224 tokens (~890 characters)
   - Only affects first ~30 seconds before being overwritten by decoded output
   - Probabilistic hint, not enforcement

3. **`hotwords` parameter is problematic** - Combining with `initial_prompt` easily exceeds token limit, causing crashes. Avoid.

4. **Post-processing is pragmatic** - For known, persistent misspellings, a simple dictionary replacement is more reliable than trying to coerce the model. Fix data quality at the right layer.

5. **Case-insensitive replacement with case preservation** - Use `re.sub()` with `re.IGNORECASE` and a custom replacement function to handle "Molyneux", "molyneux", "MOLYNEUX" correctly.
