# Task 010: Audio Transcription (Epic)

## Objective
Extract audio from video and transcribe using faster-whisper to enable team mention detection.

## Prerequisites
- [009-ocr-implementation-epic.md](009-ocr-implementation-epic.md) completed

## Epic Overview
Split this epic into sub-tasks:
1. Implement audio extractor (ffmpeg wrapper)
2. Implement Whisper transcriber (faster-whisper integration)
3. Create transcription CLI command
4. Run on test video
5. Validate transcription accuracy

## Key Deliverables

### Audio Extractor (`src/motd_analyzer/transcription/audio_extractor.py`)
- Use ffmpeg to extract audio track
- Convert to 16kHz mono WAV (Whisper requirement)

### Whisper Transcriber (`src/motd_analyzer/transcription/whisper_transcriber.py`)
- Load faster-whisper model (large-v3 recommended)
- Transcribe with word-level timestamps
- Return segments with timing info

### CLI Command
```bash
python -m motd_analyzer transcribe \
  --video data/videos/your_video.mp4 \
  --output data/cache/test/transcript.json
```

## Success Criteria
- [ ] Audio extraction works
- [ ] Transcription completes without errors
- [ ] Transcription accuracy >95% (spot-check segments)
- [ ] Word-level timestamps present

## Estimated Time
2-3 hours (+ 10-15 mins transcription time for 90-min video)

## Notes
- Using faster-whisper (not standard whisper) for 4x speed improvement
- M3 Pro will leverage GPU automatically
- First run downloads Whisper model (~3GB)

## Reference
See [roadmap.md Phase 3](../roadmap.md#phase-3-audio-transcription-est-4-6-hours) for code examples.

## Next Task
[011-analysis-pipeline-epic.md](011-analysis-pipeline-epic.md)
