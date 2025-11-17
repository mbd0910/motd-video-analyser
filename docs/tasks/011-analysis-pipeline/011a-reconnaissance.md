# Task 011a: Analysis Reconnaissance & Pattern Discovery

## Objective
Map data relationships between scenes, OCR, and transcription to discover classification patterns for segment types. Validate against ground truth from manual documentation.

## Prerequisites
- [x] Task 010 complete (transcription data available)
- [x] Have cached: scenes.json, ocr_results.json, transcript.json
- [x] Ground truth documentation: docs/motd_visual_patterns.md

## Estimated Time
45-60 minutes

## Implementation Steps

### 1. Load All Cached Data
- [ ] Load `data/cache/motd_2025-26_2025-11-01/scenes.json`
- [ ] Load `data/cache/motd_2025-26_2025-11-01/ocr_results.json`
- [ ] Load `data/cache/motd_2025-26_2025-11-01/transcript.json`
- [ ] Load ground truth from `docs/motd_visual_patterns.md` (lines 95-102: running order)

### 2. Map Data Relationships
- [ ] Cross-reference scenes with OCR detections
  - Which scenes have scoreboard graphics?
  - Which scenes have FT (Full Time) graphics?
  - Which scenes have team formations?
- [ ] Cross-reference scenes with transcript segments
  - Which scenes overlap with speech?
  - Which transcript segments contain team names?
  - Which transcript segments contain transition words ("Alright", "Right", "Moving on")?
- [ ] Map scene sequences
  - What comes before/after FT graphics?
  - What comes before/after team mentions?
  - Duration patterns by segment type

### 3. Pattern Discovery for Each Segment Type

#### Highlights Pattern
- [ ] Identify all scenes with scoreboard OCR
- [ ] Identify all scenes with FT graphic OCR
- [ ] Duration ranges for highlights segments
- [ ] Typical sequence: Formation → Scoreboards → FT graphic

#### Interview Pattern
- [ ] Identify scenes following FT graphics
- [ ] Check for interview keywords in transcript ("speak to", "join us", "after the game")
- [ ] Check for name graphics in OCR (player/manager names)
- [ ] Duration ranges for interview segments

#### Studio Intro Pattern
- [ ] Identify short scenes (7-11 seconds) at match starts
- [ ] Check for team mentions in transcript
- [ ] Verify they occur before highlights (with formation graphics)
- [ ] Transition from previous match analysis

#### Studio Analysis Pattern
- [ ] Identify scenes after interviews
- [ ] Check for transition words in transcript
- [ ] Check for team discussion keywords
- [ ] Duration ranges for analysis segments

### 4. Validate Against Ground Truth
- [ ] Compare discovered match boundaries with motd_visual_patterns.md
- [ ] Verify 7 matches detected in correct order:
  1. Liverpool v Aston Villa (00:00:50)
  2. Burnley v Arsenal (00:14:25)
  3. Forest vs Manchester United (00:26:27)
  4. Fulham v Wolves (00:41:49)
  5. Spurs v Chelsea (00:52:48)
  6. Brighton v Leeds (1:04:54)
  7. Palace v Brentford (1:14:40)
- [ ] Check if all 7 FT graphics were detected by OCR
- [ ] Document any missing FT graphics and why

### 5. Document Edge Cases
- [ ] MOTD 2 interlude (52:01-52:47) - how to detect/skip?
- [ ] Intro sequence (00:00:00-00:00:50) - already filtered?
- [ ] Outro sequence (1:22:57+) - how to detect?
- [ ] VAR reviews during highlights - correctly part of highlights?
- [ ] Formation graphics - whole screen vs bottom screen differences
- [ ] Missing OCR detections - which scenes/teams?

### 6. Propose Classification Heuristics
- [ ] Document priority-ordered rules for segment classification:
  ```
  Rule 1: FT graphic in OCR → End of highlights (next = interviews)
  Rule 2: Scoreboard OCR + no FT → Highlights
  Rule 3: After highlights + before studio transition → Interviews
  Rule 4: Short scene + team mention + before highlights → Studio Intro
  Rule 5: After interviews + transition keywords → Studio Analysis
  Rule 6: Default → Studio (generic/unclassified)
  ```
- [ ] Document confidence scoring approach
- [ ] Identify which signals are most reliable

## Deliverables

### Reconnaissance Report
Create `docs/analysis_reconnaissance_report.md` with:
- Data summary (counts, coverage)
- Pattern analysis for each segment type
- Validation against ground truth
- Edge cases documented
- Proposed classification rules with rationale
- Recommendations for 011b implementation

### Key Questions to Answer
1. **Are all 7 FT graphics detected by OCR?** If not, why?
2. **How reliable are transition words for match boundaries?**
3. **Can we confidently distinguish studio intro from studio analysis?**
4. **What % of scenes have OCR detections?** (highlights coverage)
5. **What % of scenes have overlapping transcript?** (speech coverage)
6. **Are there any unexpected segment types?** (e.g., league table reviews, montages)

## Success Criteria
- [ ] All cached data loaded and understood
- [ ] Data relationships mapped (OCR ↔ scenes ↔ transcript)
- [ ] Patterns documented for all 4 segment types
- [ ] Ground truth validation complete (7/7 matches identified)
- [ ] FT graphic detection assessed (documented any missing)
- [ ] Classification rules proposed with confidence
- [ ] Reconnaissance report written
- [ ] Ready to implement 011b (segment classifier)

## Notes
- Focus on **discovery**, not implementation
- Document **why** certain patterns work, not just what they are
- Be thorough but don't over-analyze - aim for 80/20 insights
- This reconnaissance will directly inform 011b heuristic rules
- Manual validation by user will happen in 011f, so don't need perfect accuracy yet

## Next Task
[011b-segment-classifier.md](011b-segment-classifier.md)
