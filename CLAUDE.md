# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status: Planning Phase Complete ✅ | Implementation Not Started 🚧

**This repository contains comprehensive planning documentation but zero implementation code.** All references to commands, modules, and architecture describe *planned* work, not existing functionality.

Your job: **Follow the task-driven workflow to implement the system.**

## What This Project Does

**MOTD Analyser** - Automated video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Analyses running order, airtime distribution, and post-match analysis patterns from MOTD episodes (2025/26 season).

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## General Instructions for Claude Code

* Before starting a task or set of tasks, create a feature branch.
* git commit frequently when working on a task. Follow commit message format in `COMMIT_STYLE.md`.
* Always use squash merge when merging a feature branch into main.
* Always pause to ask the user before squash merging. Never assume the user wants Claude to squash merge before asking.

## Task-Driven Development Workflow

### Critical Pattern: Follow Tasks Sequentially

1. **Start here**: `docs/tasks/README.md` - Overview of all 15 tasks
2. **Begin with**: `docs/tasks/001-environment-setup.md`
3. **Work sequentially**: Tasks build on each other (001 → 002 → 003...)
4. **Validate at checkpoints**: Each task has a validation checklist - don't skip it
5. **Reference roadmap for code**: `docs/roadmap.md` contains detailed implementation examples

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

### Phase Overview

- **Phase 0** (Tasks 001-005): Project setup, dependencies, team data, config → *30-45 mins*
- **Phase 1** (Tasks 006-008): Scene detection → *2-3 hours*
- **Phase 2** (Task 009 - Epic): OCR & team matching → *3-4 hours*
- **Phase 3** (Task 010 - Epic): Audio transcription → *2-3 hours*
- **Phase 4** (Task 011 - Epic): Analysis pipeline → *4-6 hours*
- **Phase 5** (Task 012 - Epic): Validation tools → *2-3 hours*
- **Phase 6** (Task 013): Tuning & refinement → *2-4 hours*
- **Phase 7** (Task 014 - Epic): Batch processing → *1-2 hours + 8-12 hours processing*
- **Phase 8** (Task 015): Documentation & blog prep → *3-5 hours*

**Total active work**: 19-28 hours

## Planned Architecture (Not Yet Implemented)

### Pipeline Stages (Sequential)
1. **Scene Detection** → Detects transitions between studio/highlights/interviews
2. **OCR Processing** → Extracts team names from scoreboard graphics
3. **Audio Transcription** → Transcribes commentary to detect first team mentioned
4. **Analysis & Classification** → Classifies segments, calculates airtime
5. **Validation** → Manual override capability

### Design Principles
- **Caching First**: Never re-run expensive operations (Whisper = 10-15 mins per video)
- **Fail Gracefully**: One match failing shouldn't block entire episode
- **Validation Before Automation**: Build manual correction tools first
- **Modularity**: Each stage has clear JSON input/output contracts

### Planned Directory Structure
```
motd-analyzer/
├── src/motd_analyzer/          # Python package (create in Phase 0)
│   ├── scene_detection/        # PySceneDetect integration
│   ├── ocr/                    # EasyOCR + team matching
│   ├── transcription/          # faster-whisper integration
│   ├── analysis/               # Segment classification
│   ├── validation/             # Manual labeling tools
│   └── pipeline/               # Orchestration + caching
│
├── data/
│   ├── teams/                  # Premier League team names JSON
│   ├── videos/                 # Input MP4s (gitignored)
│   ├── cache/                  # Intermediate results (gitignored)
│   └── output/                 # Final JSON analysis
│
├── config/
│   └── config.yaml             # Pipeline parameters
│
└── docs/                       # ← You are here
    ├── prd.md                  # Product requirements
    ├── architecture.md         # Technical design (detailed)
    ├── tech-tradeoffs.md       # Library comparisons
    ├── roadmap.md              # Implementation guide with code examples
    └── tasks/                  # Step-by-step breakdown
```

## Technology Decisions (Critical)

### Use These Libraries (Not Alternatives)
- **Scene Detection**: PySceneDetect (ContentDetector) - *not raw OpenCV*
- **OCR**: EasyOCR (GPU-accelerated) - *not Tesseract* (poor on sports graphics)
- **Transcription**: **faster-whisper** - ***NOT* openai-whisper** (4x slower!)
- **Video Processing**: ffmpeg + opencv-python
- **Config**: PyYAML
- **Python**: 3.12.7

**Why faster-whisper is critical**: Standard openai-whisper takes 10-15 minutes per 90-minute video. faster-whisper does it in 3-4 minutes with identical accuracy. See `docs/tech-tradeoffs.md` for benchmarks.

### If You Need to Pivot
See `docs/tech-tradeoffs.md` for alternatives:
- EasyOCR too slow? → PaddleOCR (migration guide included)
- faster-whisper has issues? → Whisper API (cloud, costs $5-10 for 10 videos)
- Scene detection missing transitions? → Adjust threshold or try AdaptiveDetector

## Future CLI Commands (Will Be Implemented)

These commands don't exist yet - you'll build them:

```bash
# Activate virtual environment first
source venv/bin/activate

# Scene detection (Phase 1)
python -m motd_analyzer detect-scenes video.mp4 --output scenes.json

# Team extraction (Phase 2)
python -m motd_analyzer extract-teams --scenes scenes.json --output teams.json

# Transcription (Phase 3)
python -m motd_analyzer transcribe --video video.mp4 --output transcript.json

# Full pipeline (Phase 4)
python -m motd_analyzer process video.mp4 --output analysis.json

# Batch processing (Phase 7)
python -m motd_analyzer batch data/videos/*.mp4 --output-dir data/output

# Manual validation (Phase 5)
python -m motd_analyzer label-scenes scenes.json
python -m motd_analyzer validate --auto analysis.json --manual manual_labels.json
```

See `docs/architecture.md` for detailed CLI specifications.

## Critical Configuration Details

### Premier League Teams - 2025/26 Season (Important!)
File: `data/teams/premier_league_2025_26.json`
- **Promoted**: Burnley, Leeds United, Sunderland
- **Relegated**: Ipswich Town, Leicester City, Southampton
- 20 teams total

**Do not use outdated 2024/25 data** - it has the wrong teams.

### OCR Regions (For 1920x1080 Video)
```yaml
scoreboard:    # Top-left BBC graphic
  x: 0, y: 0, width: 400, height: 100
formation:     # Bottom-right formation graphic
  x: 800, y: 600, width: 1920, height: 1080
```
Adjust these if BBC changes graphics or video resolution differs. Check with `ffprobe video.mp4`.

### Caching Strategy
All intermediate results cached in `data/cache/{episode_id}/`:
- `scenes.json` - Scene transitions
- `ocr_results.json` - Raw OCR text
- `transcript.json` - Full Whisper transcription (**expensive!**)
- `manual_labels.json` - Manual corrections
- `frames/` - Extracted key frames

**Never re-run Whisper unnecessarily** - it's the slowest stage.

## British English Conventions

Use British spelling throughout codebase and docs:
- analyser (not analyzer)
- colour (not color)
- optimise (not optimize)
- visualisation (not visualization)

**Exception**: Python package name is `motd_analyzer` (ASCII-compatible, US spelling is acceptable for code identifiers).

## Validation Targets (From Planning)

### After Scene Detection (Task 008)
- Expected: 40-80 scenes for 90-min video
- Too few (<20)? Lower `scene_detection.threshold` in config
- Too many (>200)? Raise threshold

### After OCR (Task 009)
- Target: >90% team detection accuracy
- If failing: Adjust OCR regions, add team name alternates, or consider PaddleOCR

### After Transcription (Task 010)
- Target: >95% transcription accuracy
- Already using fastest option (faster-whisper large-v3)

### After Full Pipeline (Task 011)
- Target: >85% segment classification accuracy
- Use manual validation (Task 012) to establish ground truth before batch processing

## Common Pitfalls to Avoid

1. **Don't use `openai-whisper`** - Use `faster-whisper` (seriously, 4x speed difference)
2. **Don't skip epic splitting** - Tasks 008+ need breakdown before coding
3. **Don't skip validation checkpoints** - Each task has them for a reason
4. **Don't assume video resolution** - BBC might not be 1920x1080, check first
5. **Don't over-engineer early** - Start with simple heuristics, add ML later if needed
6. **Don't commit large files** - Videos, cache, output are gitignored
7. **Don't skip caching** - Re-running Whisper = hours wasted

## Where to Find Information

- **"How do I implement X?"** → `docs/roadmap.md` (detailed code examples)
- **"Why this library?"** → `docs/tech-tradeoffs.md` (comparisons + alternatives)
- **"What's next?"** → `docs/tasks/README.md` (task list + status)
- **"What should the output look like?"** → `docs/prd.md` section 3.4 (JSON schema)
- **"What's the big picture?"** → `docs/architecture.md` (system design)
- **"How do I start?"** → `docs/tasks/001-environment-setup.md` (first task)

## Output Schema (Planned)

Final JSON structure per episode:
```json
{
  "episode_date": "2025-08-17",
  "matches": [
    {
      "running_order": 1,
      "teams": ["Manchester United", "Fulham"],
      "segments": [
        {"type": "studio_intro", "duration_seconds": 45},
        {"type": "highlights", "duration_seconds": 375},
        {"type": "interview", "duration_seconds": 90},
        {"type": "studio_analysis", "first_team_mentioned": "Manchester United", "duration_seconds": 225}
      ],
      "total_airtime_seconds": 735
    }
  ]
}
```

See `docs/prd.md` section 3.4 for complete schema with all fields.

## Getting Started Right Now

```bash
# 1. Open the task list
open docs/tasks/README.md

# 2. Start with task 001
open docs/tasks/001-environment-setup.md

# 3. Follow the task sequentially, validate at each checkpoint
# 4. Reference docs/roadmap.md when you need code examples
# 5. Split epics (008+) before implementing them
```

**Remember**: This is a marathon, not a sprint. The planning is done. Now execute methodically, one task at a time, with validation at every step.

Up the Addicks! ⚽🔴⚪
