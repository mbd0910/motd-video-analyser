"""
Integration tests for frame coverage validation (Task 011b-2).

Tests that long scenes have adequate frame coverage (5+ frames) and
that frames span the scene duration correctly (not bunched at start).

Validates the fix for the serialization bug where only 1 frame per
scene was saved in scenes.json.
"""

import json
import pytest
import re
from pathlib import Path


def load_scenes(episode_id):
    """Load scenes from cache."""
    cache_dir = Path("data/cache") / episode_id
    scenes_path = cache_dir / "scenes.json"

    with open(scenes_path) as f:
        data = json.load(f)

    return data["scenes"]


def extract_timestamp_from_filename(frame_path):
    """
    Extract timestamp in seconds from frame filename.

    Examples:
        frame_0075_interval_sampling_120.0s.jpg → 120.0
        frame_0329_scene_change_607.3s.jpg → 607.3
    """
    match = re.search(r'_(\d+\.\d+)s\.jpg$', str(frame_path))
    if match:
        return float(match.group(1))

    # Fallback: try without decimal
    match = re.search(r'_(\d+)s\.jpg$', str(frame_path))
    if match:
        return float(match.group(1))

    raise ValueError(f"Could not extract timestamp from: {frame_path}")


@pytest.fixture
def ground_truth_scenes():
    """Load ground truth scene IDs for frame coverage testing."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_path = fixtures_dir / "ground_truth_validation.json"

    with open(ground_truth_path) as f:
        data = json.load(f)

    return data["frame_coverage_scenes"]


@pytest.mark.parametrize("scene_data", [
    pytest.param(scene, id=f"scene_{scene['scene_id']}_{scene['position_in_episode']}")
    for scene in json.load(open(Path(__file__).parent.parent / "fixtures" / "ground_truth_validation.json"))["frame_coverage_scenes"]
])
def test_long_scene_has_good_frame_coverage(scene_data):
    """
    Test that long scenes (>15s) have adequate frame coverage.

    Validates:
    - Scene has at least 5 frames
    - Frames span at least 80% of scene duration (not bunched at start)
    - Frames are distributed across scene (validates 2s interval sampling)
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    # Find the scene
    scene = next((s for s in scenes if s["scene_id"] == scene_data["scene_id"]), None)

    assert scene is not None, f"Scene {scene_data['scene_id']} not found in scenes.json"

    # Assert minimum frame count
    num_frames = len(scene.get("frames", []))
    expected_min_frames = scene_data["expect_min_frames"]

    assert num_frames >= expected_min_frames, \
        f"Scene {scene_data['scene_id']} has {num_frames} frames (expected >= {expected_min_frames})"

    # Assert frames span duration (not bunched at start)
    if num_frames >= 2:
        frame_times = [extract_timestamp_from_filename(f) for f in scene["frames"]]

        # Calculate time span covered by frames
        time_span = max(frame_times) - min(frame_times)

        # Expected span should be at least 80% of scene duration
        expected_span = scene["duration"] * scene_data["expect_time_span_pct"]

        assert time_span >= expected_span, \
            f"Scene {scene_data['scene_id']}: frames span {time_span:.1f}s " \
            f"(expected >= {expected_span:.1f}s for {scene['duration']}s scene)"


def test_multi_frame_scene_count():
    """
    Test that adequate number of scenes have multiple frames.

    After fixing the serialization bug, we expect 300+ scenes to have
    more than 1 frame (scenes with duration >2s and interval sampling).

    Current data shows 355/1229 scenes (28.9%) have >1 frame.
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    multi_frame_count = sum(1 for s in scenes if len(s.get("frames", [])) > 1)

    # Target: at least 300 scenes with multiple frames
    assert multi_frame_count >= 300, \
        f"Only {multi_frame_count} scenes have >1 frame (expected >= 300)"


def test_frame_coverage_summary(ground_truth_scenes):
    """
    Summary test: report frame coverage statistics for all test scenes.

    Provides overview of frame distribution quality across episode.
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    coverage_stats = []

    for scene_data in ground_truth_scenes:
        scene = next((s for s in scenes if s["scene_id"] == scene_data["scene_id"]), None)

        if scene:
            num_frames = len(scene.get("frames", []))

            if num_frames >= 2:
                frame_times = [extract_timestamp_from_filename(f) for f in scene["frames"]]
                time_span = max(frame_times) - min(frame_times)
                coverage_pct = (time_span / scene["duration"]) * 100
            else:
                time_span = 0
                coverage_pct = 0

            coverage_stats.append({
                "scene_id": scene_data["scene_id"],
                "duration": scene["duration"],
                "num_frames": num_frames,
                "time_span": time_span,
                "coverage_pct": coverage_pct
            })

    # All scenes should have good coverage (>=80%)
    poor_coverage = [s for s in coverage_stats if s["coverage_pct"] < 80]

    assert len(poor_coverage) == 0, \
        f"{len(poor_coverage)} scenes have poor coverage (<80%):\n" + \
        "\n".join([f"  - Scene {s['scene_id']}: {s['coverage_pct']:.1f}% ({s['num_frames']} frames, {s['time_span']:.1f}s span)"
                   for s in poor_coverage])
