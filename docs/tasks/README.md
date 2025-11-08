# MOTD Analyser - Task List

This directory contains discrete, actionable tasks for building the MOTD Analyser. Each task is self-contained with clear objectives, steps, and validation checkpoints.

## Task Status Legend
- ✅ Completed
- 🔄 In Progress
- ⏳ Not Started
- ⏭️ Skipped/Optional

## Phase 0: Project Setup (Tasks 001-005)
- ✅ [001-environment-setup.md](001-environment-setup.md) - Set up Python venv and verify ffmpeg
- ✅ [002-create-project-structure.md](002-create-project-structure.md) - Create directory structure
- ✅ [003-install-python-dependencies.md](003-install-python-dependencies.md) - Install all Python packages
- ✅ [004-create-team-and-fixture-data.md](004-create-team-and-fixture-data.md) - Premier League teams, fixtures, and episode manifest JSON
- ⏳ [005-create-config-file.md](005-create-config-file.md) - Pipeline configuration YAML

**Estimated Time**: 30-45 minutes

---

## Phase 1: Scene Detection (Tasks 006-008)
- ⏳ [006-implement-scene-detector.md](006-implement-scene-detector.md) - PySceneDetect integration
- ⏳ [007-implement-frame-extractor.md](007-implement-frame-extractor.md) - Extract key frames
- ⏳ [008-scene-detection-testing.md](008-scene-detection-testing.md) - CLI + test on first video (Epic)

**Estimated Time**: 2-3 hours

---

## Phase 2: OCR & Team Detection (Task 009 - Epic)
- ⏳ [009-ocr-implementation-epic.md](009-ocr-implementation-epic.md) - EasyOCR integration, fixture-aware team matching, CLI, validation

**Note**: This is an epic - consider splitting into smaller tasks before starting. Fixture-aware matching improves accuracy from ~85-90% to 95%+.

**Estimated Time**: 4-5 hours

---

## Phase 3: Audio Transcription (Task 010 - Epic)
- ⏳ [010-transcription-epic.md](010-transcription-epic.md) - Audio extraction, Whisper integration, CLI, validation

**Note**: This is an epic - consider splitting into smaller tasks before starting.

**Estimated Time**: 2-3 hours (+ 10-15 mins transcription time)

---

## Phase 4: Analysis & Classification (Task 011 - Epic)
- ⏳ [011-analysis-pipeline-epic.md](011-analysis-pipeline-epic.md) - Segment classifier, team mentions, airtime calculator, orchestrator

**Note**: This is the most complex epic - definitely split into smaller tasks before starting.

**Estimated Time**: 4-6 hours

---

## Phase 5: Manual Validation Tools (Task 012 - Epic)
- ⏳ [012-validation-tools-epic.md](012-validation-tools-epic.md) - Manual labeling tool, validation comparator

**Note**: This is an epic - consider splitting into smaller tasks before starting.

**Estimated Time**: 2-3 hours

---

## Phase 6: Refinement & Tuning (Task 013)
- ⏳ [013-refinement-tuning.md](013-refinement-tuning.md) - Tune thresholds, improve accuracy, iterate

**Estimated Time**: 2-4 hours

---

## Phase 7: Batch Processing (Task 014 - Epic)
- ⏳ [014-batch-processing-epic.md](014-batch-processing-epic.md) - Batch CLI, process all 10 videos, spot-check

**Note**: This is an epic - consider splitting into smaller tasks before starting.

**Estimated Time**: 1-2 hours (+ 8-12 hours processing)

---

## Phase 8: Documentation (Task 015)
- ⏳ [015-documentation-blog-prep.md](015-documentation-blog-prep.md) - README, aggregate stats, blog posts

**Estimated Time**: 3-5 hours

---

## Total Estimated Time
- **Active Work**: 19-28 hours
- **Processing Time**: 8-12 hours (overnight batch)
- **Calendar Time**: 2-3 weeks (2-3 hours/day)

---

## How to Use This Task List

1. **Work sequentially**: Tasks build on each other
2. **Check off as you go**: Update the status emoji in this README
3. **Validate at each checkpoint**: Don't skip validation steps
4. **Adjust estimates**: Your actual time may vary

## Decision Points

### After Task 009 (Scene Detection)
**Question**: Is scene detection accurate enough (40-80 scenes for 90-min video)?
- ✅ YES → Continue to Task 010
- ❌ NO → Tune threshold in config.yaml, re-run task 009

### After Task 013 (OCR)
**Question**: Is team detection >90% accurate?
- ✅ YES → Continue to Task 014
- ❌ NO → Adjust OCR regions in config.yaml, consider PaddleOCR (see [tech-tradeoffs.md](../tech-tradeoffs.md))

### After Task 016 (Transcription)
**Question**: Is transcription accurate and fast enough?
- ✅ YES → Continue to Task 017
- ❌ NO → Already using faster-whisper? Consider smaller model or cloud API

### After Task 021 (Full Pipeline)
**Question**: Ready for batch processing?
- ✅ YES → Continue to Task 026
- ❌ NO → Back to Task 024 for more tuning

---

## Notes

- **Minimum Viable Pipeline**: Tasks 001-021 give you a working end-to-end system
- **Production Ready**: All tasks 001-029 give you a polished, documented system
- **Extensibility**: After completion, see [roadmap.md](../roadmap.md) for future enhancements

---

## Quick Start

```bash
# Start with Phase 0
cd /Users/michael/code/motd-video-analyser
open docs/tasks/001-environment-setup.md
```

Good luck! 🚀
