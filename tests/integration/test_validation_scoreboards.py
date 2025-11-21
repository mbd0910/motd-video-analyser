"""
Integration tests for scoreboard detection validation (Task 011b-2).

Tests user-approved perfect scoreboard examples to ensure OCR pipeline
detects teams correctly with high confidence across all 7 matches.
"""

import json
import pytest
import yaml
from pathlib import Path

from motd.pipeline.factory import ServiceFactory
from motd.pipeline.models import Scene


@pytest.fixture
def ground_truth_scoreboards():
    """Load user-approved scoreboard ground truth examples."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_path = fixtures_dir / "ground_truth_validation.json"

    with open(ground_truth_path) as f:
        data = json.load(f)

    return data["scoreboards"]


@pytest.fixture(scope="module")
def config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def service_factory(config):
    """Create ServiceFactory for creating pipeline components."""
    return ServiceFactory(config)


@pytest.fixture(scope="module")
def scene_processor(service_factory):
    """Create SceneProcessor for episode."""
    return service_factory.create_scene_processor("motd_2025-26_2025-11-01")


@pytest.mark.parametrize("ground_truth", [
    pytest.param(gt, id=gt["fixture_file"].replace(".jpg", ""))
    for gt in json.load(open(Path(__file__).parent.parent / "fixtures" / "ground_truth_validation.json"))["scoreboards"]
])
def test_scoreboard_detected_correctly(scene_processor, ground_truth):
    """
    Test that user-approved perfect scoreboard examples are detected correctly.

    Validates:
    - OCR source is 'scoreboard'
    - Both teams detected in correct order (home, away)
    - High confidence (≥0.9)
    - Fixture validation passes
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "scoreboards"
    frame_path = fixtures_dir / ground_truth["fixture_file"]

    # Create Scene model for processing
    scene = Scene(
        scene_number=ground_truth["scene_id"],
        start_time=ground_truth["timestamp"],
        start_seconds=ground_truth["timestamp_seconds"],
        end_seconds=ground_truth["timestamp_seconds"] + 1.0,
        duration=1.0,
        frames=[str(frame_path)]
    )

    # Process the frame
    result = scene_processor._process_single_frame(scene, frame_path)

    # Assert frame was processed successfully
    assert result is not None, f"Frame {ground_truth['fixture_file']} failed to process"

    # Assert correct OCR source
    assert result.ocr_source == "scoreboard", \
        f"Expected source 'scoreboard', got '{result.ocr_source}'"

    # Assert correct teams (ProcessedScene has team1, team2 flat fields)
    assert result.team1 == ground_truth["expected_home"], \
        f"Home team: expected '{ground_truth['expected_home']}', got '{result.team1}'"
    assert result.team2 == ground_truth["expected_away"], \
        f"Away team: expected '{ground_truth['expected_away']}', got '{result.team2}'"

    # Assert high confidence (all approved samples had confidence=1.0)
    assert result.match_confidence >= 0.9, \
        f"Match confidence too low: {result.match_confidence}"

    # Assert fixture matched
    assert result.fixture_id is not None, \
        f"Fixture not matched for {ground_truth['expected_home']} vs {ground_truth['expected_away']}"


def test_all_scoreboard_examples_detected(scene_processor, ground_truth_scoreboards):
    """
    Summary test: verify all 14 scoreboard examples are detected.

    This is a single test that processes all examples and reports
    overall success rate. Useful for quick validation.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "scoreboards"

    total = len(ground_truth_scoreboards)
    detected = 0
    failures = []

    for gt in ground_truth_scoreboards:
        frame_path = fixtures_dir / gt["fixture_file"]

        try:
            # Create Scene model for processing
            scene = Scene(
                scene_number=gt["scene_id"],
                start_time=gt["timestamp"],
                start_seconds=gt["timestamp_seconds"],
                end_seconds=gt["timestamp_seconds"] + 1.0,
                duration=1.0,
                frames=[str(frame_path)]
            )

            result = scene_processor._process_single_frame(scene, frame_path)

            if (result and
                result.ocr_source == "scoreboard" and
                result.team1 == gt["expected_home"] and
                result.team2 == gt["expected_away"]):
                detected += 1
            else:
                failures.append(f"{gt['fixture_file']}: Detection failed or incorrect")
        except Exception as e:
            failures.append(f"{gt['fixture_file']}: {str(e)}")

    # Report results
    success_rate = (detected / total) * 100

    assert detected == total, \
        f"Scoreboard detection: {detected}/{total} ({success_rate:.1f}%)\nFailures:\n" + "\n".join(failures)
