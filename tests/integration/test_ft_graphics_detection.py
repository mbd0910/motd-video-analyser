"""
Integration tests for FT graphic fixture validation.

Tests that fixture data correctly matches ground truth FT graphic teams.
Note: End-to-end OCR and SceneProcessor tests are in test_scene_processor_ft_frames.py
"""

import pytest
from pathlib import Path
from typing import Dict

from motd.ocr.fixture_matcher import FixtureMatcher


# Ground truth data for all 8 FT graphic frames from episode motd_2025-26_2025-11-01
FT_GRAPHICS_GROUND_TRUTH = [
    {
        'frame': 'frame_0329_scene_change_607.3s.jpg',
        'home': 'Liverpool',
        'away': 'Aston Villa',
    },
    {
        'frame': 'frame_0697_scene_change_1325.4s.jpg',
        'home': 'Burnley',
        'away': 'Arsenal',
    },
    {
        'frame': 'frame_1116_scene_change_2123.1s.jpg',
        'home': 'Nottingham Forest',
        'away': 'Manchester United',
    },
    {
        'frame': 'frame_1117_scene_change_2124.2s.jpg',
        'home': 'Nottingham Forest',
        'away': 'Manchester United',
    },
    {
        'frame': 'frame_1503_interval_sampling_2884.0s.jpg',
        'home': 'Fulham',
        'away': 'Wolverhampton Wanderers',
    },
    {
        'frame': 'frame_1885_interval_sampling_3646.0s.jpg',
        'home': 'Tottenham Hotspur',
        'away': 'Chelsea',
    },
    {
        'frame': 'frame_2214_interval_sampling_4300.0s.jpg',
        'home': 'Brighton & Hove Albion',
        'away': 'Leeds United',
    },
    {
        'frame': 'frame_2494_interval_sampling_4842.0s.jpg',
        'home': 'Crystal Palace',
        'away': 'Brentford',
    },
]


@pytest.fixture(scope="module")
def fixture_matcher():
    """Initialize FixtureMatcher with fixtures and episode manifest."""
    fixtures_path = Path(__file__).parent.parent.parent / "data" / "fixtures" / "premier_league_2025_26.json"
    manifest_path = Path(__file__).parent.parent.parent / "data" / "episodes" / "episode_manifest.json"
    return FixtureMatcher(fixtures_path, manifest_path)


@pytest.fixture
def episode_id():
    """Episode ID for test fixtures."""
    return "motd_2025-26_2025-11-01"


@pytest.mark.parametrize("ground_truth", FT_GRAPHICS_GROUND_TRUTH, ids=lambda gt: gt['frame'])
def test_fixture_validation(ground_truth: Dict, fixture_matcher: FixtureMatcher, episode_id: str):
    """
    Test that fixture validation correctly identifies valid team pairs.

    Verifies:
    - identify_fixture() finds correct fixture for ground truth team pair
    - Fixture data contains all expected matches
    - Home/away ordering is correct
    """
    home = ground_truth['home']
    away = ground_truth['away']

    # Test direct fixture lookup
    fixture = fixture_matcher.identify_fixture(home, away, episode_id)

    assert fixture is not None, f"No fixture found for {home} vs {away}"
    assert fixture['home_team'] == home, f"Home team mismatch: {fixture['home_team']} != {home}"
    assert fixture['away_team'] == away, f"Away team mismatch: {fixture['away_team']} != {away}"
