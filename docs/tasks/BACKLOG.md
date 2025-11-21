# MOTD Analyser - Historical Tasks

This directory contains completed tasks from the initial development phases (001-012).

**New work uses GitHub Issues** - see [Issue Workflow](/.claude/commands/issue-workflow.md).

---

## Completed Phases

### Phase 0: Project Setup (Tasks 001-005) ✅
- ✅ [001-environment-setup](completed/001-environment-setup/) - Set up Python venv and verify ffmpeg
- ✅ [002-create-project-structure](completed/002-create-project-structure/) - Create directory structure
- ✅ [003-install-python-dependencies](completed/003-install-python-dependencies/) - Install all Python packages
- ✅ [004-create-team-and-fixture-data](completed/004-create-team-and-fixture-data/) - Premier League teams, fixtures, and episode manifest JSON
- ✅ [005-create-config-file](completed/005-create-config-file/) - Pipeline configuration YAML

### Phase 1: Scene Detection (Tasks 006-008) ✅
- ✅ [006-implement-scene-detector](completed/006-implement-scene-detector/) - PySceneDetect integration
- ✅ [007-implement-frame-extractor](completed/007-implement-frame-extractor/) - Extract key frames
- ✅ [008-scene-detection-testing](completed/008-scene-detection-testing/) - CLI + test on first video (Epic with 3 subtasks)

### Phase 2: OCR & Team Detection (Task 009) ✅
- ✅ [009-ocr-implementation](completed/009-ocr-implementation/) - EasyOCR integration, fixture-aware team matching, CLI, validation

**Results**: Episode 01.11: 14/14 teams (100%); Episode 08.11: 10/10 teams (100%); 0 false positives

### Phase 3: Audio Transcription (Task 010) ✅
- ✅ [010-transcription](completed/010-transcription/) - Audio extraction, Whisper integration, CLI, validation

**Results**: Episode 01.11: 1773 segments transcribed in ~5 minutes (GPU); word-level timestamps; excellent accuracy

### Phase 4: Analysis & Classification (Task 011) ✅
- ✅ [011-analysis-pipeline](completed/011-analysis-pipeline/) - Running order detector implementation

**Results**: Episode 01: 7/7 matches detected (100% accuracy), fixture-aware matching, opponent inference (70% recovery rate)

### Phase 4.5: Match Boundary Detection (Task 012) ✅
- ✅ [012-01: Match Start Detection](completed/012-classifier-integration/012-01-pipeline-integration.md) - Dual-strategy boundary detection
- ✅ [012-02: Match End Detection](completed/012-classifier-integration/012-02-match-end-detection.md) - Interlude handling + table reviews
- ✅ [012-03: Terminal Output Fixes](completed/012-classifier-integration/012-03-output-fixes.md) - Ground truth display, strategy labels, detection events

**Results**:
- Episode 01: 7/7 matches (100% accuracy), ±1.27s avg error
- Episode 02: 5/5 matches detected
- 58/58 running order tests passing + 14 CLI output tests passing

---

## New Work

**All new work uses GitHub Issues** - [View Issues](https://github.com/mbd0910/motd-video-analyser/issues)

To work on an issue:
```bash
/issue-workflow 15              # Plan + execute issue #15
/issue-workflow 15 --plan-only  # Create task file only
/issue-workflow 15 --execute    # Execute existing plan
```

Task files for issues are created in `docs/tasks/issue-{number}/`.
