# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

**Core pipeline operational** (scene detection, OCR, transcription). **Working on** Task 012: Pipeline Integration + Match Boundary Detection. Task 011 (Running Order Detection) complete with 100% accuracy. Follow task-driven workflow in [docs/tasks/](docs/tasks/).

## What This Project Does

**MOTD Analyser** - Automated video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Analyses running order, airtime distribution, and post-match analysis patterns from MOTD episodes (2025/26 season).

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## Critical Warnings

**IMPORTANT**: This project uses task-driven development. Before implementing any feature:
1. Check if a task file exists in [docs/tasks/](docs/tasks/) or [docs/tasks/completed/](docs/tasks/completed/)
2. Check [docs/tasks/future/](docs/tasks/future/) for tentative tasks (YAGNI principle - only create when needed)
3. Never skip task validation checklists

**YOU MUST**:
- Always check video resolution with `ffprobe` before assuming 1920x1080 - BBC may change formats
- Activate virtual environment (`source venv/bin/activate`) before running any Python commands
- Check for cached results in `data/cache/{episode_id}/` before re-running expensive operations

**NEVER**:
- Run `openai-whisper` instead of `faster-whisper` (4x slower, wastes 6-12 mins per video)
- Skip caching checks - Whisper transcription costs 3-4 minutes per video
- Commit files in `data/videos/` or `data/cache/` - they're gitignored for size reasons
- Use Tesseract for OCR (poor on sports graphics) - use EasyOCR
- Create deeply nested task structures (011a→011b-1→011b-2) - use sequential numbering (011-01, 011-02) instead
- Assume 1920x1080 resolution without verification

## Repository Workflow

* Before starting a task or set of tasks, create a feature branch.
* git commit frequently when working on a task. Follow commit message format in [COMMIT_STYLE.md](COMMIT_STYLE.md).
* Always use squash merge when merging a feature branch into main.
* Always pause to ask the user before squash merging. Never assume the user wants Claude to squash merge before asking.

## Code Quality Guidelines

**Follow these guidelines when writing code:**

- [Python Style & Conventions](.claude/commands/references/python_guidelines.md)
- [Architecture & Design Patterns](.claude/commands/references/python_architecture_patterns.md)
- [ML/Pipeline Patterns](.claude/commands/references/ml_pipeline_patterns.md) **(CRITICAL - caching, GPU, etc.)**
- [Testing Guidelines](.claude/commands/references/testing_guidelines.md)
- [Code Quality Checklist](.claude/commands/references/code_quality_checklist.md)

## Domain Knowledge & Business Context

**Domain Documentation Hub** - [docs/domain/](docs/domain/)

Before implementing features, check the domain docs for business context:
- **[Domain Glossary](docs/domain/README.md)** - Terminology (FT Graphics, Running Order, Episode Manifest, Segment Types, etc.)
- **[Business Rules](docs/domain/business_rules.md)** - Validation logic, accuracy requirements, processing rules
- **[Visual Patterns](docs/domain/visual_patterns.md)** - Episode structure, timing patterns, ground truth data

**Why:** Sub-tasks reference these instead of duplicating context. Business logic documented alongside code.

**When writing sub-tasks:** Use [Sub-Task Template](.claude/commands/references/subtask_template.md) - includes Quick Context section linking to domain docs.

## Task-Driven Development Workflow

### Critical Pattern: Follow Tasks Sequentially

1. **Start here**: [docs/tasks/README.md](docs/tasks/README.md) - Overview of all 15 tasks
2. **Begin with**: [docs/tasks/001-environment-setup.md](docs/tasks/001-environment-setup.md)
3. **Work sequentially**: Tasks build on each other (001 → 002 → 003...)
4. **Validate at checkpoints**: Each task has a validation checklist - don't skip it
5. **Reference roadmap for code**: [docs/roadmap.md](docs/roadmap.md) contains detailed implementation examples

### Epic Tasks Require Splitting (Critical!)

**Tasks 008-015 are "epics"** - they combine multiple sub-tasks. Before implementing an epic:
- Read the epic file
- Split it into smaller, discrete tasks
- Implement incrementally
- Validate each sub-task

**Example**: Task 009 (OCR Implementation Epic) should be split into:
1. Implement OCR reader module
2. Implement team matcher
3. Create CLI command
4. Run on test video
5. Validate accuracy

Don't try to complete an epic in one session - split first, then execute.

## Technology Constraints (Critical)

### Use These Libraries (Not Alternatives)
- **Scene Detection**: PySceneDetect (ContentDetector) - *not raw OpenCV*
- **OCR**: EasyOCR (GPU-accelerated) - *not Tesseract* (poor on sports graphics)
- **Transcription**: **faster-whisper** - ***NOT* openai-whisper** (4x slower!)
- **Video Processing**: ffmpeg + opencv-python
- **Config**: PyYAML
- **Python**: 3.12.7

**Why faster-whisper is critical**: Standard openai-whisper takes 10-15 minutes per 90-minute video. faster-whisper does it in 3-4 minutes with identical accuracy. See [docs/tech-tradeoffs.md](docs/tech-tradeoffs.md) for benchmarks.

### If You Need to Pivot
See [docs/tech-tradeoffs.md](docs/tech-tradeoffs.md) for alternatives:
- EasyOCR too slow? → PaddleOCR (migration guide included)
- faster-whisper has issues? → Whisper API (cloud, costs $5-10 for 10 videos)
- Scene detection missing transitions? → Adjust threshold or try AdaptiveDetector

## Common Commands

```bash
# REQUIRED: Activate Python virtual environment before all Python commands
source venv/bin/activate

# Check video file properties (resolution, duration, codec)
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,codec_name -of default=noprint_wrappers=1 video.mp4

# Verify GPU availability for EasyOCR/faster-whisper
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Run tests for specific module
pytest tests/test_scene_detection.py -v

# Check cache status for episode
ls -lh data/cache/{episode_id}/

# Validate JSON output files
python -m json.tool data/output/analysis.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check if cache exists before running expensive operation
[ -f data/cache/{episode_id}/transcript.json ] && echo "Cache exists" || echo "Need to run transcription"
```

## British English Conventions

Use British spelling throughout codebase and docs:
- **Code & docs**: analyser (not analyzer), colour (not color), optimise (not optimize), visualisation (not visualization), recognise (not recognize)
- **Package name**: `motd` (not `motd-analyser` - avoid redundancy with repository name)
- **Comments**: "colour space" not "color space", "optimised for GPU" not "optimized for GPU"

## Configuration & Environment

### Premier League Teams - 2025/26 Season
File: [data/teams/premier_league_2025_26.json](data/teams/premier_league_2025_26.json) - Contains 20 teams with promoted: Burnley, Leeds United, Sunderland

### Video Resolution
**Always verify** with ffprobe before processing - do not assume 1920x1080. Adjust OCR regions in config if resolution differs.

### Caching Strategy
**CRITICAL**: Never re-run Whisper unnecessarily - it's the slowest stage (3-4 minutes per video). Always check `data/cache/{episode_id}/transcript.json` exists before transcribing. See [ML/Pipeline Patterns](.claude/commands/references/ml_pipeline_patterns.md) for caching implementation.

### Validation
Each task has validation checklists - see individual task files in [docs/tasks/](docs/tasks/) for success criteria.

## Where to Find Information

- **"What does X mean?"** → [docs/domain/README.md](docs/domain/README.md) (domain glossary - FT graphics, running order, etc.)
- **"What are the business rules?"** → [docs/domain/business_rules.md](docs/domain/business_rules.md) (validation logic, accuracy requirements)
- **"How long do segments last?"** → [docs/domain/visual_patterns.md](docs/domain/visual_patterns.md) (episode structure, timings)
- **"How do I implement X?"** → [docs/roadmap.md](docs/roadmap.md) (detailed code examples)
- **"Why this library?"** → [docs/tech-tradeoffs.md](docs/tech-tradeoffs.md) (comparisons + alternatives)
- **"What's next?"** → [docs/tasks/README.md](docs/tasks/README.md) (task list + status)
- **"What should the output look like?"** → [docs/prd.md](docs/prd.md) section 3.4 (JSON schema)
- **"What's the big picture?"** → [docs/architecture.md](docs/architecture.md) (system design + CLI specs)
- **"How do I start?"** → [docs/tasks/001-environment-setup.md](docs/tasks/001-environment-setup.md) (first task)

---

**Remember**: This is a marathon, not a sprint. The planning is done. Now execute methodically, one task at a time, with validation at every step.

Up the Addicks! ⚽🔴⚪
