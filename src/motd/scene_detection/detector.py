"""
Scene detection using PySceneDetect.
Identifies transitions between segments (studio, highlights, interviews).
"""

from scenedetect import detect, ContentDetector, AdaptiveDetector
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Monkey-patch PySceneDetect to fix NumPy 2.x compatibility
# Workaround for PySceneDetect 0.6.x with NumPy 2.x
# Issue: _frame_buffer_size is stored as float, needs to be int for numpy slicing
try:
    from packaging import version
    import scenedetect
    import numpy as np

    # Only patch if using affected versions (PySceneDetect 0.6.x with NumPy 2.x)
    pyscenedetect_version = version.parse(scenedetect.__version__)
    numpy_version = version.parse(np.__version__)

    if pyscenedetect_version.major == 0 and pyscenedetect_version.minor == 6 and numpy_version.major >= 2:
        import scenedetect.scene_manager
        original_process_frame = scenedetect.scene_manager.SceneManager._process_frame

        def patched_process_frame(self, *args, **kwargs):
            # Ensure _frame_buffer_size is an integer before processing
            if hasattr(self, '_frame_buffer_size'):
                self._frame_buffer_size = int(self._frame_buffer_size)
            return original_process_frame(self, *args, **kwargs)

        scenedetect.scene_manager.SceneManager._process_frame = patched_process_frame
        logger.debug(f"Applied NumPy 2.x compatibility patch for PySceneDetect {scenedetect.__version__}")
    else:
        logger.debug(f"NumPy compatibility patch not needed (PySceneDetect {scenedetect.__version__}, NumPy {np.__version__})")

except Exception as e:
    logger.warning(f"Failed to apply PySceneDetect compatibility patch: {e}. Scene detection may fail with NumPy 2.x.")


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
    # Note: Empirical testing shows threshold 20.0 produces ~1200 scenes for 84-min video
    # These warnings indicate likely configuration issues, not normal high scene counts
    if len(results) < 20:
        logger.warning("Very few scenes detected (<20). Consider lowering threshold.")
    elif len(results) > 2000:
        logger.warning("Very many scenes detected (>2000). Consider raising threshold or checking video quality.")

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
