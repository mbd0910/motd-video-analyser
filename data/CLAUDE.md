# Data Directory

- `videos/` - Source video files (gitignored, not committed)
- `cache/{episode_id}/` - Pipeline intermediates (gitignored):
  - `subtitles.ttml` - EBU-TT/TTML as iPlayer published it
  - `transcript.json` - Transcription with timestamps
  - `prompt.{context,tasks}.txt` - `analyse --dry-run` output: the transcript half
    every match shares, and the per-match halves concatenated
- `analysis/{episode_id}.json` - Structured episode analysis. Committed: this is the
  source of truth downstream reads, and it cannot be re-derived once iPlayer drops the episode.
- `rosters/motd_{season}.json` - Studio roster per episode (presenter, pundits, guests),
  keyed by episode_id. Hand-entered and committed: the subtitles carry no names, so this
  cannot be derived. Joined onto the analysis at publish time, never written into it.
- `fixtures/` - Fixture JSON files (e.g., `premier_league_2026_27.json`)
- `squads/` - Squad names per club code, written by the same `fixtures sync`. Committed:
  the analyser checks a claimed span against who is named in it, and FPL serves only the
  season in progress.
- `teams/` - Team list JSON files (e.g., `premier_league_2026_27.json`)
