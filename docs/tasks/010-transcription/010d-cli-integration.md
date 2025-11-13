# Task 010d: CLI Integration - Transcribe Command

## Status
⏳ Not Started

## Objective
Create a CLI command that orchestrates audio extraction and transcription with intelligent caching to avoid re-processing expensive Whisper operations.

## Prerequisites
- Task 010b (Audio Extractor) completed
- Task 010c (Whisper Transcriber) completed
- Both modules tested independently

## Why This Phase Matters
**Caching is critical for Whisper!** Transcription takes 3-15 minutes per video (depending on GPU/CPU). Without caching:
- Every test run = 3-15 min wait
- Development iteration becomes painfully slow
- Risk of accidentally re-processing same video

The CLI should:
1. Check if transcript already exists → skip if present
2. Extract audio only if needed
3. Transcribe and save results
4. Make results easily accessible for next pipeline stages

## Tasks

### 1. Design CLI Interface
- [ ] Plan command structure:
  ```bash
  python -m motd transcribe VIDEO_PATH [options]

  # Examples:
  python -m motd transcribe data/videos/motd_2025-11-01.mp4
  python -m motd transcribe data/videos/motd_2025-11-01.mp4 --output custom.json
  python -m motd transcribe data/videos/motd_2025-11-01.mp4 --force
  python -m motd transcribe data/videos/motd_2025-11-01.mp4 --model-size medium
  ```
- [ ] Define parameters:
  - `video_path`: Input video (required)
  - `--output`: Custom output path (optional, default: auto-generate)
  - `--force`: Re-transcribe even if cache exists
  - `--model-size`: Whisper model size (optional, default: from config)
  - `--config`: Path to config file (optional, default: config/config.yaml)

### 2. Implement Cache Path Logic
- [ ] Generate cache directory per video:
  ```python
  # For: data/videos/motd_2025-11-01.mp4
  # Cache: data/cache/motd_2025-11-01/
  #   ├── audio.wav          # Extracted audio
  #   └── transcript.json    # Transcription result
  ```
- [ ] Use video filename (without extension) as cache key
- [ ] Create cache directory if doesn't exist
- [ ] Check if transcript.json exists before processing

### 3. Add Transcribe Command to CLI
- [ ] Open `src/motd/__main__.py`
- [ ] Add `transcribe` subcommand to argument parser
- [ ] Import AudioExtractor and WhisperTranscriber
- [ ] Implement command handler function

### 4. Implement Command Logic Flow
- [ ] Parse arguments
- [ ] Load configuration from config.yaml
- [ ] Determine cache paths
- [ ] Check if transcript exists (skip if present and not --force)
- [ ] Extract audio (skip if audio.wav exists)
- [ ] Transcribe audio
- [ ] Save transcript to cache directory
- [ ] Display summary (processing time, segment count, cache location)

### 5. Add Progress Logging
- [ ] Log: "Checking cache for existing transcript..."
- [ ] Log: "Cache hit! Using existing transcript at {path}" (if found)
- [ ] Log: "Extracting audio from video..."
- [ ] Log: "Audio extraction complete: {size}MB, {duration}s"
- [ ] Log: "Transcribing audio with Whisper ({model_size})..."
- [ ] Log: "Transcription complete: {segment_count} segments in {time}s"
- [ ] Log: "Transcript saved to: {path}"
- [ ] Log: "Performance: {real_time_factor}x real-time"

### 6. Implement JSON Output
- [ ] Save transcript in clean JSON format:
  ```json
  {
    "video_path": "data/videos/motd_2025-11-01.mp4",
    "processed_at": "2025-11-13T14:32:01Z",
    "model_size": "large-v3",
    "device": "cuda",
    "language": "en",
    "duration_seconds": 5400.2,
    "segment_count": 342,
    "segments": [
      {
        "id": 0,
        "text": "Welcome to Match of the Day.",
        "start": 12.5,
        "end": 15.2,
        "words": [...]
      }
    ]
  }
  ```
- [ ] Use pretty printing (indent=2) for readability
- [ ] Include metadata for debugging/validation

### 7. Add Error Handling
- [ ] Validate video file exists
- [ ] Handle invalid video format
- [ ] Handle ffmpeg errors (no audio track)
- [ ] Handle Whisper errors (out of memory, model download failure)
- [ ] Handle disk space issues (large files)
- [ ] Provide actionable error messages

### 8. Test End-to-End
- [ ] Run command on test video (first time - no cache)
- [ ] Verify audio extracted to cache
- [ ] Verify transcript saved to cache
- [ ] Run command again (second time - should use cache)
- [ ] Verify cache hit message appears
- [ ] Verify processing is instant (no re-transcription)
- [ ] Test --force flag (should re-transcribe)
- [ ] Test --model-size flag (should use specified model)

### 9. Code Quality Check
- [ ] Follow Python style guidelines
- [ ] Clear argument descriptions in CLI help
- [ ] Error messages are helpful
- [ ] Logging is clear and informative
- [ ] No hardcoded paths
- [ ] Configuration values from config.yaml

## Validation Checklist

Before marking this task complete, verify:

- ✅ `transcribe` command added to CLI
- ✅ All parameters work correctly (video_path, --output, --force, --model-size)
- ✅ Cache checking works (skips if transcript exists)
- ✅ Audio extraction integrated correctly
- ✅ Transcription integrated correctly
- ✅ JSON output is well-formed and complete
- ✅ Progress logging is clear
- ✅ Cache hit/miss logged correctly
- ✅ Error handling works
- ✅ --force flag bypasses cache
- ✅ Running twice uses cache (instant second run)
- ✅ Code follows Python guidelines

## Expected Output

**Files modified:**
- `src/motd/__main__.py` (add transcribe command)

**Example CLI help output:**
```bash
$ python -m motd transcribe --help
usage: motd transcribe [-h] [--output OUTPUT] [--force]
                       [--model-size {base,small,medium,large-v2,large-v3}]
                       [--config CONFIG]
                       video_path

Transcribe MOTD video audio using faster-whisper.

positional arguments:
  video_path            Path to MOTD video file

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT       Output JSON path (default: auto-generate in cache)
  --force               Force re-transcription even if cache exists
  --model-size SIZE     Whisper model size (default: large-v3)
  --config CONFIG       Path to config file (default: config/config.yaml)
```

**Example execution output:**
```bash
$ python -m motd transcribe data/videos/motd_2025-11-01.mp4

[INFO] Checking cache for existing transcript...
[INFO] No cached transcript found
[INFO] Extracting audio from video...
[INFO] Audio extraction complete: 54.2MB, 5400.2s
[INFO] Transcribing audio with Whisper (large-v3) on cuda...
[INFO] Transcription complete: 342 segments in 3m 24s
[INFO] Performance: 26.5x real-time
[INFO] Transcript saved to: data/cache/motd_2025-11-01/transcript.json

Summary:
  Video: data/videos/motd_2025-11-01.mp4
  Duration: 90m 0s
  Segments: 342
  Cache: data/cache/motd_2025-11-01/
  Processing time: 3m 24s
```

**Example cache hit (second run):**
```bash
$ python -m motd transcribe data/videos/motd_2025-11-01.mp4

[INFO] Checking cache for existing transcript...
[INFO] Cache hit! Using existing transcript at data/cache/motd_2025-11-01/transcript.json

Summary:
  Video: data/videos/motd_2025-11-01.mp4
  Duration: 90m 0s
  Segments: 342
  Cache: data/cache/motd_2025-11-01/
  Processing time: 0.2s (cached)
```

## Example Implementation Outline

```python
def transcribe_command(args):
    """Execute transcribe command with caching."""

    # 1. Load config
    config = load_config(args.config)

    # 2. Determine cache paths
    video_name = Path(args.video_path).stem
    cache_dir = Path(f"data/cache/{video_name}")
    audio_path = cache_dir / "audio.wav"
    transcript_path = cache_dir / "transcript.json"

    # 3. Check cache
    if transcript_path.exists() and not args.force:
        logger.info(f"Cache hit! Using existing transcript at {transcript_path}")
        with open(transcript_path) as f:
            result = json.load(f)
        return result

    # 4. Extract audio (if needed)
    if not audio_path.exists():
        logger.info("Extracting audio from video...")
        extractor = AudioExtractor(config)
        extractor.extract(args.video_path, audio_path)

    # 5. Transcribe
    logger.info(f"Transcribing audio with Whisper...")
    transcriber = WhisperTranscriber(config)
    result = transcriber.transcribe(audio_path)

    # 6. Save to cache
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(transcript_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Transcript saved to: {transcript_path}")
    return result
```

## Time Estimate
45-60 minutes

## Dependencies
- **Blocks:** 010e (need CLI to run transcription)
- **Blocked by:** 010b, 010c (need both modules working)

## Notes
- **Cache directory structure:** Mirrors Task 009 pattern (per-video folders)
- **Audio caching:** Keep audio.wav for debugging/re-processing with different models
- **Transcript format:** JSON for easy parsing by next pipeline stages
- **Force flag:** Useful for testing different models or after code changes
- **Model size flag:** Allow experimenting with smaller/faster models

## Troubleshooting
- **Cache not used:** Check if paths match exactly (filename case sensitivity)
- **Permission errors:** Ensure cache directory is writable
- **Large files:** WAV files are ~10MB/min, JSON is ~2-5MB for 90-min video

## Reference
- [docs/architecture.md - CLI Design](../../architecture.md)
- [Task 009d - CLI Integration](../../tasks/completed/009-ocr-implementation/009e-cli-integration.md) (similar pattern)

## Next Phase
[010e-execution.md](010e-execution.md) - Run transcription on full test video
