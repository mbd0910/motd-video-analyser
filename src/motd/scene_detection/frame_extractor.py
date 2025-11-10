"""
Extract key frames from video at scene transitions.
These frames will be used for OCR to identify team names.
"""

import cv2
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)


def extract_key_frame(
    video_path: Path | str,
    timestamp_seconds: float,
    output_path: Path | str
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
    # Convert to Path objects
    video_path = Path(video_path)
    output_path = Path(output_path)

    cap = cv2.VideoCapture(str(video_path))
    try:
        # Seek to timestamp
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)

        # Read frame
        ret, frame = cap.read()

        if ret:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save frame as JPEG
            cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            logger.debug(f"Extracted frame to {output_path}")
        else:
            logger.warning(f"Failed to extract frame at {timestamp_seconds}s")

        return ret
    finally:
        cap.release()


def extract_key_frames_for_scenes(
    video_path: Path | str,
    scenes: list[dict[str, Any]],
    output_dir: Path | str,
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
    # Convert to Path objects
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting key frames to {output_dir}")

    for scene in scenes:
        scene_id = scene['scene_id']
        frame_path = output_dir / f"scene_{scene_id:03d}.jpg"

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
            scene['key_frame_path'] = str(frame_path)
        else:
            logger.error(f"Failed to extract frame for scene {scene_id}")
            scene['key_frame_path'] = None

    logger.info(f"Extracted {len([s for s in scenes if s.get('key_frame_path')])} key frames")


def extract_multiple_frames_per_scene(
    video_path: Path | str,
    scene: dict[str, Any],
    output_dir: Path | str,
    num_frames: int = 3
) -> list[str]:
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
    # Convert to Path objects
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []

    scene_id = scene['scene_id']
    duration = scene['end_seconds'] - scene['start_seconds']

    for i in range(num_frames):
        # Distribute frames evenly across scene
        offset = (i / (num_frames - 1)) if num_frames > 1 else 0
        timestamp = scene['start_seconds'] + (duration * offset)

        frame_path = output_dir / f"scene_{scene_id:03d}_frame_{i+1}.jpg"

        success = extract_key_frame(video_path, timestamp, frame_path)
        if success:
            frame_paths.append(str(frame_path))

    return frame_paths
