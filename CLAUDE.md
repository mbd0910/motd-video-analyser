# CLAUDE.md

## What This Project Does

**MOTD Analyser** - Video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Uses LLM-based analysis to identify running order, segment boundaries, and airtime distribution from MOTD episodes (2025/26 season).

**Workflow:** Run automated pipeline → Generate LLM prompt → Claude analysis → Save structured JSON

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## How Analysis Works

**The analysis is LLM-based, not rule-based.** Transcription (OpenAI Whisper API) produces a timestamped transcript. Claude analyses the transcript against fixture data to identify running order, segment boundaries, and durations.

## Architecture Overview

**4-stage pipeline:** Download (optional) → Transcribe → Analyse → Publish

**Modules** (`src/motd/`):
- `models.py` - **Pydantic data contracts** (Transcript, EpisodeAnalysis, Fixture, etc.)
- `fixtures.py` - **Fixture loading** (FixtureProvider interface + FileFixtureProvider)
- `fpl.py` - **Fixture sync** (Fantasy Premier League API → season fixtures file)
- `clubs.py` - **Club directory** (club code → canonical name, nicknames, venue)
- `transcriber.py` - **Transcription** (OpenAI Whisper API, chunked)
- `analyser.py` - **Analysis** (Claude via `claude -p`)
- `publisher.py` - **Publishing** (Cloudflare R2)
- `downloader.py` - **Download** (yt-dlp from BBC iPlayer)
- `pipeline.py` - **Orchestrator** (sequences all stages)
- `episode.py` - **Episode identity** (episode_id format, season derivation, cache paths)
- `cache.py` - **Cache** (get_or_compute / load for pipeline artefacts)
- `__main__.py` - **CLI entry point** (`python -m motd`)

**Key deps:** Pydantic v2, Click

## Project Structure

- `src/motd/` - Main package
- `config/` - Configuration files (config.yaml)
- `data/` - Videos, cache, analysis outputs (gitignored) — see `data/CLAUDE.md`
- `docs/` - Documentation and domain knowledge
- `tests/` - Test suite

## Critical Warnings

- Activate virtual environment (`source venv/bin/activate`) before running Python commands
- Check `data/cache/{episode_id}/` before re-running expensive operations (transcription takes 15-20 mins)
- Never commit files in `data/videos/` or `data/cache/`

## Committing

Commit directly to main.

## Code Style

- **Line length**: 100 characters
- **Spelling**: British English (analyser, colour, optimise)

## Fixture Data

Fixtures come from the public Fantasy Premier League API, one file per season at
`data/fixtures/premier_league_{season}.json`. The API only serves the season in
progress — there is no archive endpoint, so 2025/26 stays hand-maintained.

Club names and venues are not in the FPL payload; `fixtures sync` resolves them
from `data/teams/premier_league.json`, keyed by three-letter club code. A newly
promoted club must be added there or the sync fails loudly.

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
- `python -m motd run VIDEO_PATH [--url URL --date YYYY-MM-DD] [--episode-id ID] [--skip-to STAGE] [--force]`

**Fixture data:**
- `python -m motd fixtures sync [--dry-run]` — refresh the current season's fixtures from the FPL API

**Individual stages:**
- `python -m motd download URL_OR_ID BROADCAST_DATE` (date as YYYY-MM-DD — iPlayer metadata has no date fields)
- `python -m motd transcribe VIDEO_PATH [--output PATH] [--force]`
- `python -m motd analyse EPISODE_ID [--output PATH] [--force]`
- `python -m motd publish EPISODE_ID`

**Tests:**
- `pytest`

Use `--help` on any command for full options.
