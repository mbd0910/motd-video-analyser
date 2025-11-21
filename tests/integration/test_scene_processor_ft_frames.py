"""
Integration tests for SceneProcessor with 8 ground truth FT frames.

Tests the refactored Scene

Processor class end-to-end with real FT graphic frames.
This is the definitive test - if these pass, all 8 FT frames will be detected.
"""

import pytest
from pathlib import Path
import yaml

from motd.pipeline.factory import ServiceFactory
from motd.pipeline.models import Scene


# Ground truth data for all 8 FT graphic frames
FT_GRAPHICS_GROUND_TRUTH = [
    {
        'frame': 'frame_0329_scene_change_607.3s.jpg',
        'scene_number': 329,
        'home': 'Liverpool',
        'away': 'Aston Villa',
        'timestamp': 607.3,
        'issue': 'OCR misses "Aston Villa" (non-bold text) - requires opponent inference',
    },
    {
        'frame': 'frame_0697_scene_change_1325.4s.jpg',
        'scene_number': 697,
        'home': 'Burnley',
        'away': 'Arsenal',
        'timestamp': 1325.4,
        'issue': None,  # Currently working
    },
    {
        'frame': 'frame_1116_scene_change_2123.1s.jpg',
        'scene_number': 1116,
        'home': 'Nottingham Forest',
        'away': 'Manchester United',
        'timestamp': 2123.1,
        'issue': None,  # Working after fixture validation fix
    },
    {
        'frame': 'frame_1117_scene_change_2124.2s.jpg',
        'scene_number': 1117,
        'home': 'Nottingham Forest',
        'away': 'Manchester United',
        'timestamp': 2124.2,
        'issue': 'Duplicate frame (1s after frame_1116)',
    },
    {
        'frame': 'frame_1503_interval_sampling_2884.0s.jpg',
        'scene_number': 1503,
        'home': 'Fulham',
        'away': 'Wolverhampton Wanderers',
        'timestamp': 2884.0,
        'issue': 'OCR detected but scene rejected - unknown reason',
    },
    {
        'frame': 'frame_1885_interval_sampling_3646.0s.jpg',
        'scene_number': 1885,
        'home': 'Tottenham Hotspur',
        'away': 'Chelsea',
        'timestamp': 3646.0,
        'issue': 'OCR detected but scene rejected - unknown reason',
    },
    {
        'frame': 'frame_2214_interval_sampling_4300.0s.jpg',
        'scene_number': 2214,
        'home': 'Brighton & Hove Albion',
        'away': 'Leeds United',
        'timestamp': 4300.0,
        'issue': 'OCR detected but scene rejected - unknown reason',
    },
    {
        'frame': 'frame_2494_interval_sampling_4842.0s.jpg',
        'scene_number': 2494,
        'home': 'Crystal Palace',
        'away': 'Brentford',
        'timestamp': 4842.0,
        'issue': None,  # Working after fixture ordering fix
    },
]


@pytest.fixture(scope="module")
def config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def service_factory(config):
    """Create ServiceFactory from config."""
    return ServiceFactory(config)


@pytest.fixture(scope="module")
def scene_processor(service_factory):
    """Create SceneProcessor for test episode."""
    episode_id = "motd_2025-26_2025-11-01"
    return service_factory.create_scene_processor(episode_id)


@pytest.fixture(scope="module")
def fixtures_dir():
    """Path to FT graphics test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "ft_graphics"


@pytest.mark.parametrize("ground_truth", FT_GRAPHICS_GROUND_TRUTH, ids=lambda gt: gt['frame'])
def test_scene_processor_detects_ft_graphic(ground_truth, scene_processor, fixtures_dir):
    """
    CRITICAL TEST: SceneProcessor must detect all 8 ground truth FT graphics.

    This is the definitive integration test. If this passes for all 8 frames,
    the refactoring is successful and FT detection works correctly.

    Tests:
    - SceneProcessor.process() does NOT return None
    - Detected teams match ground truth (home and away)
    - ProcessedScene contains correct metadata
    """
    frame_path = fixtures_dir / ground_truth['frame']
    assert frame_path.exists(), f"Test fixture missing: {frame_path}"

    # Create Scene model
    scene = Scene(
        scene_number=ground_truth['scene_number'],
        start_time=f"{int(ground_truth['timestamp'] // 60):02d}:{int(ground_truth['timestamp'] % 60):02d}",
        start_seconds=ground_truth['timestamp'],
        end_seconds=ground_truth['timestamp'] + 1.0,
        duration=1.0,
        frames=[str(frame_path)],
        key_frame_path=str(frame_path)
    )

    # Process scene
    result = scene_processor.process(scene)

    # CRITICAL ASSERTION: Must not return None
    assert result is not None, \
        f"SceneProcessor returned None for ground truth FT graphic {ground_truth['frame']}. "\
        f"Expected: {ground_truth['home']} vs {ground_truth['away']}. " \
        f"Known issue: {ground_truth['issue']}"

    # Verify teams detected (allow for order swap - will be fixed by fixture ordering)
    detected_teams = {result.team1, result.team2}
    expected_teams = {ground_truth['home'], ground_truth['away']}

    assert detected_teams == expected_teams, \
        f"Team mismatch for {ground_truth['frame']}: " \
        f"detected {detected_teams}, expected {expected_teams}"

    # Verify fixture ordering (home team first)
    if result.home_team and result.away_team:
        assert result.home_team == ground_truth['home'], \
            f"Home team mismatch: {result.home_team} != {ground_truth['home']}"
        assert result.away_team == ground_truth['away'], \
            f"Away team mismatch: {result.away_team} != {ground_truth['away']}"

    # Verify metadata
    assert result.scene_number == ground_truth['scene_number']
    assert result.ocr_source in ['ft_score', 'scoreboard', 'formation']
    assert 0.0 <= result.match_confidence <= 1.0

    # Log success
    print(f"\n✅ {ground_truth['frame']}: {result.team1} vs {result.team2} "
          f"(confidence: {result.match_confidence:.2f}, source: {result.ocr_source})")


def test_all_ft_graphics_detected(scene_processor, fixtures_dir):
    """
    Summary test: Verify all 8 FT graphics are detected.

    This test runs after the parametrized tests and provides a summary.
    """
    detection_count = 0
    failed_frames = []

    for gt in FT_GRAPHICS_GROUND_TRUTH:
        frame_path = fixtures_dir / gt['frame']
        scene = Scene(
            scene_number=gt['scene_number'],
            start_time=f"{int(gt['timestamp'] // 60):02d}:{int(gt['timestamp'] % 60):02d}",
            start_seconds=gt['timestamp'],
            end_seconds=gt['timestamp'] + 1.0,
            duration=1.0,
            frames=[str(frame_path)]
        )

        result = scene_processor.process(scene)
        if result:
            detection_count += 1
        else:
            failed_frames.append(gt['frame'])

    print(f"\n{'='*60}")
    print(f"FT GRAPHIC DETECTION SUMMARY")
    print(f"{'='*60}")
    print(f"Detected: {detection_count}/8 ({detection_count/8*100:.0f}%)")
    print(f"Failed: {len(failed_frames)}")

    if failed_frames:
        print(f"\nFailed frames:")
        for frame in failed_frames:
            print(f"  - {frame}")

    print(f"{'='*60}\n")

    # CRITICAL: Must detect all 8 frames
    assert detection_count == 8, \
        f"Only {detection_count}/8 FT graphics detected. Failed: {failed_frames}"


def test_multi_frame_scene_ft_detection(scene_processor):
    """
    TEST FOR BUG: FT graphics in frames[1+] should be detected (not just frames[0]).

    This test simulates the CLI behavior where Scene.frames contains multiple frames
    from hybrid extraction (scene change + interval sampling). The FT graphic might
    not be at frames[0], so SceneProcessor must iterate through all frames.

    Real-world example: frame_1503 (Fulham vs Wolves)
    - frames[0] = frame_1502_scene_change_2881.3s.jpg (NO FT graphic)
    - frames[1] = frame_1503_interval_sampling_2884.0s.jpg (HAS FT graphic) ← Should detect this!
    """
    # Multi-frame scene where FT graphic is at frames[1] (not frames[0])
    scene = Scene(
        scene_number=734,
        start_time="00:48:01",
        start_seconds=2881.3,
        end_seconds=2886.0,
        duration=4.7,
        frames=[
            "data/cache/motd_2025-26_2025-11-01/frames/frame_1502_scene_change_2881.3s.jpg",  # NO FT
            "data/cache/motd_2025-26_2025-11-01/frames/frame_1503_interval_sampling_2884.0s.jpg",  # FT HERE!
            "data/cache/motd_2025-26_2025-11-01/frames/frame_1504_interval_sampling_2886.0s.jpg"
        ]
    )

    result = scene_processor.process(scene)

    # CRITICAL: Must detect FT graphic even though it's in frames[1]
    assert result is not None, \
        "SceneProcessor failed to detect FT graphic at frames[1]. " \
        "Bug: SceneProcessor._extract_frame() only checks frames[0]"

    # Verify correct teams detected
    detected_teams = {result.team1, result.team2}
    expected_teams = {"Fulham", "Wolverhampton Wanderers"}

    assert detected_teams == expected_teams, \
        f"Team mismatch: detected {detected_teams}, expected {expected_teams}"

    assert result.ocr_source == "ft_score", \
        f"Expected FT graphic (ft_score), got {result.ocr_source}"

    print(f"\n✅ Multi-frame test passed: {result.team1} vs {result.team2} "
          f"detected from frames[1] (frame_1503)")


def test_ft_preferred_over_scoreboard(scene_processor):
    """
    TEST: FT graphics should be prioritized over scoreboards in multi-frame scenes.

    When a scene has BOTH scoreboard (frames[1]) and FT graphic (frames[4]),
    SceneProcessor should prefer the FT graphic for segment classification.

    Real-world scenario: Scene 1002 (Brighton vs Leeds)
    - frames[1] = frame_2211 (scoreboard detection)
    - frames[4] = frame_2214 (FT graphic) ← Should prefer this!

    Why: Segment classifier (Task 011c) needs FT graphics to detect match → post-match
    transitions. Scoreboards appear throughout match footage but don't mark boundaries.
    """
    # Scene 1002: Brighton vs Leeds with scoreboard before FT graphic
    scene = Scene(
        scene_number=1002,
        start_time="01:11:31",
        start_seconds=4291.52,
        end_seconds=4303.72,
        duration=12.2,
        frames=[
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2210_scene_change_4291.5s.jpg",  # Unknown
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2211_interval_sampling_4294.0s.jpg",  # SCOREBOARD
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2212_interval_sampling_4296.0s.jpg",
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2213_interval_sampling_4298.0s.jpg",
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2214_interval_sampling_4300.0s.jpg",  # FT GRAPHIC
            "data/cache/motd_2025-26_2025-11-01/frames/frame_2215_interval_sampling_4302.0s.jpg"
        ]
    )

    result = scene_processor.process(scene)

    # CRITICAL: Must detect FT graphic, not scoreboard
    assert result is not None, \
        "SceneProcessor failed to detect any teams in scene 1002"

    assert result.ocr_source == "ft_score", \
        f"Expected FT graphic (ft_score), got {result.ocr_source}. " \
        f"SceneProcessor stopped at scoreboard instead of continuing to FT graphic. " \
        f"This will break segment classification (Task 011c) which needs FT boundaries."

    # Verify it's the FT frame, not the scoreboard frame
    assert "frame_2214" in result.frame_path, \
        f"Expected frame_2214 (FT graphic), got {result.frame_path}. " \
        f"Detected from wrong frame."

    # Verify correct teams
    detected_teams = {result.team1, result.team2}
    expected_teams = {"Brighton & Hove Albion", "Leeds United"}

    assert detected_teams == expected_teams, \
        f"Team mismatch: detected {detected_teams}, expected {expected_teams}"

    print(f"\n✅ FT prioritization test passed: {result.team1} vs {result.team2} "
          f"detected from FT graphic (frame_2214) instead of earlier scoreboard (frame_2211)")
