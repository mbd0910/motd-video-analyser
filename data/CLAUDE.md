# Data Directory

- `videos/` - Source video files (gitignored, not committed)
- `cache/{episode_id}/` - Pipeline intermediates (gitignored):
  - `subtitles.ttml` - EBU-TT/TTML as iPlayer published it
  - `transcript.json` - Transcription with timestamps
  - `prompt.{context,tasks}.txt` - `analyse --dry-run` output: the transcript half
    every match shares, and the per-match halves concatenated
- `analysis/{episode_id}.json` - Structured episode analysis. Committed: this is the
  source of truth downstream reads, and it cannot be re-derived once iPlayer drops the episode.
- `metadata/{episode_id}.json` - BBC's own record of an episode: broadcast date, version
  pid, synopses, credits, content window, availability deadline. Committed, and stored in
  BBC's vocabulary rather than mapped down to ours. `/programmes` serves it indefinitely,
  so unlike a transcript it could be re-fetched — it is committed as the provenance for a
  derived roster, and because the iPlayer half of it expires with the episode.
- `rosters/motd_{season}.json` - Only what BBC's credits omit, keyed by episode_id: guests
  above all, plus overrides for a credit that is wrong or missing. Hand-entered and
  committed. Presenter, pundits and editor are derived from `metadata/`; the two are joined
  onto the analysis at publish time, never written into it.
- `fixtures/` - Fixture JSON files (e.g., `premier_league_2026_27.json`)
- `squads/` - Squad names per club code, written by the same `fixtures sync`. Committed:
  the analyser checks a claimed span against who is named in it, and FPL serves only the
  season in progress.
- `teams/` - Team list JSON files (e.g., `premier_league_2026_27.json`)
