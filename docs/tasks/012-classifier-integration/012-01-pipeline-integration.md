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

```json
{
  "season": "2025-26",
  "competition": "Premier League",
  "venues": [
    {
      "team": "Liverpool",
      "stadium": "Anfield",
      "city": "Liverpool",
      "aliases": ["Anfield", "the Anfield"]
    },
    {
      "team": "Arsenal",
      "stadium": "Emirates Stadium",
      "city": "London",
      "aliases": ["Emirates", "the Emirates", "Emirates Stadium"]
    },
    {
      "team": "Manchester United",
      "stadium": "Old Trafford",
      "city": "Manchester",
      "aliases": ["Old Trafford", "the Theatre of Dreams"]
    },
    {
      "team": "Burnley",
      "stadium": "Turf Moor",
      "city": "Burnley",
      "aliases": ["Turf Moor", "the Turf Moor"]
    }
    // ... all 20 Premier League teams
  ]
}
```

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
- [ ] Create `data/venues/premier_league_2025_26.json` with all 20 PL stadiums
- [ ] Update `data/fixtures/premier_league_2025_26.json` to include `venue` field
- [ ] Add `VenueMatcher` class (similar to `TeamMatcher`/`FixtureMatcher`)

**Success criteria:**
- Venue JSON file created with 20 teams
- Fixtures updated with venue references
- VenueMatcher can fuzzy match venue mentions

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

### 2. Fix Team Mention Detection (45 mins)

**Goal:** Fix current algorithm to search **backward** and find **both teams**

**Current bugs:**
1. Bidirectional search is redundant (forward result never used)
2. Match 1 uses hardcoded 50s instead of detection
3. Finds wrong mentions 30-50s too late for matches 2-7

**Fixes required (see "Code Review Findings" above):**
- Remove bidirectional search → keep pure backward search
- Remove Match 1 hardcoded logic → use same algorithm for all matches
- Simplify to one consistent implementation

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

## Deliverables

1. **CLI command:** `python -m motd analyze-running-order <episode_id>`
2. **Boundary detection method:** `detect_match_boundaries()` in RunningOrderDetector
3. **JSON output:** `data/output/{episode_id}/running_order.json`
4. **Validation notes:** Brief doc confirming ±30s accuracy

---

## Success Criteria

### Phase 0: Venue Data Setup
- [ ] `data/venues/premier_league_2025_26.json` created with 20 teams
- [ ] `data/fixtures/premier_league_2025_26.json` updated with venue field
- [ ] `VenueMatcher` class implemented

### Phase 1: CLI Command (COMPLETED ✅)
- [x] CLI command runs successfully
- [x] 7 matches detected with 100% consensus
- [x] JSON output generated

### Phase 2: Fix Boundary Detection (IN PROGRESS)
- [ ] Team Mention strategy: Search BACKWARD from highlights_start
- [ ] Team Mention strategy: Find BOTH teams within 10s
- [ ] All 7 matches within ±10s of ground truth timestamps
- [ ] Venue strategy implemented (optional for now)
- [ ] Cross-validation logging added

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
