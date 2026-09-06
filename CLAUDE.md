# CLAUDE.md

## What This Project Does

**MOTD Analyser** - Video analysis pipeline to objectively measure coverage bias in BBC's Match of the Day. Uses LLM-based analysis to identify running order, segment boundaries, and airtime distribution from MOTD episodes (2026/27 season).

**Workflow:** Metadata → download → subtitles → transcript → Claude analysis → publish

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

**One call per match, and the model is asked only where.** Every attempt to get a whole
running order from one call collapsed — an array stopped after one entry, and a required
property per candidate was worse, returning all-unshown in four variants and exceeding the
compiled-grammar limit above eight candidates. The same model locates each match correctly
when that is the entire question. `analyse` therefore loops the candidates, and the prompt
is split so the transcript is written to cache once and read back by every later call.

**The model reports evidence; the analysis derives the rest.** It emits no position and no
verdict — `order` is the rank of the timestamps it reported, so gaps and repeats are not
expressible, and presence follows from having timings at all. Both were judgement slots the
model could satisfy with a default, and defaults are what it kept reaching for.

**The squad list is what holds a match to its timings.** `_assert_spans_name_the_clubs`
checks that the span claimed for a match names a player from one of the two clubs, using
`data/squads/`. Players belong to one club, so this tests the timestamps rather than the
prose — and it is the only separator the round-up has, where the studio hands over to
nothing and matches run back to back. A handover quote is still recorded and verified
where one exists, but it is never required: it proves a line is somewhere in the
transcript, not that it is where the answer says it is.

**A run fails whole or not at all.** A match that cannot be located, a span naming
neither club, a quote that is not in the transcript, two matches claiming the same
package, or timings covering less than `MIN_TIMELINE_SHARE` of the content window all raise. Nothing is written when they do: a
half-filled analysis is worse than none, because the transcript cannot be re-fetched once
iPlayer drops the episode.

**The roster is metadata, not analysis.** It is unrecoverable from a transcript — the TTML
carries a four-colour speaker palette but no names — but BBC credits it themselves, so
`roster.from_credits` derives presenter, pundits and editor from `data/metadata/` and
`data/rosters/motd_{season}.json` supplies only what BBC omits. Guests are the standing
case: a visiting manager is on screen and never credited. Neither is written into
`data/analysis/`: that file is rewritten wholesale by every `analyse` run, which would
fight a hand-edited field. `publisher` joins them into a `PublishedEpisode` on the way
out, so correcting a roster costs a re-publish rather than a billed re-analysis.

**BBC's own record of an episode is worth keeping** (`programme.py`). `/programmes/{pid}.json`
is a permanent catalogue — it answers years after iPlayer has dropped the video — and
carries the broadcast date, the version pid and BBC's billing, which names the presenter
and counts the matches. The iPlayer business layer adds what only it knows: the content
window and the availability deadline. Stored verbatim in BBC's own vocabulary rather than
mapped down to the roster's, because their roles do not line up with ours in either
direction: they have no role for a guest, and they credit the **editor**, who changes week
to week and is the one person who chose the running order.

**Airtime is measured against the content window, not the file.** iPlayer publishes where
the programme proper starts and ends (`started`/`ended` playback events), which on a typical
episode excludes a 30-second lead-in and about two minutes of end credits.
`MIN_TIMELINE_SHARE` is checked against that when the metadata has been fetched, and falls
back to the full runtime when it has not.

**Analyses are committed, everything else is cache.** `analyse` writes
`data/analysis/{episode_id}.json` and that file is the source of truth: publishing and any
downstream site read it, and it cannot be re-derived once iPlayer drops the episode and the
transcript with it.

**The candidate window is the gameweek, not the broadcast date** (`fixtures.candidates_for_broadcast`).
An episode shows more than that day's matches: a Friday game held over to Saturday's show, or
a round-up of Saturday action on Sunday. Deliberately wider than any one episode needs.

## Architecture Overview

**5-stage pipeline:** Metadata → Download → Transcribe → Analyse → Publish

Metadata runs first because it carries the broadcast date the rest of the pipeline keys
off. The video is downloaded as a matter of course even though nothing reads it yet:
iPlayer drops an episode after 30 days and it cannot be re-fetched. `--no-video` opts out.

**Modules** (`src/motd/`):
- `models.py` - **Pydantic data contracts** (Transcript, EpisodeAnalysis, Fixture, etc.)
- `roster.py` - **Studio roster** (presenter/pundits/editor from BBC credits, guests by hand)
- `programme.py` - **BBC metadata** (/programmes + iPlayer business layer → EpisodeMetadata)
- `fixtures.py` - **Fixture loading** (FixtureProvider interface + FileFixtureProvider + candidate window)
- `squads.py` - **Squad lookup** (which clubs a stretch of commentary names)
- `fpl.py` - **Fixture sync** (Fantasy Premier League API → season fixtures and squads)
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
- `data/` - Fixtures, teams, metadata and analysis outputs (committed); videos and cache
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
`data/fixtures/premier_league_{season}.json`, and squads from the same sync at
`data/squads/premier_league_{season}.json`. The API only serves the season in
progress — there is no archive endpoint, so past seasons cannot be re-fetched.

Squads are a snapshot taken when the sync ran, so a January transfer moves a player
out from under an August episode. That is tolerable because analysis happens within
days of broadcast, and a match only needs one of its players named to check out.

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
- **MOTD covers every match in its window.** It is the highlights show for the whole
  division — the Sky/TNT/Amazon rights split governs live coverage, not highlights — so
  which matches appeared is not a question to put to a model. A candidate that cannot be
  located in the transcript is a failed run, not a match that did not air.
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
- `python -m motd run VIDEO_PATH [--url URL] [--date YYYY-MM-DD] [--episode-id ID] [--skip-to STAGE] [--force] [--no-video]`

**Fixture data:**
- `python -m motd fixtures sync [--dry-run]` — refresh the current season's fixtures and
  squads from the FPL API; both come from the one bootstrap payload, so they cannot drift apart

**Episode metadata:**
- `python -m motd metadata fetch URL_OR_ID` — store BBC's record and credits for an episode
- `python -m motd metadata show EPISODE_ID` — print the stored record and BBC's billing

**Roster data:**
- `python -m motd roster show SEASON` — list the rosters derived from BBC's credits,
  marking the episodes a hand-entered override touches

**Individual stages:**
- `python -m motd download URL_OR_ID [BROADCAST_DATE]` — the date is read from BBC's
  metadata when omitted, and that fetch is stored rather than thrown away
- `python -m motd transcribe VIDEO_PATH [--output PATH] [--force]`
- `python -m motd analyse EPISODE_ID [--output PATH] [--force] [--model ID] [--effort LEVEL] [--cache-ttl 5m|1h|off] [--dry-run]`
  — one API call per match, so a few minutes per episode; `--dry-run` writes the shared
  context half and every per-match task half to the cache dir and makes no API call
- `python -m motd publish EPISODE_ID`

**Judging a prompt or schema change:**
- `uv run python scripts/probe_analysis.py EPISODE_ID [EFFORT ...]` — runs the live prompt and
  prints what `analyse` discards: thinking, token counts, whether each handover quote
  verified. Billed, one call per match per effort level.

**Tests:**
- `uv run pytest`

Use `--help` on any command for full options.
