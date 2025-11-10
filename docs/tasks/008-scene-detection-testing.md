# Task 008: Create Scene Detection CLI & Test

## Objective
Create a CLI command for scene detection and run it on your first MOTD video to validate the approach.

## Prerequisites
- [007-implement-frame-extractor.md](007-implement-frame-extractor.md) completed
- At least one MOTD video downloaded to `data/videos/`

## Epic Overview
This task combines CLI creation and testing into one epic. Before starting, you may want to split this into smaller tasks:
1. Create the CLI command structure
2. Wire up the scene detector and frame extractor
3. Run on test video
4. Manually validate results
5. Tune parameters if needed

## High-Level Steps

### 1. Create CLI Entry Point
Add scene detection command to `src/motd_analyzer/__main__.py`:
- Accept video path as argument
- Accept threshold and other config parameters
- Call detector and frame extractor
- **Note**: Start with single-frame extraction (`num_frames=1`). The frame extractor supports 1-3 frames per scene (see Task 007, lines 107-146) for cases where scoreboard appears mid-scene, but this adds complexity. Only add multi-frame support to CLI if initial OCR accuracy is <90% in Task 009.
- Save results to JSON

### 2. Test on First Video
```bash
python -m motd_analyzer detect-scenes data/videos/your_video.mp4 \
  --threshold 30.0 \
  --output data/cache/test/scenes.json
```

### 3. Manual Validation
- Open the generated JSON file
- Look at the extracted frames in `data/cache/test/frames/`
- Check: Do the detected scenes match actual transitions?
- Typical MOTD video should have 40-80 scenes

### 4. Tune If Needed
If results aren't good:
- Too few scenes (<20)? Lower threshold (try 20)
- Too many scenes (>200)? Raise threshold (try 40)
- Update `config/config.yaml` with best threshold

## Validation Checklist
- [ ] CLI command works
- [ ] Scenes JSON generated with timestamps
- [ ] Key frames extracted successfully
- [ ] Scene count looks reasonable (40-80 for 90-min video)
- [ ] Spot-checked scenes match actual transitions
- [ ] Frame extraction using single frame per scene (multi-frame support deferred to refinement if needed)

## Estimated Time
1-2 hours (including waiting for processing and manual review)

## Reference
See [roadmap.md Phase 1](../roadmap.md#phase-1-scene-detection-est-4-6-hours) for detailed implementation examples.

## Next Task
[009-ocr-implementation-epic.md](009-ocr-implementation-epic.md)
