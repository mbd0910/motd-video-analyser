# Task 006: Implement Scene Detector

## Objective
Create the scene detection module using PySceneDetect to identify transitions in MOTD videos.

## Prerequisites
- [005-create-config-file.md](005-create-config-file.md) completed
- Virtual environment activated

## Steps

### 1. Create the detector module
```bash
cat > src/motd/scene_detection/detector.py << 'EOF'
"""
Scene detection using PySceneDetect.
Identifies transitions between segments (studio, highlights, interviews).
"""

from scenedetect import detect, ContentDetector, AdaptiveDetector
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def detect_scenes(
    video_path: str,
    threshold: float = 30.0,
    min_scene_duration: float = 3.0,
    detector_type: str = "content"
) -> List[Dict]:
    """
    Detect scene transitions in video.

    Args:
        video_path: Path to video file
        threshold: Scene detection sensitivity (lower = more sensitive)
        min_scene_duration: Minimum scene length in seconds
        detector_type: "content" or "adaptive"

    Returns:
        List of scenes with start/end timestamps and frame numbers
    """
    logger.info(f"Detecting scenes in {video_path}")
    logger.info(f"Parameters: threshold={threshold}, min_duration={min_scene_duration}")

    # Choose detector
    if detector_type == "adaptive":
        detector = AdaptiveDetector(
            adaptive_threshold=threshold,
            min_scene_len=min_scene_duration
        )
    else:
        detector = ContentDetector(
            threshold=threshold,
            min_scene_len=min_scene_duration
        )

    # Detect scenes
    try:
        scenes = detect(video_path, detector)
    except Exception as e:
        logger.error(f"Scene detection failed: {e}")
        raise

    # Format results
    results = []
    for i, (start, end) in enumerate(scenes):
        scene_data = {
            "scene_id": i + 1,
            "start_time": start.get_timecode(),
            "end_time": end.get_timecode(),
            "start_frame": start.get_frames(),
            "end_frame": end.get_frames(),
            "start_seconds": start.get_seconds(),
            "end_seconds": end.get_seconds(),
            "duration_seconds": (end - start).get_seconds()
        }
        results.append(scene_data)

    logger.info(f"Detected {len(results)} scenes")

    # Warn if unusual number of scenes
    if len(results) < 20:
        logger.warning("Very few scenes detected. Consider lowering threshold.")
    elif len(results) > 200:
        logger.warning("Very many scenes detected. Consider raising threshold.")

    return results


def get_total_frames(video_path: str) -> int:
    """Get total number of frames in video."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total_frames


def get_fps(video_path: str) -> float:
    """Get frames per second of video."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps
EOF
```

### 2. Test the module
```bash
python -c "
from src.motd.scene_detection.detector import detect_scenes
print('Module imported successfully')
"
```

## Validation Checklist
- [x] File created at `src/motd/scene_detection/detector.py`
- [x] Module imports without errors
- [x] No syntax errors

## Estimated Time
15-20 minutes

## Notes

### How Scene Detection Works
- **ContentDetector**: Compares frame-to-frame differences using histogram comparison
- **Threshold**: Higher values = less sensitive (fewer scenes), lower = more sensitive
- **Min Scene Duration**: Prevents very short scenes from being detected

### When to Use Adaptive vs Content
- **Content** (recommended): Good for clear cuts and transitions
- **Adaptive**: Better for gradual transitions (fades, dissolves)

For MOTD, **Content** detector works well as BBC uses mostly hard cuts.

## Next Task
[007-implement-frame-extractor.md](007-implement-frame-extractor.md)
