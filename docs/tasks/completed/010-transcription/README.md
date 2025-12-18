# Task 010: Audio Transcription

> **Last reviewed:** 2025-12-18

## Summary

Implemented audio extraction and transcription using faster-whisper for team mention detection and segment classification.

## Approach

1. **Audio extraction** - ffmpeg wrapper converts video to 16kHz mono WAV (Whisper optimal)
2. **Whisper transcriber** - faster-whisper integration with large-v3 model
3. **Word-level timestamps** - Essential for detecting "first team mentioned"
4. **CLI command** (`python -m motd transcribe`) - End-to-end with caching

## Key Decisions

- **faster-whisper over openai-whisper** - 4x faster (3-4 mins vs 15-20 mins per 90-min video)
- **large-v3 model** - Best accuracy, acceptable speed on M3 Pro
- **Aggressive caching** - Whisper is the slowest pipeline stage, cache in `data/cache/{episode_id}/transcript.json`
- **GPU auto-detection** - Uses MPS on Apple Silicon when available

## Results

- Episode 01.11: 1,773 segments transcribed in ~5 minutes (GPU)
- Word-level timestamps present on all segments
- Team name accuracy: 100%
- Pundit name accuracy: 100%
- Timestamp accuracy: ±1 second
