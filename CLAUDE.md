# CLAUDE.md

## What This Project Does

**MOTD Analyser** - Video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Uses LLM-based analysis to identify running order, segment boundaries, and airtime distribution from MOTD episodes (2026/27 season).

**Workflow:** Download → subtitles → transcript → Claude analysis → publish

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## How Analysis Works

**The analysis is LLM-based, not rule-based.** Transcripts are parsed from the EBU-TT/TTML
subtitles iPlayer publishes alongside an episode; `claude -p` then analyses the transcript
against the day's fixtures to identify running order, segment boundaries, and durations.
`transcriber.py` keeps a speech-to-text path for video without usable subtitles.

## Architecture Overview

**4-stage pipeline:** Download (optional) → Transcribe → Analyse → Publish

**Modules** (`src/motd/`):
- `models.py` - **Pydantic data contracts** (Transcript, EpisodeAnalysis, Fixture, etc.)
- `fixtures.py` - **Fixture loading** (FixtureProvider interface + FileFixtureProvider)
- `fpl.py` - **Fixture sync** (Fantasy Premier League API → season fixtures file)
- `clubs.py` - **Club directory** (club code → canonical name, nicknames, venue)
- `subtitles.py` - **Subtitles** (yt-dlp fetch + EBU-TT/TTML parse → Transcript)
- `transcriber.py` - **Speech-to-text** (OpenAI Whisper API, chunked; standalone path)
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
- `data/` - Videos, cache, analysis outputs (gitignored) — see `data/CLAUDE.md`
- `tests/` - Test suite

## Critical Warnings

- Run Python commands through `uv run` (or activate `.venv` first); `uv sync` after any dependency change
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
progress — there is no archive endpoint, so past seasons cannot be re-fetched.

Club names and venues are not in the FPL payload; `fixtures sync` resolves them
from `data/teams/premier_league.json`, keyed by three-letter club code. A newly
promoted club must be added there or the sync fails loudly.

## Domain Facts

- **Running order is editorial, not chronological.** Which match leads the show is the
  central research question; kickoff times tell you nothing about it.
- **MOTD covers roughly 7 of the 10 Saturday fixtures.** Sky, TNT and Amazon hold rights to
  the rest, so the analyser is handed every fixture for the broadcast date and works out
  from the transcript which ones actually appeared.
- **Segment keys are `studio_intro`, `highlights`, `studio_analysis`**, defined by the
  prompt in `analyser.py`. Post-match interviews fall inside the highlights run.

## Common Commands

Commands below assume `uv run` in front, or an activated `.venv`.

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
- `uv run pytest`

Use `--help` on any command for full options.
