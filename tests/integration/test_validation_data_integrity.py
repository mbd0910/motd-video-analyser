"""
Integration tests for overall data integrity validation (Task 011b-2).

Tests high-level metrics to ensure data quality meets expectations:
- Frame extraction counts
- FT graphic vs scoreboard ratio
- Scene structure consistency
"""

import json
from pathlib import Path


def load_scenes(episode_id):
    """Load scenes from cache."""
    cache_dir = Path("data/cache") / episode_id
    scenes_path = cache_dir / "scenes.json"

    with open(scenes_path) as f:
        data = json.load(f)

    return data["scenes"]


def load_ocr_results(episode_id):
    """Load OCR results from cache."""
    cache_dir = Path("data/cache") / episode_id
    ocr_results_path = cache_dir / "ocr_results.json"

    with open(ocr_results_path) as f:
        data = json.load(f)

    return data["ocr_results"]


def test_ft_graphic_count():
    """
    Test that expected number of FT graphics were detected.

    Target: 7-15 FT graphics (one per match, plus potential duplicates).
    Current data: 8 FT graphics detected (100% ground truth coverage).
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    ft_count = sum(1 for r in ocr_results if r["ocr_source"] == "ft_score")

    assert 7 <= ft_count <= 15, \
        f"FT graphic count: {ft_count} (expected 7-15)"


def test_scoreboard_count():
    """
    Test that expected number of scoreboards were detected.

    Target: 350-600 scoreboards across 7 matches (~50-85 per match).
    Scoreboards appear throughout match highlights at 2s intervals.
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    scoreboard_count = sum(1 for r in ocr_results if r["ocr_source"] == "scoreboard")

    assert 350 <= scoreboard_count <= 600, \
        f"Scoreboard count: {scoreboard_count} (expected 350-600)"


def test_total_ocr_detections():
    """
    Test that total OCR detections are within expected range.

    Total should be FT + scoreboards, roughly 360-610 detections.
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    total_count = len(ocr_results)

    assert 360 <= total_count <= 610, \
        f"Total OCR detections: {total_count} (expected 360-610)"


def test_frame_extraction_count():
    """
    Test that adequate frames were extracted from video.

    With 2s interval sampling + scene changes, we expect ~2,500 frames
    for an 84-minute episode (versus ~1,450 with 5s intervals).

    Current data: 2,599 frames (78% increase from original 1,459).
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    # Count unique frames across all scenes
    all_frames = set()
    for scene in scenes:
        for frame in scene.get("frames", []):
            all_frames.add(frame)

    frame_count = len(all_frames)

    # Target: 2,400-2,800 frames (±200 from expected ~2,600)
    assert 2400 <= frame_count <= 2800, \
        f"Frame extraction count: {frame_count} (expected 2400-2800)"


def test_scenes_count():
    """
    Test that expected number of scenes were detected.

    PySceneDetect should find ~1,200-1,300 scenes for an 84-minute
    episode with typical MOTD editing (quick cuts, replays, etc.).
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    scene_count = len(scenes)

    assert 1100 <= scene_count <= 1400, \
        f"Scene count: {scene_count} (expected 1100-1400)"


def test_multi_frame_scene_ratio():
    """
    Test that adequate proportion of scenes have multiple frames.

    With 2s interval sampling, scenes longer than 2s should have
    multiple frames. We expect at least 25% of scenes to have >1 frame.

    Current data: 355/1229 scenes (28.9%) have >1 frame.
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")

    total_scenes = len(scenes)
    multi_frame_scenes = sum(1 for s in scenes if len(s.get("frames", [])) > 1)

    multi_frame_ratio = (multi_frame_scenes / total_scenes) * 100

    assert multi_frame_ratio >= 25, \
        f"Multi-frame scene ratio: {multi_frame_ratio:.1f}% (expected >= 25%)"


def test_data_integrity_summary():
    """
    Summary test: report overall data quality metrics.

    Provides comprehensive overview of data integrity across all
    validation dimensions.
    """
    scenes = load_scenes("motd_2025-26_2025-11-01")
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    # Calculate metrics
    total_scenes = len(scenes)
    all_frames = set()
    for scene in scenes:
        for frame in scene.get("frames", []):
            all_frames.add(frame)
    total_frames = len(all_frames)

    multi_frame_scenes = sum(1 for s in scenes if len(s.get("frames", [])) > 1)
    multi_frame_pct = (multi_frame_scenes / total_scenes) * 100

    ft_count = sum(1 for r in ocr_results if r["ocr_source"] == "ft_score")
    scoreboard_count = sum(1 for r in ocr_results if r["ocr_source"] == "scoreboard")
    total_ocr = len(ocr_results)

    # Build summary message
    summary = f"""
    Data Integrity Summary for motd_2025-26_2025-11-01:

    Scene Detection:
      - Total scenes: {total_scenes}
      - Multi-frame scenes: {multi_frame_scenes} ({multi_frame_pct:.1f}%)

    Frame Extraction:
      - Total frames: {total_frames}
      - Avg frames/scene: {total_frames/total_scenes:.1f}

    OCR Detection:
      - FT graphics: {ft_count}
      - Scoreboards: {scoreboard_count}
      - Total detections: {total_ocr}
      - FT ratio: {(ft_count/total_ocr)*100:.1f}%
    """

    # All metrics should be within expected ranges (validated by individual tests)
    # This summary test just reports for visibility
    print(summary)

    # Assert overall quality
    assert total_scenes >= 1100, "Scene count below minimum"
    assert total_frames >= 2400, "Frame count below minimum"
    assert ft_count >= 7, "FT graphic count below minimum"
    assert scoreboard_count >= 350, "Scoreboard count below minimum"
    assert multi_frame_pct >= 25, "Multi-frame scene ratio below minimum"
