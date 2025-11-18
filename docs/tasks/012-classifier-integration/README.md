# Task 012: Classifier Integration + Match Boundary Detection

## Status: Ready to Start

**Prerequisites:** Task 011 complete (Running order detector implemented)

---

## Objective

Wire `RunningOrderDetector` into pipeline and implement transcript-based boundary detection to produce complete match segments with three-part structure: Studio Intro → Highlights → Post-Match Analysis.

---

## Sub-Tasks

1. **[012-01-pipeline-integration.md](012-01-pipeline-integration.md)** - Pipeline integration + boundary detection (1.5-2 hours)
   - Create CLI command: `python -m motd analyze-running-order <episode_id>`
   - Implement transcript-based `match_start` detection
   - Set `match_end` = next match's `match_start`
   - Generate JSON output with complete boundaries

---

## Key Deliverable

**Three segments per match:**
- **Studio Intro** (`match_start` → `highlights_start`): Host introduction, formations, preview
- **Highlights** (`highlights_start` → `highlights_end`): Match footage with scoreboards → FT graphic
- **Post-Match** (`highlights_end` → `match_end`): Interviews, analysis (ends when next match starts)

---

## Success Criteria

- [ ] CLI command working: `python -m motd analyze-running-order motd_2025-26_2025-11-01`
- [ ] JSON output with 7 matches, each with complete boundaries
- [ ] `match_start` detected via transcript (first team mention)
- [ ] `match_end` = next match's `match_start` (no gaps)
- [ ] Manual validation: ±30s accuracy for studio intro boundaries
- [ ] All boundaries sequential (no overlaps)

---

## Estimated Time

1.5-2 hours

---

## Next Task

To be determined based on project needs
