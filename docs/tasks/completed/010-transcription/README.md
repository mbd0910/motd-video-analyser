# Task 010: Audio Transcription (Epic)

## Status
⏳ Not Started

## Objective
Extract audio from video and transcribe using faster-whisper to enable team mention detection and segment classification.

## Prerequisites
- Task 009 (OCR Implementation Epic) completed
- Test video available with OCR results

## Epic Overview

This epic is broken down into **6 phased subtasks** following the proven Task 009 pattern:

### Phase Structure: Reconnaissance → Core Modules → Integration → Execution → Validation

1. **[010a: Audio Reconnaissance](010a-audio-reconnaissance.md)** (30-45 min)
   - Inspect test video audio properties with ffprobe
   - Extract and verify 30-second sample
   - Document format and quality
   - **Deliverable:** Audio characteristics documentation

2. **[010b: Audio Extractor](010b-audio-extractor.md)** (45-60 min)
   - Implement ffmpeg wrapper for audio extraction
   - Convert to Whisper-optimal format (16kHz mono WAV)
   - Add error handling and logging
   - **Deliverable:** `src/motd/transcription/audio_extractor.py`

3. **[010c: Whisper Transcriber](010c-whisper-transcriber.md)** (1-1.5 hours)
   - Integrate faster-whisper (NOT openai-whisper - 4x faster!)
   - Implement word-level timestamp extraction
   - Support GPU/CPU with auto-detection
   - **Deliverable:** `src/motd/transcription/whisper_transcriber.py`

4. **[010d: CLI Integration](010d-cli-integration.md)** (45-60 min)
   - Create `transcribe` CLI command
   - Wire audio extractor + transcriber
   - Implement caching (critical for Whisper!)
   - **Deliverable:** End-to-end CLI command

5. **[010e: Execution](010e-execution.md)** (15-20 min + processing)
   - Run transcription on full test video
   - Monitor performance (GPU/CPU usage)
   - Verify output and caching
   - **Deliverable:** Full transcript JSON + execution report

6. **[010f: Validation](010f-validation.md)** (45-60 min)
   - Manually validate 15-20 sampled segments
   - Check team names, pundit names, timestamps
   - Target: >95% accuracy on critical elements
   - **Deliverable:** Validation report with accuracy metrics

**Total Time:** 4-5 hours (active work) + 10-15 min (processing)

## Key Deliverables Summary

### Modules
- **Audio Extractor** (`src/motd/transcription/audio_extractor.py`)
  - ffmpeg wrapper for audio extraction
  - Converts to 16kHz mono WAV (Whisper optimal format)
  - Error handling for missing/invalid video files

- **Whisper Transcriber** (`src/motd/transcription/whisper_transcriber.py`)
  - faster-whisper integration (large-v3 model)
  - Word-level timestamp extraction
  - GPU/CPU auto-detection and fallback

### CLI Command
```bash
# Basic usage
python -m motd transcribe data/videos/motd_2025-11-01.mp4

# With options
python -m motd transcribe data/videos/motd_2025-11-01.mp4 \
  --output custom.json \
  --model-size large-v3 \
  --force
```

### Output Format
```json
{
  "video_path": "data/videos/motd_2025-11-01.mp4",
  "duration_seconds": 5400.2,
  "segment_count": 342,
  "segments": [
    {
      "id": 0,
      "text": "Welcome to Match of the Day.",
      "start": 12.5,
      "end": 15.2,
      "words": [
        {"word": "Welcome", "start": 12.5, "end": 12.8, "probability": 0.98},
        ...
      ]
    }
  ]
}
```

## Success Criteria

All 6 subtasks must be completed:
- [x] 010a: Audio reconnaissance complete
- [x] 010b: Audio extractor implemented and tested
- [x] 010c: Whisper transcriber implemented and tested
- [x] 010d: CLI command integrated with caching
- [x] 010e: Full video transcription executed successfully
- [ ] 010f: Accuracy validated (>95% on critical elements)

## Completion Checklist

Before marking Task 010 as complete, verify:
- ✅ All subtask files have checkboxes marked complete
- ✅ Audio extraction works reliably
- ✅ Transcription completes without errors
- ✅ Caching prevents re-processing
- ✅ Word-level timestamps present
- ✅ Team names transcribed correctly (>95%)
- ✅ Pundit names transcribed correctly (>95%)
- ✅ Timestamps accurate within ±1 second
- ✅ Processing time acceptable (3-15 min per video)
- ✅ Validation documentation created

## Important Notes

### Critical Technology Decision
**Use faster-whisper, NOT openai-whisper!**
- faster-whisper: 3-4 min per 90-min video (25-30x real-time)
- openai-whisper: 10-15 min per 90-min video (6-9x real-time)
- Same accuracy, 4x speed difference

### Performance Expectations
- **GPU (Apple M3 Pro):** 3-4 minutes per 90-min video
- **CPU fallback:** 15-20 minutes per 90-min video
- **Model download:** ~3GB on first run (one-time)
- **Output size:** ~2-5MB JSON per 90-min video

### Caching Strategy
**Critical:** Whisper is expensive (3-15 min per video)
- Cache transcript in `data/cache/{video_name}/transcript.json`
- Check cache before re-processing
- Use `--force` flag only when needed
- Keep audio.wav for debugging

### Why Word-Level Timestamps Matter
Needed for downstream analysis:
- Detect "first team mentioned" in studio segments
- Align speech with video segments
- Support manual validation
- Enable time-based filtering

## Key Differences from Task 009

Task 010 is **simpler than Task 009**:
- ✅ Linear pipeline (audio → text) vs multi-component OCR
- ✅ Fewer modules (2 vs 3)
- ✅ Less tuning needed (Whisper works well out-of-box)
- ✅ No fixture matching equivalent

But still follows same **phased approach**:
1. Reconnaissance (understand input)
2. Core implementation (build modules)
3. Integration (wire together)
4. Execution (test on real data)
5. Validation (measure accuracy)

## Reference Documentation
- [docs/roadmap.md - Phase 3: Audio Transcription](../../roadmap.md)
- [docs/architecture.md - Transcription Module Design](../../architecture.md)
- [docs/tech-tradeoffs.md - Whisper Library Comparison](../../tech-tradeoffs.md)
- [Task 009 (completed)](../completed/009-ocr-implementation/) - Pattern reference

## Next Task
After Task 010 complete: **[Task 011: Analysis Pipeline Epic](../011-analysis-pipeline/README.md)**
