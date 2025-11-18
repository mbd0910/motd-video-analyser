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

## Three Segments Per Match

### 1. Studio Intro (`match_start` → `highlights_start`)
- **Content:** Host introduces match, formations walkthrough, pre-match analysis
- **Detection:** Search transcript **backward** from `highlights_start` for **first mention** of either team
- **Duration:** Typically 30-90 seconds

### 2. Highlights (`highlights_start` → `highlights_end`)
- **Content:** Match footage with scoreboards
- **Already detected:**
  - `highlights_start`: First scoreboard appearance
  - `highlights_end`: FT graphic timestamp

### 3. Post-Match Analysis (`highlights_end` → `match_end`)
- **Content:** Interviews, pundit analysis, slow-motion replays
- **Detection:** `match_end` = next match's `match_start` (or episode end for final match)
- **Duration:** Variable (3-8 minutes typically)

**Key insight:** No gaps between matches! Each match ends exactly when the next one starts.

---

## Implementation Steps

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

### 2. Implement Boundary Detection (45 mins)

**Goal:** Detect `match_start` via transcript, set `match_end` = next match start

**Add method to RunningOrderDetector:**
```python
def detect_match_boundaries(self, running_order: RunningOrderResult) -> RunningOrderResult:
    """
    Detect match_start and match_end using transcript + known running order.

    For each match:
    1. Find match_start: Search transcript backward from highlights_start
       for first mention of either team name
    2. Set match_end: Next match's match_start (or episode end for last match)

    Returns:
        Updated RunningOrderResult with complete boundaries
    """
    # Implementation here
```

**Algorithm:**
1. For each match in running_order.matches:
   - Get `highlights_start` timestamp
   - Search transcript backward from that point
   - Find first segment mentioning either team name (fuzzy match)
   - Set `match_start` = that segment's start time

2. For each match except the last:
   - Set `match_end` = next_match.match_start

3. For the last match:
   - Set `match_end` = episode duration (from transcript or video metadata)

**Edge cases:**
- If no team mention found before `highlights_start`, use `highlights_start - 60s` as fallback
- Ensure `match_start` < `highlights_start` (sanity check)
- Handle interludes (if encountered): Document but don't implement yet

**Success criteria:**
- All 7 matches have `match_start` detected
- All matches have `match_end` set
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

- [ ] CLI command runs successfully
- [ ] 7 matches detected with complete boundaries
- [ ] All `match_start` values detected via transcript
- [ ] All `match_end` values set (= next match start)
- [ ] JSON output generated
- [ ] Manual validation confirms ±30s accuracy
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
