# Data Directory

- `videos/` - Source video files (gitignored, not committed)
- `cache/{episode_id}/` - Pipeline outputs:
  - `scenes.json` - Scene detection results
  - `ocr_results.json` - Team extraction results
  - `transcript.json` - Transcription with timestamps
  - `frames/` - Extracted key frames
- `analysis/{episode_id}/` - Final analysis outputs
- `teams/` - Team list JSON files (e.g., `premier_league_2025_26.json`)
