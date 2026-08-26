# Data Directory

- `videos/` - Source video files (gitignored, not committed)
- `cache/{episode_id}/` - Pipeline intermediates (gitignored):
  - `subtitles.ttml` - EBU-TT/TTML as iPlayer published it
  - `transcript.json` - Transcription with timestamps
  - `prompt.{context,task}.txt` - `analyse --dry-run` output
- `analysis/{episode_id}.json` - Structured episode analysis. Committed: this is the
  source of truth downstream reads, and it cannot be re-derived once iPlayer drops the episode.
- `fixtures/` - Fixture JSON files (e.g., `premier_league_2026_27.json`)
- `teams/` - Team list JSON files (e.g., `premier_league_2026_27.json`)
