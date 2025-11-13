# Task 010e: Execute Transcription on Test Video

## Status
⏳ Not Started

## Objective
Run the complete transcription pipeline on the full test video and verify the output is correct, complete, and usable for downstream analysis.

## Prerequisites
- Task 010d (CLI Integration) completed
- `transcribe` command working and tested on short samples
- Test video available (same video used in Task 009)

## Why This Phase Matters
This is the **proof of concept** - does our transcription pipeline actually work on a real 90-minute MOTD video?

Key questions to answer:
- Does processing complete without errors?
- Is processing time acceptable (3-15 min)?
- Is the output well-formed and complete?
- Are team names and pundit names transcribed correctly?
- Are timestamps accurate?

This phase validates the pipeline before formal accuracy testing in 010f.

## Tasks

### 1. Preparation
- [ ] Identify test video path (same as Task 009)
- [ ] Verify video file is accessible
- [ ] Verify sufficient disk space:
  - Audio: ~55MB for 90-min video
  - Transcript: ~2-5MB JSON
  - Total: ~60MB free space recommended
- [ ] Clear any existing cache (to test fresh run):
  ```bash
  rm -rf data/cache/motd_2025-11-01/transcript.json
  rm -rf data/cache/motd_2025-11-01/audio.wav
  ```

### 2. First Run - Full Pipeline
- [ ] Run transcribe command:
  ```bash
  python -m motd transcribe data/videos/motd_2025-11-01.mp4
  ```
- [ ] Monitor console output for:
  - Audio extraction progress
  - Model loading (first time = download)
  - Transcription progress
  - Processing time
  - Any warnings or errors
- [ ] Note processing time (target: 3-15 min depending on GPU/CPU)
- [ ] Note GPU/CPU usage (if monitoring available)

### 3. Verify Output Files Created
- [ ] Check cache directory exists:
  ```bash
  ls -lh data/cache/motd_2025-11-01/
  ```
- [ ] Verify audio.wav created (~55MB for 90-min video)
- [ ] Verify transcript.json created (~2-5MB)
- [ ] Check file sizes are reasonable

### 4. Inspect Transcript Structure
- [ ] Open transcript.json in editor
- [ ] Verify JSON is valid (proper formatting)
- [ ] Check top-level fields present:
  - video_path
  - processed_at
  - model_size
  - device
  - language
  - duration_seconds
  - segment_count
  - segments array
- [ ] Check segment count is reasonable (expected: 200-500 segments)
- [ ] Check duration matches video duration (~5400 seconds)

### 5. Spot-Check Transcript Content
- [ ] Read first 5 segments - do they make sense?
- [ ] Read last 5 segments - do they make sense?
- [ ] Read 5 random middle segments - do they make sense?
- [ ] Look for obvious errors:
  - Gibberish text
  - Corrupted words
  - Missing segments (large time gaps)
- [ ] Verify word-level timestamps present in segments

### 6. Test Cache Hit (Second Run)
- [ ] Run same command again:
  ```bash
  python -m motd transcribe data/videos/motd_2025-11-01.mp4
  ```
- [ ] Verify "Cache hit!" message appears
- [ ] Verify processing time is instant (<1 second)
- [ ] Verify same transcript returned

### 7. Test Force Re-transcription
- [ ] Run with --force flag:
  ```bash
  python -m motd transcribe data/videos/motd_2025-11-01.mp4 --force
  ```
- [ ] Verify re-transcription occurs (no cache hit message)
- [ ] Verify processing time is same as first run
- [ ] Verify transcript is regenerated

### 8. Document Performance Metrics
- [ ] Record in execution notes:
  - Processing time (first run)
  - Real-time factor (e.g., 26x = 90 min video in 3.5 min)
  - Device used (GPU model or CPU)
  - Model size used (large-v3)
  - Segment count
  - Output file sizes
  - Cache hit time (second run)

### 9. Create Execution Report
- [ ] Create `docs/validation/010e_execution_report.md`
- [ ] Include:
  - Test video details
  - Processing time and performance
  - Output file information
  - Spot-check observations
  - Any issues or warnings encountered
  - Recommendation (proceed to validation or investigate issues)

## Validation Checklist

Before marking this task complete, verify:

- ✅ Command runs without crashes
- ✅ Audio extracted successfully
- ✅ Transcription completed successfully
- ✅ Processing time acceptable (3-15 min)
- ✅ Output files created in cache directory
- ✅ transcript.json is valid JSON
- ✅ Segment count is reasonable (200-500)
- ✅ Duration matches video duration
- ✅ Spot-check shows sensible content (no gibberish)
- ✅ Word-level timestamps present
- ✅ Cache hit works on second run (instant)
- ✅ Force flag bypasses cache
- ✅ Execution report documented

## Expected Output

**Files created:**
- `data/cache/motd_2025-11-01/audio.wav` (~55MB)
- `data/cache/motd_2025-11-01/transcript.json` (~2-5MB)
- `docs/validation/010e_execution_report.md`

**Example execution report:**
```markdown
# Transcription Execution Report - Task 010e

**Date:** 2025-11-13
**Test Video:** data/videos/motd_2025-11-01.mp4
**Duration:** 90 minutes (5400 seconds)

## Performance Metrics

- **Device:** NVIDIA RTX 3080 (GPU)
- **Model:** large-v3
- **Processing Time:** 3m 42s (first run)
- **Real-Time Factor:** 24.3x (90 min processed in 3.7 min)
- **Cache Hit Time:** 0.3s (second run)

## Output Files

- **Audio:** 54.8 MB (data/cache/motd_2025-11-01/audio.wav)
- **Transcript:** 3.2 MB (data/cache/motd_2025-11-01/transcript.json)
- **Segments:** 387 segments

## Spot-Check Observations

✅ First 5 segments: Match expected MOTD intro
✅ Last 5 segments: Match expected MOTD outro
✅ Random middle segments: Coherent match commentary
✅ Word timestamps: Present and appear accurate
✅ Team names: Visible in transcript (spot-checked)
✅ JSON structure: Valid and complete

## Issues/Warnings

None encountered. Pipeline executed smoothly.

## Recommendation

✅ Proceed to Task 010f (Validation) - output looks good for formal accuracy testing.
```

## Time Estimate
15-20 minutes (active work) + 3-15 minutes (processing time)

**Total:** ~20-35 minutes depending on GPU/CPU

## Dependencies
- **Blocks:** 010f (need transcript to validate)
- **Blocked by:** 010d (need working CLI command)

## Notes
- **First run is slowest:** Model download (~3GB) happens once
- **Subsequent runs instant:** Caching makes iteration fast
- **GPU vs CPU:** GPU = 3-4 min, CPU = 15-20 min (both acceptable)
- **File sizes:** WAV is large (~10MB/min), JSON is manageable (~2-5MB)
- **Memory usage:** Peak ~4GB GPU VRAM or ~8GB system RAM
- **Don't commit large files:** Audio/transcript in .gitignore

## Troubleshooting

### Processing Takes Too Long (>30 min)
- Check if GPU is being used: look for "cuda" in logs
- Try smaller model: `--model-size medium`
- Check system resources: close other GPU-heavy apps

### Out of Memory Error
- Try smaller model: `--model-size medium` or `large-v2`
- Use CPU instead: Update config device to "cpu"
- Close other applications

### Transcript Has Time Gaps
- Not necessarily a problem - could be silence periods
- Check corresponding video timestamps
- Document for validation phase (010f)

### JSON Parse Error
- Check transcript.json for corruption
- Re-run with --force flag
- Check disk space

## Reference
- [Task 009f - Execution](../../tasks/completed/009-ocr-implementation/009f-execution.md) (similar pattern)
- [docs/architecture.md - Caching Strategy](../../architecture.md)

## Next Phase
[010f-validation.md](010f-validation.md) - Manually validate transcription accuracy
