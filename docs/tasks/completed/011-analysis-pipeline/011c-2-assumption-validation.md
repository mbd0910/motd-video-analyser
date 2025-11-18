# Task 011c-2: Multi-Strategy Validation

## Quick Context

**Parent Task:** [011c-segment-classifier](011c-segment-classifier.md)  
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Running Order](../../domain/README.md#running-order), [FT Graphic](../../domain/README.md#ft-graphic)  
**Business Rules:** [100% Running Order Accuracy](../../domain/business_rules.md#rule-4-100-running-order-accuracy-requirement)

**Why This Matters:** This task validates that our **2-strategy, two-phase detection approach** works with real data before implementing it in code. We test 2 independent strategies for detecting running order, cross-validate them, then defer boundary detection to Phase 2. This evidence-based approach prevents building a classifier based on incorrect assumptions.

**Strategic Pivot:** We've shifted from "sequential scene classification" to "2-strategy detection with cross-validation":
1. **Phase 1 (this task):** Detect running order using 2 independent strategies (scoreboard order, FT graphic order)
2. **Phase 2 (future task):** Use known order to detect match boundaries via targeted transcript/mention analysis
3. **Simplified segments:** Highlights (scoreboard → FT) + Post-Match Analysis (FT → next match). Interview/studio split deferred.

**Prerequisites:** 011c-1 complete with ground truth analysis showing OCR + sequencing + dynamic detection is optimal approach.

---

## Objective

Validate that 2-strategy running order detection works with real episode data, achieving 100% running order accuracy. Implement production code with TDD methodology.

## Prerequisites

- [x] Task 011c-1 complete (ground truth dataset with analysis.md)
- [x] OCR results available: `data/cache/motd_2025-26_2025-11-01/ocr_results.json`
- [x] Transcript available: `data/cache/motd_2025-26_2025-11-01/transcript.json`
- [x] Scenes available: `data/cache/motd_2025-26_2025-11-01/scenes.json`
- [ ] Understanding of [Running Order accuracy requirement](../../domain/business_rules.md#rule-4-100-running-order-accuracy-requirement) (100% required)

## Estimated Time

45 minutes (exploratory validation with quick Python scripts)

## Deliverables

1. **Running order strategy validation** - Test 2 strategies, cross-validate for consensus
2. **Production code** - `RunningOrderDetector` with TDD test suite
3. **Pydantic models** - Type-safe data structures (`MatchBoundary`, `RunningOrderResult`)
4. **2-segment approach validation** - Confirm highlights + post-match is sufficient
5. **Validation report** - Document strategy results, confidence levels, edge cases

---

## Implementation Steps

### 1. Strategy 1: Scoreboard Appearance Order (10 mins)

**Goal:** Validate that first scoreboard appearance per match pair gives correct running order

- [x] Load `ocr_results.json`
- [x] Filter for scenes with `ocr_source: "scoreboard"` (should be ~394 scenes)
- [x] Group by detected team pairs (e.g., Liverpool + Aston Villa)
- [x] For each match pair, find **first appearance timestamp**
- [x] Sort match pairs by first appearance → This is scoreboard-detected running order
- [x] Compare against ground truth (visual_patterns.md):
  ```
  Expected order:
  1. Liverpool vs Aston Villa
  2. Burnley vs Arsenal
  3. Nottingham Forest vs Manchester United
  4. Fulham vs Wolverhampton Wanderers
  5. Tottenham Hotspur vs Chelsea
  6. Brighton & Hove Albion vs Leeds United
  7. Crystal Palace vs Brentford
  ```
- [x] Calculate accuracy: 7/7 matches correct, positions correct
- [x] Document findings
- [x] **Commit:** `test(011c-2): Validate scoreboard appearance order strategy (7/7 matches)` ✅

**Success criteria:** ✅ 7/7 matches detected in correct order

---

### 2. Strategy 2: FT Graphic Appearance Order (5 mins)

**Goal:** Validate that FT graphic order matches running order (100% reliable anchor points)

- [x] Load `ocr_results.json`
- [x] Filter for scenes with `ft_graphic: true` (should be exactly 7)
- [x] Sort by `start_seconds` timestamp
- [x] Extract team pairs from FT graphic scenes
- [x] Compare order against ground truth
- [x] Document findings
- [x] **Commit:** `test(011c-2): Validate FT graphic appearance order strategy (7/7 FT graphics)` ✅

**Success criteria:** ✅ 7/7 FT graphics detected in correct order (with deduplication)

---

### 3-7. TDD Implementation (Production Code)

**Approach:** Implemented RunningOrderDetector with full test suite (18 tests)

- [x] Created Pydantic models (MatchBoundary, RunningOrderResult)
- [x] Wrote comprehensive test suite (TDD methodology)
- [x] Implemented scoreboard strategy (100% accuracy)
- [x] Implemented FT graphic strategy with deduplication (7/7 matches)
- [x] Implemented cross-validation consensus logic
- [x] Removed redundant Strategy 3 (mention clustering) - deferred to Phase 2
- [x] All 18 tests passing ✅

**Commits:**
- [x] `feat(models): Add MatchBoundary and RunningOrderResult Pydantic models` ✅
- [x] `test(011c-2): Add comprehensive TDD tests for RunningOrderDetector` ✅
- [x] `feat(011c-2): Implement RunningOrderDetector with multi-strategy detection` ✅
- [x] `refactor(011c-2): Remove redundant Strategy 3, adopt 2-strategy approach` ✅

**Success criteria:** ✅ Production code with 18/18 tests passing

---

### 8. Create Validation Report (5 mins)

**Goal:** Document production code and validation results

- [x] Create `docs/ground_truth/validation_report_011c-2.md`
- [x] Include:
  - Running order strategy results and consensus
  - 2-segment model validation
  - Recommendations for 011c-3 implementation
  - Edge cases identified
  - Decision: Proceed / Investigate / Pivot
  - Rationale for 2-strategy approach
- [x] **Commit:** `docs(011c-2): Create 2-strategy validation report with Phase 2 deferral` ✅

---

## Success Criteria

- [x] 2 independent running order strategies tested (scoreboard + FT graphic)
- [x] Both strategies agree on running order (7/7 positions, 100% consensus)
- [x] FT graphics detected: 7/7 (100% anchor reliability)
- [x] Boundary signals validated (FT 100%, scoreboard 100%)
- [x] 2-segment model confirmed sufficient for MVP
- [x] Validation report created with clear recommendations
- [x] Decision documented: Proceed to 011c-3 implementation
- [x] Production code with TDD test suite (18/18 tests passing)
- [x] Pydantic models for type safety

---

## Next Steps

**Validation successful - proceeding to next phase:**
→ Proceed to [011c-3: Classifier Implementation](011c-3-classifier-implementation.md)

**Strategic decision made:**
- Removed redundant Strategy 3 (mention clustering)
- Adopted two-phase approach: Phase 1 (running order) → Phase 2 (boundaries)
- Phase 2 will use known order to detect boundaries via targeted transcript analysis

---

## Notes

- **TDD approach adopted** - Validation combined with production code implementation
- **Ground truth comparison critical** - visual_patterns.md is source of truth
- **Document edge cases** - They inform 011c-3 implementation
- **Cross-validation is key** - Multiple strategies catch OCR failures
- **Two-phase approach** - Phase 1 (this task) detects running order; Phase 2 (future) detects boundaries using known order
- **Dependency injection pattern** - RunningOrderDetector takes data, not file paths

---

## Related Tasks

- [011c-1: Ground Truth Dataset Creation](011c-1-ground-truth-dataset.md) - Provided analysis.md insights
- [011c-3: Classifier Implementation](011c-3-classifier-implementation.md) - Next task (integrate RunningOrderDetector)
- [011c: Segment Classifier](011c-segment-classifier.md) - Parent task
