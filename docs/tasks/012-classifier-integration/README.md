# Task 012: Classifier Integration + Match Boundary Detection

## Status: In Progress (012-01 ✅ Complete, 012-02 📋 TODO)

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

2. **[012-02: Match End Detection](012-02-match-end-detection.md)** 📋 TODO (3-4 hours estimated)
   - Handle BBC interlude breaks between matches
   - Implement proper `match_end` boundary detection (not naive `next_match.match_start`)
   - Complete segment timeline with all gaps accounted for
   - Phase 1: Gap analysis (observe the problem first)

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

### 012-02: Match End Detection 📋
- [ ] Interlude detection working (BBC advert breaks identified)
- [ ] `match_end` properly detected (not naive `next_match.match_start`)
- [ ] Complete segment timeline (matches + interludes, no gaps)
- [ ] All boundaries validated (±10s accuracy for match_end)
- [ ] Tests cover interlude edge cases

---

## Estimated Time

**Total:** 9-10 hours (012-01: 6 hours actual, 012-02: 3-4 hours estimated)

**Original estimate:** 1.5-2 hours (significantly exceeded due to dual-strategy validation research in 012-01)

---

## Next Task

To be determined based on project needs
