# CLAUDE.md

## What This Project Does

**MOTD Analyser** - Video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Uses LLM-based analysis to identify running order, segment boundaries, and airtime distribution from MOTD episodes (2026/27 season).

**Workflow:** Download → subtitles → transcript → Claude analysis → publish

**User goal**: Settle football fan debates ("we're never on first!", "there's an agenda against my team") with data, not perception.

## How Analysis Works

**The analysis is LLM-based, not rule-based.** Transcripts are parsed from the EBU-TT/TTML
subtitles iPlayer publishes alongside an episode; the Claude API then reads the transcript
against the gameweek's fixtures to identify running order and segment boundaries.
`transcriber.py` keeps a speech-to-text path for video without usable subtitles.

**The model never emits an identifier.** It is handed the candidate fixtures as an enumerated
list and constrained by a JSON schema (`analyser._build_schema`) to echo back one of those
exact labels, which `_resolve_matches` maps to a fixture in code. Everything else — team
names, venue, score — joins in from the fixture row rather than being restated by the model.

**The answer commits to the sweep before it writes it.** `_build_schema` puts a required
`walkthrough` string ahead of `running_order`, because property order is generation order:
the model writes out its pass over the transcript first, then fills an array it is already
answerable to. Without it the analyser returned one or two matches out of six at every
effort level — reasoning does not constrain the answer block, and `minItems` above 1 is
rejected by structured outputs. The walkthrough is kept in provenance for auditing coverage,
but it is model prose, not an index: it can contain overlaps the array resolves.

**The roster is metadata, not analysis.** Who presented and punditted an episode lives in
`data/rosters/motd_{season}.json`, hand-entered — the TTML carries a four-colour speaker
palette but no names, so it is unrecoverable from a transcript. It is never written into
`data/analysis/`: that file is rewritten wholesale by every `analyse` run, which would
fight a hand-edited field. `publisher` joins the two into a `PublishedEpisode` on the way
out, so correcting a roster costs a re-publish rather than a billed re-analysis.

**Analyses are committed, everything else is cache.** `analyse` writes
`data/analysis/{episode_id}.json` and that file is the source of truth: publishing and any
downstream site read it, and it cannot be re-derived once iPlayer drops the episode and the
transcript with it.

**The candidate window is the gameweek, not the broadcast date** (`fixtures.candidates_for_broadcast`).
An episode shows more than that day's matches: a Friday game held over to Saturday's show, or
a round-up of Saturday action on Sunday. Deliberately wider than any one episode needs.

## Architecture Overview

**4-stage pipeline:** Download (optional) → Transcribe → Analyse → Publish

**Modules** (`src/motd/`):
- `models.py` - **Pydantic data contracts** (Transcript, EpisodeAnalysis, Fixture, etc.)
- `roster.py` - **Studio roster** (per-episode presenter/pundits/guests, loaded per season)
- `fixtures.py` - **Fixture loading** (FixtureProvider interface + FileFixtureProvider + candidate window)
- `fpl.py` - **Fixture sync** (Fantasy Premier League API → season fixtures file)
- `clubs.py` - **Club directory** (club code → canonical name, nicknames, venue)
- `subtitles.py` - **Subtitles** (yt-dlp fetch + EBU-TT/TTML parse → Transcript)
- `transcriber.py` - **Speech-to-text** (OpenAI Whisper API, chunked; standalone path)
- `analyser.py` - **Analysis** (Claude API, schema-constrained to the candidate fixtures)
- `publisher.py` - **Publishing** (Cloudflare R2)
- `downloader.py` - **Download** (yt-dlp from BBC iPlayer)
- `pipeline.py` - **Orchestrator** (sequences all stages)
- `episode.py` - **Episode identity** (episode_id format, season derivation, cache paths)
- `cache.py` - **Cache** (get_or_compute / load for pipeline artefacts)
- `__main__.py` - **CLI entry point** (`python -m motd`)

**Key deps:** Pydantic v2, Click, anthropic

**Credentials:** copy `.env.template` to `.env`. `analyse` needs `ANTHROPIC_API_KEY`. The CLI
calls `load_dotenv()` from the working directory; real environment variables win over the file.

## Project Structure

- `src/motd/` - Main package
- `data/` - Fixtures, teams and analysis outputs (committed); videos and cache
  (gitignored) — see `data/CLAUDE.md`
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

**Join on `fpl_code`, not `match_id`.** match_id embeds the date, so a postponed fixture
silently becomes a different id; FPL's `code` follows the fixture through rescheduling.
Clubs carry an `fpl_code` too — FPL's stable club id, unlike the `id` in the same payload,
which is a 1-20 alphabetical rank that reshuffles on every promotion. `fixtures sync` fails
before writing if the directory and the live payload disagree.

## Domain Facts

- **Running order is editorial, not chronological.** Which match leads the show is the
  central research question; kickoff times tell you nothing about it.
- **MOTD covers roughly 7 of the 10 Saturday fixtures.** Sky, TNT and Amazon hold rights to
  the rest, so the analyser is handed every fixture for the broadcast date and works out
  from the transcript which ones actually appeared.
- **Segment keys are `studio_intro`, `highlights`, `studio_analysis`**, defined by the
  prompt in `analyser.py`. Post-match interviews fall inside the highlights run.
- **A match can appear in two episodes.** MOTD2 round-ups revisit Saturday games covered the
  night before. Both are recorded the same way; full package versus brief second look is
  derived later from duration and earlier episodes, not stored.
- **Subtitle colour is not an identity.** BBC marks speaker changes with a four-colour
  palette reused across the whole programme: white is the presenter in studio but the
  commentator during highlights. It separates voices within a stretch; it does not name them.
- **This stage produces running order and timings only.** No interpretation, no airtime
  aggregation, no bias measurement — those come later, off the stored data.

## Common Commands

Commands below assume `uv run` in front, or an activated `.venv`.

**Full pipeline:**
- `python -m motd run VIDEO_PATH [--url URL --date YYYY-MM-DD] [--episode-id ID] [--skip-to STAGE] [--force]`

**Fixture data:**
- `python -m motd fixtures sync [--dry-run]` — refresh the current season's fixtures from the FPL API

**Roster data:**
- `python -m motd roster show SEASON` — list the recorded rosters and validate the file

**Individual stages:**
- `python -m motd download URL_OR_ID BROADCAST_DATE` (date as YYYY-MM-DD — iPlayer metadata has no date fields)
- `python -m motd transcribe VIDEO_PATH [--output PATH] [--force]`
- `python -m motd analyse EPISODE_ID [--output PATH] [--force] [--model ID] [--effort LEVEL] [--cache-ttl 5m|1h|off] [--dry-run]`
  — `--dry-run` writes the prompt's two halves to the cache dir and makes no API call
- `python -m motd publish EPISODE_ID`

**Judging a prompt or schema change:**
- `uv run python scripts/probe_analysis.py EPISODE_ID [EFFORT ...]` — runs the live prompt and
  prints what `analyse` discards: thinking, token counts, emitted key order, the walkthrough.
  Billed, one call per effort level.

**Tests:**
- `uv run pytest`

Use `--help` on any command for full options.
