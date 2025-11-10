# Task 008b: Test Scene Detection on Video

## Objective
Run the scene detection CLI on a test MOTD video to validate the implementation and generate initial results.

## Prerequisites
- [008a-create-cli-command.md](008a-create-cli-command.md) completed
- At least one MOTD video downloaded to `data/videos/`

## Steps

### 1. Prepare Test Environment
- Ensure you have a test video in `data/videos/`
- Create cache directory: `data/cache/test/`
- Verify video properties with ffprobe (resolution, duration, format)

### 2. Run Scene Detection
```bash
python -m motd detect-scenes data/videos/your_video.mp4 \
  --threshold 30.0 \
  --output data/cache/test/scenes.json
```

Expected processing time:
- 90-minute video: ~2-5 minutes depending on hardware
- Monitor console output for progress

### 3. Review Generated Files
Check that the following were created:
- `data/cache/test/scenes.json` - Scene metadata
- `data/cache/test/frames/scene_XXXX_frame_0.jpg` - Extracted frames

### 4. Initial Spot Check
Open scenes.json and verify:
- Total scene count is in reasonable range (expect 40-80 for 90-min MOTD)
- Scene timestamps look sequential and logical
- Frame paths are correct

Quick visual check:
- Open 5-10 random frames from `data/cache/test/frames/`
- Verify they show different segments (studio, highlights, etc.)

## Validation Checklist
- [x] CLI command ran without errors
- [x] scenes.json generated successfully
- [x] Key frames extracted to frames/ directory
- [x] Scene count is reasonable (not 5, not 500)
- [x] Timestamps are sequential
- [x] Visual spot-check shows variety of scenes

## Expected Results
For a typical 90-minute MOTD episode:
- Scene count: 40-80 scenes
- Too few (<20): Scenes are being missed
- Too many (>200): Detecting too many small transitions

## Troubleshooting
- **No scenes detected**: Video might be corrupted or threshold too high
- **Thousands of scenes**: Threshold too low, try increasing to 35-40
- **Missing frames**: Check disk space and permissions

## Estimated Time
15-30 minutes (including processing time)

## Next Subtask
[008c-validate-and-tune.md](008c-validate-and-tune.md)
