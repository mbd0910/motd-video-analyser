# Task 012-01: Pipeline Integration + Match Boundary Detection

## Quick Context

**Parent Task:** [012-classifier-integration](README.md)
**Prerequisites:** Task 011 complete (RunningOrderDetector implemented with 18 passing tests)
**Domain Concepts:** [Match Segments](../../domain/README.md#match-segments), [Running Order](../../domain/README.md#running-order)
**Business Rules:** [100% Running Order Accuracy](../../domain/business_rules.md#rule-4-100-running-order-accuracy-requirement)

**Why This Matters:** This task integrates the RunningOrderDetector into the pipeline and implements transcript-based boundary detection. We'll detect studio introductions via team mentions in the transcript, creating three distinct segments per match: Studio Intro → Highlights → Post-Match Analysis.

---

## Objective

Wire RunningOrderDetector into pipeline with CLI command and implement transcript-based boundary detection to produce complete match segments.

## Prerequisites

- [x] Task 011c-2 complete (RunningOrderDetector with 18/18 tests passing)
- [x] OCR results available
- [x] Transcript available
- [x] Pydantic models (MatchBoundary, RunningOrderResult)

## Estimated Time

1.5-2 hours

---

## Ground Truth Validation Data

**Match intro timestamps** (for boundary detection validation - from visual_patterns.md + manual verification):

| Match | Teams | Intro Start | Notes |
|-------|-------|-------------|-------|
| 1 | Liverpool v Aston Villa | **00:01:01** | NOT 00:00:50 (that's show intro + pundits) |
| 2 | Arsenal v Burnley | **00:14:25** | Transcript: "Thank you very much. Leaders, Arsenal..." |
| 3 | Nottingham Forest v Man Utd | **00:26:27** | Transcript: "OK. It is a year today since Ruben Amaran..." |
| 4 | Fulham v Wolves | **00:41:49** | |
| 5 | Tottenham v Chelsea | **00:52:48** | |
| 6 | Brighton v Leeds | **01:04:54** | |
| 7 | Crystal Palace v Brentford | **01:14:40** | |

**Current detection results** (INCORRECT - 30-50s too late):
- Match 1: 00:00:50 ❌ (should be 00:01:01)
- Match 2: 00:15:00 ❌ (should be 00:14:25, off by 35s)
- Match 3: 00:27:19 ❌ (should be 00:26:27, off by 52s)
- Match 4-7: Similar pattern (30-50s too late)

---

## Three Segments Per Match

### 1. Intro (`match_start` → `highlights_start`)
- **Content:** Host introduces match, formations walkthrough, pre-match analysis
- **Detection:** See "Boundary Detection Algorithm" below
- **Duration:** Variable (5-90 seconds - some matches have very brief intros)

### 2. Highlights (`highlights_start` → `highlights_end`)
- **Content:** Match footage with scoreboards
- **Already detected:**
  - `highlights_start`: First scoreboard appearance (exact via OCR)
  - `highlights_end`: FT graphic timestamp (exact via OCR)

### 3. Post-Match (`highlights_end` → `match_end`)
- **Content:** Interviews, pundit analysis, slow-motion replays
- **Detection:** `match_end` = next match's `match_start` (or episode end for final match)
- **Duration:** Variable (10-600 seconds)

**Key insight:** No gaps between matches! Each match ends exactly when the next one starts.

---

## Boundary Detection Algorithm

### 2-Strategy Approach (Like Running Order Detection)

Similar to how we detect running order with 2 independent strategies (scoreboards + FT graphics), we'll use multiple strategies for boundary detection with cross-validation.

#### Strategy 1: Team Mention Detection (PRIMARY)

**Algorithm:**
1. Search **BACKWARD** from `highlights_start` (first scoreboard)
2. Find **BOTH teams mentioned within 10s of each other**
3. Use the **earlier** mention timestamp as `match_start`

**Why backward search:**
- Avoids "coming up later" mentions from earlier in episode
- Finds the actual intro (always immediately before highlights)
- Current forward search finds wrong mentions 30-50s too late

**Implementation:**
```python
# Iterate segments in reverse from highlights_start
for segment in reversed(segments_before_highlights):
    # Check if both teams mentioned close together
    if both_teams_in_segment or both_teams_in_adjacent_segments(within_10s):
        return earlier_mention_timestamp
```

#### Strategy 2: Venue Detection (VALIDATION)

**Algorithm:**
1. Search **BACKWARD** from `highlights_start`
2. Find venue mention ("at Anfield", "at Turf Moor", etc.)
3. Fuzzy match against fixture venue data
4. Use venue mention timestamp as `match_start`

**Why venue detection:**
- Presenters often say "at [stadium]" or "[stadium name]"
- Independent validation of team mention detection
- Less ambiguous than team names (no "Man United" vs "Manchester United" issues)

**Implementation:**
```python
# Search for venue patterns
patterns = ["at {venue}", "{venue}", "the {venue}"]
for segment in reversed(segments_before_highlights):
    for venue in expected_fixtures[match].venues:
        if fuzzy_match(segment.text, venue):
            return segment.start
```

#### Cross-Validation

- Run **both strategies** independently
- Compare results:
  - **Agreement** (within ±10s): High confidence, use Team Mention result
  - **Disagreement** (>10s apart): Log warning, use Team Mention as primary, flag for review
- Log consensus metadata for future tuning

**Example (Match 2):**
- Team Mention: 865s ("Arsenal" at 866s + "Burnley" at 870s → use 866s)
- Venue: 874s ("at Turf Moor")
- Agreement: NO (9s apart) - but both detect intro region correctly
- Result: Use 866s (Team Mention), log 9s variance

---

## Code Review Findings (2025-11-18)

### Issue 1: Bidirectional Search is Redundant

**Problem:** Current implementation (running_order_detector.py:270-301) does both forward and backward search, but **always uses backward result**. Forward search is never used.

**Decision:** Remove bidirectional search, simplify to pure backward search as documented

**Fix required in next session:**
- Remove forward search logic (lines 275-280 in running_order_detector.py)
- Keep backward search only (lines 282-288)
- Update docstrings to remove "bidirectional" language (lines 176-189, 240-255)

### Issue 2: Match 1 Hardcoded Fallback

**Problem:** Match 1 uses hardcoded `min(50.0, highlights_start - 10.0)` instead of proper detection (lines 257-260 in running_order_detector.py)

**Impact:** Bypasses both team mention AND venue detection for first match

**Decision:** Remove hardcoded logic, use same backward search for **ALL matches** (including Match 1)

**Fix required in next session:**
- Delete `if is_first_match: return min(50.0, ...)` block (lines 257-260)
- Match 1 will now use team mention detection (should find ~61s, not 50s)
- Venue strategy will work for Match 1 too (once implemented)

### Simplified Algorithm (After Fixes)

**Pure Backward Search (applies to ALL 7 matches):**

1. Filter segments before `highlights_start`
2. Iterate **backward** through filtered segments
3. Find where **BOTH teams** mentioned within 10s:
   - Both in same segment → return that segment's timestamp
   - Both in adjacent segments (≤10s apart) → return earlier segment's timestamp
4. Fallback if not found: `max(search_start, highlights_start - 60s)`

**No special cases** - same algorithm for Match 1 through Match 7.

---

## Venue Data Structure

### New Files Required

**1. data/venues/premier_league_2025_26.json**

**2. Update data/fixtures/premier_league_2025_26.json**

Add `venue` field to fixtures:
```json
{
  "date": "2025-11-01",
  "home": "Liverpool",
  "away": "Aston Villa",
  "venue": "Anfield"  // References venues JSON
}
```

**3. VenueMatcher class** (similar to TeamMatcher/FixtureMatcher)

---

## Implementation Steps

### Phase 0: Venue Data Setup (15 mins)

**Goal:** Create venue reference data

**Tasks:**
- [X] Create `data/venues/premier_league_2025_26.json` with all 20 PL stadiums
- [X] Update `data/fixtures/premier_league_2025_26.json` to include `venue` field
- [X] Add `VenueMatcher` class (similar to `TeamMatcher`/`FixtureMatcher`)

**Success criteria:**
- Venue JSON file created with 20 teams
- Fixtures updated with venue references
- VenueMatcher can fuzzy match venue mentions

---

### Phase 2a: Venue Strategy Implementation (COMPLETED ✅)

**Goal:** Implement venue-based boundary detection as primary strategy

**What Was Completed (2025-11-18):**

1. **Venue Strategy Implementation**
   - Backward search from `highlights_start` to find venue mentions
   - Fuzzy matching against `data/venues/premier_league_2025_26.json`
   - Fixture validation to ensure correct venue for each match
   - Search within 20s proximity window to avoid false positives

2. **Sentence Extraction from Transcript Segments**
   - Implemented `_extract_sentences_from_segments()` method
   - Combines transcript segments until sentence-ending punctuation (`.`, `!`, `?`)
   - Handles multi-segment sentences (e.g., "It was six defeats..." + "for champions Liverpool.")
   - 9 unit tests covering edge cases (question marks, transitions, empty segments)

3. **Fuzzy Matching Improvements**
   - Fixed critical bug: Single-letter words (e.g., "a") matching team names with 100% score
   - Now skip words <4 characters to prevent false positives
   - Stadium-only matching (removed alias index to prevent "that lane" → "The Lane" matches)
   - Punctuation stripping in venue matcher to handle transcription errors

4. **Earliest Team Sentence Selection**
   - Search backward through sentences to find ALL team-containing sentences
   - Return EARLIEST (minimum timestamp) within proximity window
   - Avoids picking latest mention (which is closer to highlights)

**Results:**
- **7/7 matches PERFECT** (all within 5s accuracy)
  - Match 1-4, 6: 0.00s difference (exact alignment with ground truth)
  - Match 5: +1.86s (logic correct - selects first team-containing sentence)
  - Match 7: +3.46s (logic correct - selects "Crystal Palace and Brentford" sentence)
- Average difference: 0.76s across all 7 matches
- All tests passing: 31 running order tests + 9 sentence extraction tests ✅

**Code Changes:**
- Branch: `feature/task-012-venue-strategy`
- Files modified:
  - `src/motd/analysis/running_order_detector.py`: Sentence extraction + venue strategy
  - `src/motd/analysis/venue_matcher.py`: Fuzzy matching fixes
  - `tests/unit/analysis/test_sentence_extraction.py`: New file with 9 tests
  - `tests/unit/analysis/test_running_order_detector.py`: Added venue strategy tests
  - `tests/test_venue_matcher.py`: Venue matching validation

**Success Criteria:**
- [x] Venue strategy implemented with backward search ✅
- [x] Sentence extraction from transcript segments ✅
- [x] Fuzzy matching bug fixes (single-letter, alias false positives) ✅
- [x] 7/7 matches within 5s accuracy (PERFECT) ✅
- [x] All unit tests passing ✅

---

### 1. Create CLI Command (30 mins)

**Goal:** Wire RunningOrderDetector into a CLI command

**Steps:**
1. Create `src/motd/__main__.py` or extend existing CLI
2. Add command: `analyze-running-order <episode_id>`
3. Load required data:
   ```python
   ocr_results = load_json(f'data/cache/{episode_id}/ocr_results.json')
   transcript = load_json(f'data/cache/{episode_id}/transcript.json')
   team_names = load_json('data/teams/premier_league_2025_26.json')
   ```
4. Create RunningOrderDetector instance
5. Call `detect_running_order()`
6. Pretty-print results to console

**Success criteria:**
- Command runs without errors
- Prints 7 matches in correct order
- Shows `highlights_start` and `highlights_end` for each match

---

### Phase 2b-1a: Clustering Strategy Implementation (NEW - IN PROGRESS)

**Goal:** Implement temporal density clustering as an independent strategy for match boundary detection. Output BOTH venue and clustering results side-by-side for manual comparison.

**Why Clustering?**
- Provides independent validation of venue strategy (like scoreboards + FT graphics for running order)
- Uses statistical density regardless of linguistic patterns
- Detects "bursts" of team co-mentions in transcript
- Handles cases where venue isn't mentioned explicitly

**Algorithm Concept:**
1. Extract all team mentions from transcript (both teams)
2. Find windows where both teams co-occur (within 20s proximity)
3. Calculate density (mentions per second) for each window
4. Identify densest cluster before `highlights_start`
5. Return EARLIEST mention in that cluster (not center)

**Implementation Tasks:**
- [ ] Write test cases first (`TestClusteringStrategy` class)
  - [ ] `test_extracts_team_mentions_from_transcript()`
  - [ ] `test_finds_co_mention_pairs_within_window()`
  - [ ] `test_identifies_dense_clusters()`
  - [ ] `test_returns_earliest_mention_in_cluster()`
  - [ ] `test_ignores_isolated_preview_mentions()`
  - [ ] `test_clustering_produces_reasonable_timestamps()`

- [ ] Implement helper methods in `RunningOrderDetector`:
  - [ ] `_find_team_mentions()` - Extract timestamps where team mentioned
  - [ ] `_find_co_mention_windows()` - Find temporal co-occurrence windows
  - [ ] `_identify_densest_cluster()` - Select densest cluster before highlights

- [ ] Implement main clustering method:
  - [ ] `_detect_match_start_clustering()` - Return cluster metadata + timestamp

- [ ] Integrate into `detect_match_boundaries()`:
  - [ ] Call clustering strategy alongside venue strategy
  - [ ] Store both results (no selection logic yet)
  - [ ] Keep existing match_start logic unchanged (observation only)

- [ ] Update Pydantic model:
  - [ ] Add `clustering_result` field to `MatchBoundary`

- [ ] Update CLI output for comparison:
  - [ ] Show venue AND clustering results side-by-side
  - [ ] Display difference from ground truth for both
  - [ ] Show agreement/disagreement (seconds difference)
  - [ ] Add summary statistics at end

- [ ] Validation & observation:
  - [ ] Run on Episode 01 (all 7 matches)
  - [ ] Document which matches have agreement (±10s)
  - [ ] Identify failure modes
  - [ ] Experiment with parameters (window size, density threshold)
  - [ ] Decide: proceed with cross-validation or venue-only

**Parameters to Tune:**
```python
CLUSTERING_WINDOW_SECONDS = 20.0   # Both teams within 20s
CLUSTERING_MIN_DENSITY = 0.1       # 0.1 mentions/sec minimum
CLUSTERING_MIN_SIZE = 3            # Minimum 3 co-mentions
```

**Success Criteria:**
- [ ] All clustering tests passing
- [ ] Existing 31 running order tests still passing
- [ ] CLI shows both strategies side-by-side
- [ ] Summary stats show agreement rate
- [ ] Observations documented for decision making

**What We're NOT Doing (Yet):**
- ❌ Selection logic (which strategy to use)
- ❌ Automated cross-validation
- ❌ Confidence scoring based on agreement
- ❌ OCR data integration (transcript-only)
- ❌ Changing match_start values (keep using venue)

---

### Phase 2b: Team Mention Strategy Validation (DEFERRED)

**Status:** DEFERRED - Replaced by Phase 2b-1a (Clustering Strategy)

**Rationale:** Clustering provides better independent validation than improving team mention strategy. Team mention already exists as fallback. Focus on orthogonal signals (venue + clustering) first.

**Updated method in RunningOrderDetector:**
```python
def detect_match_boundaries(self, running_order: RunningOrderResult) -> RunningOrderResult:
    """
    Detect match_start and match_end using 2-strategy approach.

    Strategy 1 (PRIMARY): Team Mention Detection
    - Search BACKWARD from highlights_start
    - Find BOTH teams mentioned within 10s
    - Use earlier mention as match_start

    Strategy 2 (VALIDATION): Venue Detection
    - Search BACKWARD from highlights_start
    - Find venue mention (fuzzy match)
    - Cross-validate with Strategy 1

    Returns:
        Updated RunningOrderResult with complete boundaries
    """
    # Implementation here
```

**Algorithm (Team Mention - Strategy 1):**
1. For each match in running_order.matches:
   - Get `highlights_start` timestamp
   - Filter segments: `segment.start < highlights_start`
   - **Search BACKWARD** through filtered segments
   - Track when BOTH teams mentioned:
     - Both in same segment → return segment.start
     - Both in adjacent segments (≤10s apart) → return earlier segment.start
   - Set `match_start` = that timestamp

2. For each match except the last:
   - Set `match_end` = next_match.match_start

3. For the last match:
   - Set `match_end` = episode duration

**Algorithm (Venue - Strategy 2):**
1. Load venue data for match's fixture
2. Search BACKWARD from `highlights_start`
3. Fuzzy match segment text against venue aliases
4. Return venue mention timestamp

**Cross-Validation:**
- Run both strategies
- Compare results (should agree within ±10s)
- Log any disagreements
- Use Team Mention as primary

**Edge cases:**
- If BOTH teams not found: Use fallback (`highlights_start - 60s`)
- ~~First match special case~~ **REMOVED**: Use same algorithm for all matches (Match 1 will be detected properly now)
- Ensure `match_start` < `highlights_start` (sanity check)

**Success criteria:**
- All 7 matches have `match_start` within ±10s of ground truth
- Team Mention strategy achieves ±5s accuracy
- Venue strategy (if implemented) validates Team Mention
- No gaps or overlaps between matches
- `match_start` < `highlights_start` < `highlights_end` < `match_end` for all matches

---

### 3. Generate JSON Output (15 mins)

**Goal:** Save results to JSON file

**Steps:**
1. Create output directory: `data/output/{episode_id}/`
2. Generate JSON:
   ```python
   output = running_order_result.model_dump_json(indent=2)
   ```
3. Save to: `data/output/{episode_id}/running_order.json`
4. Print success message with file path

**JSON structure:**
```json
{
  "matches": [
    {
      "teams": ["Aston Villa", "Liverpool"],
      "position": 1,
      "match_start": 50.0,
      "highlights_start": 112.0,
      "highlights_end": 607.3,
      "match_end": 911.0,
      "confidence": 0.95,
      "detection_sources": ["scoreboard", "ft_graphic", "transcript"]
    },
    ...
  ],
  "strategy_results": { ... },
  "consensus_confidence": 1.0,
  "disagreements": []
}
```

**Success criteria:**
- JSON file created successfully
- File is valid JSON (can be loaded and parsed)
- Pydantic model can deserialize it

---

### 4. Manual Validation (20 mins)

**Goal:** Verify boundaries align with actual episode content

**Steps:**
1. Run command on motd_2025-26_2025-11-01
2. Open JSON output
3. Sample 3 matches (first, middle, last)
4. For each match:
   - Jump to `match_start` timestamp in video
   - Verify: Is this the studio intro? (host talking about the match)
   - Jump to `highlights_start`
   - Verify: Is this the first scoreboard?
   - Jump to `highlights_end`
   - Verify: Is this the FT graphic?
   - Jump to `match_end`
   - Verify: Does the next match start here?

**Acceptance:**
- Studio intro boundaries: ±30s accuracy acceptable
- Highlights boundaries: Should be exact (we have OCR timestamps)
- Match end boundaries: Should be exact (= next match start)

**Document any issues found**

---

## Known Issues to Address

### match_end Detection (To Investigate)

**Current Implementation:**
```python
# For each match except the last:
match_end = next_match.match_start

# For the last match:
match_end = episode_duration
```

**User Observation:**
- `match_start` detection is working perfectly (venue strategy 7/7 within 5s)
- `match_end` likely has problems with match boundaries

**To Validate:**
- Check for gaps/overlaps between matches
- Verify `match_end = next_match.match_start` assumption is correct
- May need post-match analysis boundary detection if gaps exist
- Document findings and plan fix if needed

**Context for Future Work:**
- This issue should be addressed before Task 012 is marked complete
- May require additional strategy for detecting post-match analysis end
- Could involve detecting when studio analysis ends and next intro begins

---

## Deliverables

1. **CLI command:** `python -m motd analyze-running-order <episode_id>`
2. **Boundary detection method:** `detect_match_boundaries()` in RunningOrderDetector
3. **JSON output:** `data/output/{episode_id}/running_order.json`
4. **Validation notes:** Brief doc confirming ±30s accuracy

---

## Success Criteria

### Phase 0: Venue Data Setup
- [X] `data/venues/premier_league_2025_26.json` created with 20 teams
- [X] `data/fixtures/premier_league_2025_26.json` updated with venue field
- [X] `VenueMatcher` class implemented

### Phase 1: CLI Command (COMPLETED ✅)
- [x] CLI command runs successfully
- [x] 7 matches detected with 100% consensus
- [x] JSON output generated

### Phase 2a: Venue Strategy (COMPLETED ✅)
- [x] Venue strategy implemented with backward search
- [x] Sentence extraction from transcript segments (9 unit tests)
- [x] Fuzzy matching bug fixes (single-letter, alias false positives)
- [x] 7/7 matches within 5s accuracy (PERFECT)
- [x] All unit tests passing (31 + 9 = 40 tests total)

### Phase 2b: Team Mention Strategy (REMAINING)
- [ ] Team Mention strategy: Apply sentence extraction improvements
- [ ] Team Mention strategy: Validate against all 7 matches
- [ ] Compare results with venue strategy (document which performs better)
- [ ] Cross-validation logging between strategies
- [ ] Document variance metrics for tuning

### Phase 3: Validation
- [ ] Match 1: 00:01:01 ±10s (NOT 00:00:50)
- [ ] Match 2: 00:14:25 ±10s
- [ ] Match 3: 00:26:27 ±10s
- [ ] Match 4: 00:41:49 ±10s
- [ ] Match 5: 00:52:48 ±10s
- [ ] Match 6: 01:04:54 ±10s
- [ ] Match 7: 01:14:40 ±10s
- [ ] No gaps or overlaps between matches
- [ ] Pydantic model validation passes

---

## Next Steps (Resume Here)

**Estimated Time Remaining:** 1-1.5 hours

### 1. Validate Team Mention Strategy (30-45 mins)
- Apply sentence extraction approach from venue strategy
- Test against all 7 matches with ground truth
- Compare with venue strategy results
- Document which strategy performs better per match

### 2. Investigate match_end Issues (20-30 mins)
- Validate match boundaries for gaps/overlaps between matches
- Check if `match_end = next_match.match_start` assumption holds
- Document findings and plan fix if needed
- May require post-match analysis boundary detection

### 3. Cross-Validation Logging (15 mins)
- Log when strategies agree/disagree
- Record variance metrics between strategies
- Add confidence scoring based on agreement
- Prepare for future tuning

### 4. Final Phase 3 Validation (20 mins)
- Run full validation against all 7 ground truth timestamps
- Verify no gaps/overlaps between matches
- Validate Pydantic model serialization
- Check all remaining Phase 2b and Phase 3 checkboxes
- Prepare for squash merge to main

**Time Spent So Far:**
- Phase 0: ~15 mins (venue data setup)
- Phase 1: ~30 mins (CLI command)
- Phase 2a: ~2 hours (venue strategy implementation)
- **Total:** ~2.75 hours

**Original Estimate:** 1.5-2 hours (exceeded due to venue strategy thoroughness - but worth it for 7/7 perfect results!)

---

## Notes

- **Transcript search:** Use fuzzy matching for team names (handle "Man United", "Manchester United", etc.)
- **Backward search:** Start from `highlights_start` and search backward through transcript
- **Episode end:** Get from transcript metadata or video duration
- **Interludes:** If encountered, document but defer implementation
- **Extend not replace:** `detect_match_boundaries()` enhances the existing RunningOrderResult

---

## Related Tasks

- [011c-2: Running Order Detector](../011-analysis-pipeline/011c-2-assumption-validation.md) - Implemented Phase 1
- [012: Classifier Integration](README.md) - Parent task

---

## Example Usage

```bash
# Run analysis
python -m motd analyze-running-order motd_2025-26_2025-11-01

# Output:
# Running order detected: 7/7 matches (100% consensus)
#
# Match 1: Liverpool vs Aston Villa
#   Studio Intro:     00:00:50 - 00:01:52 (62s)
#   Highlights:       00:01:52 - 00:10:07 (495s)
#   Post-Match:       00:10:07 - 00:15:11 (304s)
#
# ...
#
# Saved to: data/output/motd_2025-26_2025-11-01/running_order.json
```
