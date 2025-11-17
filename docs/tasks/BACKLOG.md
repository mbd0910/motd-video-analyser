# MOTD Analyser - Task List

This directory contains discrete, actionable tasks for building the MOTD Analyser. Each task is self-contained with clear objectives, steps, and validation checkpoints.

## Task Status Legend
- ✅ Completed
- 🔄 In Progress
- ⏳ Not Started
- ⏭️ Skipped/Optional

## Phase 0: Project Setup (Tasks 001-005) ✅
- ✅ [001-environment-setup](completed/001-environment-setup/) - Set up Python venv and verify ffmpeg
- ✅ [002-create-project-structure](completed/002-create-project-structure/) - Create directory structure
- ✅ [003-install-python-dependencies](completed/003-install-python-dependencies/) - Install all Python packages
- ✅ [004-create-team-and-fixture-data](completed/004-create-team-and-fixture-data/) - Premier League teams, fixtures, and episode manifest JSON
- ✅ [005-create-config-file](completed/005-create-config-file/) - Pipeline configuration YAML

**Estimated Time**: 30-45 minutes

---

## Phase 1: Scene Detection (Tasks 006-008) ✅
- ✅ [006-implement-scene-detector](completed/006-implement-scene-detector/) - PySceneDetect integration
- ✅ [007-implement-frame-extractor](completed/007-implement-frame-extractor/) - Extract key frames
- ✅ [008-scene-detection-testing](completed/008-scene-detection-testing/) - CLI + test on first video (Epic with 3 subtasks)

**Estimated Time**: 2-3 hours

---

## Phase 2: OCR & Team Detection (Task 009 - Epic) ✅
- ✅ [009-ocr-implementation](009-ocr-implementation/) - EasyOCR integration, fixture-aware team matching, CLI, validation
  - ✅ 009a: Visual pattern reconnaissance (31 screenshots, strategic pivot to FT graphics)
  - ✅ 009b: OCR reader implementation with EasyOCR (GPU-accelerated, multi-tiered extraction)
  - ✅ 009c: Team matcher with fuzzy matching (rapidfuzz, 100% accuracy on test cases)
  - ✅ 009d: Fixture matcher for validation (confidence boost, 0 false positives)
  - ✅ 009e: CLI integration (`extract-teams` command with smart filtering)
  - ✅ 009f: Run on test video and validate accuracy
  - ✅ 009g: Validation and tuning (100% accuracy achieved, no tuning required)

**Results**: Episode 01.11: 14/14 teams (100%); Episode 08.11: 10/10 teams (100%); 0 false positives; smart filtering reduces scenes by ~50%

**Estimated Time**: 4-5 hours

---

## Phase 3: Audio Transcription (Task 010 - Epic) ✅
- ✅ [010-transcription](completed/010-transcription/) - Audio extraction, Whisper integration, CLI, validation
  - ✅ 010a: Audio transcription reconnaissance (evaluated faster-whisper models, chose large-v3)
  - ✅ 010b: Audio extractor implementation (ffmpeg integration, WAV extraction)
  - ✅ 010c: Transcription engine with faster-whisper (GPU-accelerated, 5min runtime for 84min video)
  - ✅ 010d: CLI integration (`transcribe` command with caching)
  - ✅ 010e: Run on test video (1773 segments, word-level timestamps)
  - ✅ 010f: Validation (excellent accuracy, duration 5039.3s ≈ 84 minutes)

**Results**: Episode 01.11: 1773 segments transcribed in ~5 minutes (GPU); word-level timestamps; excellent accuracy; full caching implemented

**Estimated Time**: 2-3 hours (+ 5 mins transcription time with faster-whisper)

---

## Phase 4: Analysis & Classification (Task 011 - Epic)
- 🔄 [011-analysis-pipeline](011-analysis-pipeline/) - Segment classifier, match boundaries, airtime, orchestrator
  - ⏳ 011a: Analysis reconnaissance & pattern discovery
  - ⏳ 011b: Segment classifier (multi-signal: OCR + transcript + timing)
  - ⏳ 011c: Match boundary detector (running order via OCR + team mentions)
  - ⏳ 011d: Airtime calculator (sum durations by segment type)
  - ⏳ 011e: Pipeline orchestrator & CLI (`process` command)
  - ⏳ 011f: Execution, validation & FT graphic investigation

**Note**: This is the most complex epic - split into 6 subtasks. Running order accuracy (100%) is critical.

**Estimated Time**: 8-11 hours

---

## Phase 5: Manual Validation Tools (Task 012 - Epic)
- ⏳ [012-validation-tools](012-validation-tools/) - Manual labeling tool, validation comparator

**Note**: This is an epic - split into smaller subtasks before starting.

**Estimated Time**: 2-3 hours

---

## Phase 6: Refinement & Tuning (Task 013)
- ⏳ [013-refinement-tuning](013-refinement-tuning/) - Tune thresholds, improve accuracy, iterate

**Estimated Time**: 2-4 hours

---

## Phase 7: Batch Processing (Task 014 - Epic)
- ⏳ [014-batch-processing](014-batch-processing/) - Batch CLI, process all 10 videos, spot-check

**Note**: This is an epic - split into smaller subtasks before starting.

**Estimated Time**: 1-2 hours (+ 8-12 hours processing)

---

## Phase 8: Documentation (Task 015)
- ⏳ [015-documentation](015-documentation/) - README, aggregate stats, blog posts

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

### After Task 008 (Scene Detection Testing)
**Question**: Is scene detection accurate enough (40-80 scenes for 90-min video)?
- ✅ YES → Continue to Task 009
- ❌ NO → Tune threshold in config.yaml, re-run task 008

### After Task 009 (OCR Implementation)
**Question**: Is team detection >90% accurate?
- ✅ YES → Continue to Task 010
- ❌ NO → Adjust OCR regions in config.yaml, consider PaddleOCR (see [tech-tradeoffs.md](../tech-tradeoffs.md))

### After Task 010 (Transcription)
**Question**: Is transcription accurate and fast enough?
- ✅ YES → Continue to Task 011
- ❌ NO → Already using faster-whisper? Consider smaller model or cloud API

### After Task 011 (Analysis & Classification)
**Question**: Ready for batch processing?
- ✅ YES → Continue to Task 014
- ❌ NO → Back to Task 013 for more tuning

---

## Notes

- **Minimum Viable Pipeline**: Tasks 001-021 give you a working end-to-end system
- **Production Ready**: All tasks 001-029 give you a polished, documented system
- **Extensibility**: After completion, see [roadmap.md](../roadmap.md) for future enhancements

---

## Quick Start

```bash
# View task list
cd /Users/michael/code/motd-video-analyser
open docs/tasks/README.md

# Start next task using task-workflow
# See .claude/commands/task-workflow.md for details
```

## Task File Organization

All tasks are now organized in folders:
- **Completed tasks**: `completed/{number}-{name}/README.md`
- **Active/upcoming tasks**: `{number}-{name}/README.md`
- **Epic subtasks**: `{number}-{name}/{number}{letter}-{subtask-name}.md`

Example: Task 008 (epic) contains:
- `008-scene-detection-testing/README.md` - Epic overview
- `008-scene-detection-testing/008a-create-cli-command.md` - Subtask A
- `008-scene-detection-testing/008b-test-on-video.md` - Subtask B
- `008-scene-detection-testing/008c-validate-and-tune.md` - Subtask C

Good luck! 🚀
