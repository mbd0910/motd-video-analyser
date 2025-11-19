# Task 012-02: Match End Boundary Detection + Interlude Handling

**Status:** TODO - Planning Phase

## Quick Context

**Parent Task:** [012-classifier-integration](README.md)
**Prerequisites:** Task 012-01 complete (match_start detection working perfectly)
**Domain Concepts:** [Match Segments](../../domain/README.md#match-segments), [Running Order](../../domain/README.md#running-order)

**Why This Matters:** Complete the segment timeline by detecting where post-match analysis ends for each match. Handle BBC interlude breaks (advert segments) that appear between matches in some episodes, which break the naive `match_end = next_match.match_start` assumption.

---

## Objective

Implement robust match_end detection and interlude handling to create a complete, gap-free segment timeline for each MOTD episode.

---

## Current State (From 012-01)

**What's Working:**
- ✅ match_start detection: Venue + clustering strategies, 100% agreement, ±1.27s avg accuracy
- ✅ highlights_start: From OCR (first scoreboard appearance)
- ✅ highlights_end: From OCR (FT graphic timestamp)

**What's Naive:**
- ❌ match_end: Currently uses simplistic assumption:
  - Matches 1-6: `match_end = next_match.match_start`
  - Match 7: `match_end = episode_duration`

---

## The Interlude Problem

**Issue:** Episode 01 (motd_2025-26_2025-11-01) contains at least one BBC interlude (advert break) between matches. This breaks the `match_end = next_match.match_start` assumption.

**Example Failure:**
```
Match 3 (highlights_end = 00:41:30)
  → Post-match analysis...
  → Match 3 ends somewhere around 00:43:00 (unknown)
  → [BBC INTERLUDE: 00:43:00 - 00:44:30] ← Not detected!
  → Match 4 starts at 00:44:30

Current code: match_end = 00:44:30 (WRONG - includes interlude in Match 3!)
Correct: match_end = 00:43:00, separate interlude segment
```

**Impact:**
- Incorrect match_end timestamps for matches surrounding interludes
- Post-match analysis airtime calculations will be wrong
- Segment timeline has gaps (interludes unaccounted for)

---

## Approach

### Phase 1: Observe the Problem (Don't Fix Yet)

**Goal:** Understand what actually breaks with current naive implementation.

**Steps:**
1. Run current detection on Episode 01
2. For each match, calculate: `next_match.match_start - current_match.highlights_end`
3. Identify which gaps are:
   - Normal post-match analysis (10-120 seconds)
   - Suspiciously long (>2 minutes) → likely interlude
4. Manual verification: Watch video at suspicious timestamps
5. Document findings:
   - Where are interludes? (which matches?)
   - How long are they?
   - What visual/audio patterns appear?
   - Are there other types of gaps?

**Deliverable:** Ground truth table of actual match_end timestamps and interlude locations.

---

### Phase 2: Detection Strategy (To Be Planned)

**Once we understand the problem, plan detection approach.**

Possible strategies to explore:
- **Scene Detection:** Fade to black, BBC logo appearance
- **OCR Patterns:** BBC branding graphics, "Coming up" text
- **Audio Analysis:** Music patterns, silence during interlude
- **Transcript Gaps:** No speech during interlude periods
- **Studio Return Detection:** Scene change back to studio for next match

**Note:** Strategy selection will depend on Phase 1 findings.

---

### Phase 3: Implementation (To Be Planned)

**TBD based on chosen strategy.**

Likely includes:
- Update `detect_match_boundaries()` to detect match_end properly
- Add `Interlude` segment type to Pydantic models (if needed)
- JSON output includes complete timeline (matches + interludes)
- Update tests to cover interlude cases

---

### Phase 4: Validation (To Be Planned)

**Success criteria:**
- All 7 matches have accurate match_end timestamps (±10s)
- Interludes identified and timestamped (if present)
- No gaps or overlaps in complete segment timeline
- JSON output is valid and complete
- Tests cover interlude edge cases

---

## Estimated Time

**TBD** - Likely 3-4 hours once strategy is planned.

**Breakdown estimate (provisional):**
- Phase 1 (Gap Analysis): 30-45 mins
- Phase 2 (Strategy Planning): 15-30 mins
- Phase 3 (Implementation): 1.5-2 hours
- Phase 4 (Validation): 30-45 mins

---

## Next Steps

**Start Phase 1 gap analysis in a new Claude Code session.**

Do NOT attempt to fix interludes until we understand:
1. Where they are
2. How long they are
3. What patterns we can detect
4. Whether other gap types exist (studio segments, recaps, etc.)

Premature optimization without understanding the problem will waste time.

---

## Related Tasks

- [012-01: Match Start Detection](012-01-pipeline-integration.md) - Completed (prerequisite)
- [012: Classifier Integration](README.md) - Parent task
