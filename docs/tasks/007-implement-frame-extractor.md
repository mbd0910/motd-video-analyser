# Task 007: Implement Frame Extractor

## Objective
Create a module to extract key frames at scene transitions for OCR processing.

## Prerequisites
- [006-implement-scene-detector.md](006-implement-scene-detector.md) completed

## Steps

### 1. Create the frame extractor module
```bash
cat > src/motd/scene_detection/frame_extractor.py << 'EOF'
"""
Extract key frames from video at scene transitions.
These frames will be used for OCR to identify team names.
"""

import cv2
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def extract_key_frame(
    video_path: str,
    timestamp_seconds: float,
    output_path: str
) -> bool:
    """
    Extract a single frame at given timestamp.

    Args:
        video_path: Path to video file
        timestamp_seconds: Timestamp in seconds
        output_path: Where to save the frame image

    Returns:
        True if successful, False otherwise
    """
    cap = cv2.VideoCapture(video_path)

    # Seek to timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)

    # Read frame
    ret, frame = cap.read()

    if ret:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save frame as JPEG
        cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logger.debug(f"Extracted frame to {output_path}")
    else:
        logger.warning(f"Failed to extract frame at {timestamp_seconds}s")

    cap.release()
    return ret


def extract_key_frames_for_scenes(
    video_path: str,
    scenes: List[Dict],
    output_dir: str,
    extract_position: str = "start"
) -> None:
    """
    Extract key frame for each scene.

    Args:
        video_path: Path to video file
        scenes: List of scene dictionaries from detect_scenes()
        output_dir: Directory to save frames
        extract_position: "start", "middle", or "end" of scene
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Extracting key frames to {output_dir}")

    for scene in scenes:
        scene_id = scene['scene_id']
        frame_path = os.path.join(output_dir, f"scene_{scene_id:03d}.jpg")

        # Determine timestamp to extract
        if extract_position == "middle":
            timestamp = (scene['start_seconds'] + scene['end_seconds']) / 2
        elif extract_position == "end":
            timestamp = scene['end_seconds']
        else:  # start
            timestamp = scene['start_seconds']

        # Extract frame
        success = extract_key_frame(video_path, timestamp, frame_path)

        if success:
            scene['key_frame_path'] = frame_path
        else:
            logger.error(f"Failed to extract frame for scene {scene_id}")
            scene['key_frame_path'] = None

    logger.info(f"Extracted {len([s for s in scenes if s.get('key_frame_path')])} key frames")


def extract_multiple_frames_per_scene(
    video_path: str,
    scene: Dict,
    output_dir: str,
    num_frames: int = 3
) -> List[str]:
    """
    Extract multiple frames from a scene (e.g., start, middle, end).
    Useful if scoreboard appears/disappears during scene.

    Args:
        video_path: Path to video file
        scene: Single scene dictionary
        output_dir: Directory to save frames
        num_frames: Number of frames to extract

    Returns:
        List of frame paths
    """
    os.makedirs(output_dir, exist_ok=True)
    frame_paths = []

    scene_id = scene['scene_id']
    duration = scene['end_seconds'] - scene['start_seconds']

    for i in range(num_frames):
        # Distribute frames evenly across scene
        offset = (i / (num_frames - 1)) if num_frames > 1 else 0
        timestamp = scene['start_seconds'] + (duration * offset)

        frame_path = os.path.join(
            output_dir,
            f"scene_{scene_id:03d}_frame_{i+1}.jpg"
        )

        success = extract_key_frame(video_path, timestamp, frame_path)
        if success:
            frame_paths.append(frame_path)

    return frame_paths
EOF
```

### 2. Test the module
```bash
python -c "
from src.motd.scene_detection.frame_extractor import extract_key_frame
print('Module imported successfully')
"
```

## Validation Checklist
- [x] File created at `src/motd/scene_detection/frame_extractor.py`
- [x] Module imports without errors
- [x] No syntax errors

## Estimated Time
15-20 minutes

## Notes

### Extract Position Strategy
- **Start**: Good for detecting match start (scoreboard appears)
- **Middle**: More stable, scoreboard likely visible throughout
- **End**: Good for detecting match end

For MOTD, **start** or **middle** works well as scoreboards are usually visible early in match highlights.

### Multiple Frames Per Scene
The `extract_multiple_frames_per_scene()` function is useful if:
- Scoreboard appears mid-scene
- You want higher confidence in team detection
- OCR fails on one frame but succeeds on another

We'll keep it simple initially (single frame per scene) and can enhance later if needed.

## Next Task
[008-create-scene-detection-cli.md](008-create-scene-detection-cli.md)
