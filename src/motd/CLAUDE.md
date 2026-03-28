# src/motd

Main package for MOTD video analysis pipeline.

- `__main__.py` - CLI entry point (run with `python -m motd`)
- `models.py` - Pydantic data contracts (Transcript, EpisodeAnalysis, Fixture, etc.)
- `fixtures.py` - Fixture loading (FixtureProvider interface + FileFixtureProvider)
- `transcriber.py` - Transcription via OpenAI Whisper API (stub)
- `analyser.py` - LLM-based analysis via Claude (stub)
- `publisher.py` - Publish to Cloudflare R2 (stub)
- `downloader.py` - Download from BBC iPlayer via yt-dlp (stub)
- `pipeline.py` - Pipeline orchestrator (stub)
