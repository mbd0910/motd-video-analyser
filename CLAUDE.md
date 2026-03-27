# CLAUDE.md

## What This Project Does

**MOTD Analyser** - Video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Uses LLM-based analysis to identify running order, segment boundaries, and airtime distribution from MOTD episodes (2025/26 season).

**Workflow:** Run automated pipeline → Generate LLM prompt → Claude analysis → Save structured JSON

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## How Analysis Works

**The analysis is LLM-based, not rule-based.** Scene detection, OCR, and transcription are preprocessing stages that produce advisory hints. Claude performs the actual segment analysis via `python -m motd generate-llm-prompt`.

Don't try to improve accuracy by tweaking OCR rules - the LLM interprets imperfect hints.

## Architecture Overview

**4-stage pipeline:** Video → Scenes → OCR/Teams → Transcription → LLM Prompt

**Modules** (`src/motd/`):
- `scene_detection/` - **Find segment boundaries** (PySceneDetect, OpenCV)
- `ocr/` - **Read team names from graphics** (EasyOCR, rapidfuzz)
- `transcription/` - **Convert speech to text** (ffmpeg, faster-whisper)
- `llm/` - **Prepare prompt for Claude** (OCR hints + transcript)
- `pipeline/` - Orchestrator, service factory, Pydantic models

**Key deps:** PySceneDetect, EasyOCR, faster-whisper, Pydantic v2

## Project Structure

- `src/motd/` - Main package (pipeline, OCR, transcription, scene detection) - see `src/motd/CLAUDE.md`
- `config/` - Configuration files (config.yaml)
- `data/` - Videos, cache, analysis outputs (gitignored) - see `data/CLAUDE.md`
- `docs/` - Documentation and domain knowledge
- `tests/` - Test suite

## Critical Warnings

- Activate virtual environment (`source venv/bin/activate`) before running Python commands
- Check `data/cache/{episode_id}/` before re-running expensive operations (transcription takes 15-20 mins)
- Never commit files in `data/videos/` or `data/cache/`

## Code Style

- **Line length**: 100 characters
- **Spelling**: British English (analyser, colour, optimise)

## Domain Knowledge

See [docs/domain/](docs/domain/) for business context:
- [Glossary](docs/domain/README.md) - FT Graphics, Running Order, Segment Types
- [Business Rules](docs/domain/business_rules.md) - Validation logic
- [Visual Patterns](docs/domain/visual_patterns.md) - Episode structure, timings

## Common Commands

```bash
source venv/bin/activate
```

**Full pipeline:**
- `python -m motd run VIDEO_PATH [--force] [--config PATH]`

**Individual stages:**
- `python -m motd detect-scenes VIDEO_PATH [--threshold N] [--min-scene-duration N] [--output PATH]`
- `python -m motd extract-teams --scenes PATH --episode-id ID [--output PATH]`
- `python -m motd transcribe VIDEO_PATH [--model-size SIZE] [--force] [--output PATH]`

**Generate LLM prompt:**
- `python -m motd generate-llm-prompt EPISODE_ID [--force] [--no-hints] [--output PATH]`

**Tests:**
- `pytest`

Use `--help` on any command for full options.
