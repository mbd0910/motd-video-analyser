# Task 008a: Create Scene Detection CLI Command

## Objective
Implement CLI entry point for scene detection that accepts video input and outputs scene data with extracted frames.

## Prerequisites
- [007-implement-frame-extractor.md](../completed/007-implement-frame-extractor/README.md) completed
- Scene detector and frame extractor modules implemented

## Steps

### 1. Create CLI Module Structure
Update `src/motd/__main__.py` to add the `detect-scenes` command:
- Use argparse or Click for CLI argument parsing
- Accept video path as required argument
- Accept optional parameters: threshold, output path, cache directory
- Set up logging for CLI operations

### 2. Wire Up Scene Detector
- Import and initialize the scene detector
- Pass threshold from CLI arguments (default from config if not provided)
- Call detector with video path
- Handle errors gracefully

### 3. Wire Up Frame Extractor
- Import and initialize the frame extractor
- Extract single frame per scene (num_frames=1)
- Save frames to cache directory with naming convention: `scene_{index:04d}_frame_0.jpg`
- Handle file I/O errors

### 4. Generate Output JSON
Save scene data to JSON with structure:
```json
{
  "video_path": "path/to/video.mp4",
  "threshold": 30.0,
  "total_scenes": 42,
  "scenes": [
    {
      "scene_index": 0,
      "start_time": 0.0,
      "end_time": 12.5,
      "duration": 12.5,
      "frames": ["scene_0000_frame_0.jpg"]
    }
  ]
}
```

### 5. Test CLI Works
```bash
python -m motd detect-scenes --help
# Should show usage information
```

## Validation Checklist
- [x] CLI command registered and accessible
- [x] Help text displays correctly
- [x] Required and optional arguments work
- [x] Error handling for missing video file
- [x] Logging output is clear and informative

## Estimated Time
30-45 minutes

## Next Subtask
[008b-test-on-video.md](008b-test-on-video.md)
