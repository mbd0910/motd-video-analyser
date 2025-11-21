# Task 012: Classifier Integration + Match Boundary Detection

## Status: ✅ COMPLETE (012-01, 012-02, 012-03 all complete)

**Prerequisites:** Task 011 complete (Running order detector implemented)

---

## Objective

Wire `RunningOrderDetector` into pipeline and implement transcript-based boundary detection to produce complete match segments with three-part structure: Studio Intro → Highlights → Post-Match Analysis.

---

## Sub-Tasks

1. **[012-01: Match Start Detection](012-01-pipeline-integration.md)** ✅ COMPLETE (6 hours)
   - Dual-strategy boundary detection (venue + clustering)
   - Algorithm tuning and cross-validation
   - CLI command: `python -m motd analyze-running-order <episode_id>`
   - 7/7 matches detected, 100% agreement, ±1.27s average accuracy
   - 46/46 tests passing

2. **[012-02: Match End Detection](012-02-match-end-detection.md)** ✅ COMPLETE (7.75 hours actual)
   - Handle BBC interlude breaks between matches (MOTD 2 segments)
   - Handle table reviews after last match (Premier League standings)
   - Implement proper `match_end` boundary detection via dual-signal approach (keyword + team mention validation)
   - Episode 01: 7/7 matches correct (100% accuracy)
   - 57/57 tests passing, frame extraction bug fixed

3. **[012-03: Terminal Output Fixes](012-03-output-fixes.md)** ✅ COMPLETE (2 hours actual)
   - Fix ground truth display bug (Episode 01-specific only)
   - Fix contradictory boundary strategy labels
   - Add detection events section for debugging
   - Fix Episode 02 interlude detection (West Ham United "United" alternate false positive)

---

## Key Deliverable

**Three segments per match:**
- **Studio Intro** (`match_start` → `highlights_start`): Host introduction, formations, preview
- **Highlights** (`highlights_start` → `highlights_end`): Match footage with scoreboards → FT graphic
- **Post-Match** (`highlights_end` → `match_end`): Interviews, analysis (ends when next match starts)

---

## Success Criteria

### 012-01: Match Start Detection ✅
- [x] CLI command working: `python -m motd analyze-running-order motd_2025-26_2025-11-01`
- [x] JSON output with 7 matches
- [x] `match_start` detected via dual-strategy validation (venue + clustering)
- [x] Manual validation: All 7 matches within ±5s accuracy
- [x] 100% agreement between strategies
- [x] 46/46 tests passing

### 012-02: Match End Detection ✅
- [x] Interlude detection working (MOTD 2 segments identified via keyword + validation)
- [x] Table review detection working (league standings after last match)
- [x] `match_end` properly detected via dual-signal approach (keyword + team mentions)
- [x] Episode 01: 7/7 matches correct (100% accuracy)
- [x] 57/57 tests passing (52 existing + 5 new)
- [x] Frame extraction bug fixed (skip logic removed, 100% coverage)

### 012-03: Terminal Output Fixes ✅
- [x] Ground truth display fixed (Episode 01-specific only, not shown for Episode 02)
- [x] Boundary strategy labels fixed (show actual strategy used: venue/clustering/team mention)
- [x] Detection events section added (show FT graphics, scoreboards)
- [x] Episode 02 interlude detection fixed ("United" alternate false positive)
- [x] 14 CLI output tests + 1 interlude test passing (15 new tests total)
- [x] Episode 02 output validated (no ground truth, correct strategy labels, interlude at 2640.28s)
- [x] Import fixes applied (from src.motd → from motd)
- [x] Pre-existing test failures documented (8 FT detection tests - out of scope)

---

## Estimated Time

**Total:** 15.75 hours
- 012-01: 6 hours actual (match start detection)
- 012-02: 7.75 hours actual (match end detection + interlude/table handling + frame extraction bug fix)
- 012-03: 2 hours actual (terminal output fixes + Episode 02 interlude detection)

**Original estimate:** 1.5-2 hours (significantly exceeded due to dual-strategy validation research + comprehensive edge case handling)

---

## Next Task

To be determined based on project needs
