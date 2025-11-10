"""
Scene detection using PySceneDetect.
Identifies transitions between segments (studio, highlights, interviews).
"""

from scenedetect import detect, ContentDetector, AdaptiveDetector
from typing import Any
import logging

# Monkey-patch PySceneDetect to fix NumPy 2.x compatibility
# Issue: _frame_buffer_size is stored as float, needs to be int for numpy slicing
import scenedetect.scene_manager
original_process_frame = scenedetect.scene_manager.SceneManager._process_frame

def patched_process_frame(self, *args, **kwargs):
    # Ensure _frame_buffer_size is an integer before processing
    if hasattr(self, '_frame_buffer_size'):
        self._frame_buffer_size = int(self._frame_buffer_size)
    return original_process_frame(self, *args, **kwargs)

scenedetect.scene_manager.SceneManager._process_frame = patched_process_frame

logger = logging.getLogger(__name__)


def detect_scenes(
    video_path: str,
    threshold: float = 30.0,
    min_scene_duration: float = 3.0,
    detector_type: str = "content"
) -> list[dict[str, Any]]:
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
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return total_frames
    finally:
        cap.release()


def get_fps(video_path: str) -> float:
    """Get frames per second of video."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        return fps
    finally:
        cap.release()
