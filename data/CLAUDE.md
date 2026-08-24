# Data Directory

- `videos/` - Source video files (gitignored, not committed)
- `cache/{episode_id}/` - Pipeline outputs:
  - `transcript.json` - Transcription with timestamps
  - `analysis.json` - Structured episode analysis
- `fixtures/` - Fixture JSON files (e.g., `premier_league_2026_27.json`)
- `teams/` - Team list JSON files (e.g., `premier_league_2026_27.json`)
- `episodes/` - Episode manifest (episode_manifest.json) — provenance only, not read by the pipeline
