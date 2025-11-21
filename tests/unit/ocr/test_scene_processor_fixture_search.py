"""
Unit tests for SceneProcessor alternative fixture search logic.

Tests the fix for frame_0834 bug: when top 2 teams don't form a valid fixture,
search through top N teams to find a valid combination.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from motd.pipeline.models import Scene, TeamMatch, OCRResult
from motd.ocr.scene_processor import SceneProcessor, EpisodeContext
from motd.ocr.fixture_matcher import FixtureMatcher


@pytest.fixture
def mock_ocr_reader():
    """Mock OCR reader that returns predefined results."""
    reader = Mock()
    reader.extract_with_fallback = Mock()
    reader.validate_ft_graphic = Mock(return_value=True)
    return reader


@pytest.fixture
def mock_team_matcher():
    """Mock team matcher that returns predefined team matches."""
    matcher = Mock()
    return matcher


@pytest.fixture
def fixture_matcher():
    """Real fixture matcher with test data."""
    fixtures_path = Path("data/fixtures/premier_league_2025_26.json")
    manifest_path = Path("data/episodes/episode_manifest.json")
    return FixtureMatcher(fixtures_path, manifest_path)


@pytest.fixture
def episode_context():
    """Episode context for Episode 02 (motd_2025-26_2025-11-08)."""
    return EpisodeContext(
        episode_id="motd_2025-26_2025-11-08",
        expected_teams=[
            "Tottenham Hotspur",
            "Manchester United",
            "West Ham United",
            "Burnley",
            "Everton",
            "Fulham",
            "Sunderland",
            "Arsenal",
            "Chelsea",
            "Wolverhampton Wanderers"
        ],
        expected_fixtures=[
            {"match_id": "2025-11-08-tottenham-manutd", "home_team": "Tottenham Hotspur", "away_team": "Manchester United"},
            {"match_id": "2025-11-08-westham-burnley", "home_team": "West Ham United", "away_team": "Burnley"},
            {"match_id": "2025-11-08-everton-fulham", "home_team": "Everton", "away_team": "Fulham"},
            {"match_id": "2025-11-08-sunderland-arsenal", "home_team": "Sunderland", "away_team": "Arsenal"},
            {"match_id": "2025-11-08-chelsea-wolves", "home_team": "Chelsea", "away_team": "Wolverhampton Wanderers"}
        ]
    )


def test_top2_teams_valid_fixture_fast_path(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test fast path: top 2 teams form a valid fixture.

    This is the common case - should return immediately without searching alternatives.
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    # Top 2 teams form valid fixture (Tottenham vs Man Utd)
    teams = [
        TeamMatch(team="Tottenham Hotspur", confidence=0.95, matched_text="tottenham", source="ocr"),
        TeamMatch(team="Manchester United", confidence=0.90, matched_text="manchester", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is not None
    assert fixture is not None
    assert fixture['match_id'] == "2025-11-08-tottenham-manutd"
    assert {validated_teams[0].team, validated_teams[1].team} == {"Tottenham Hotspur", "Manchester United"}


def test_top2_invalid_but_teams_2_and_3_valid(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test alternative search: top 2 don't form fixture, but teams 2+3 do.

    Scenario:
    - Team 1: West Ham United (false positive)
    - Team 2: Manchester United
    - Team 3: Tottenham Hotspur
    - Valid fixture: Man Utd + Tottenham (#2 + #3)
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    teams = [
        TeamMatch(team="West Ham United", confidence=1.00, matched_text="united", source="ocr"),  # False positive
        TeamMatch(team="Manchester United", confidence=1.00, matched_text="manchester united", source="ocr"),
        TeamMatch(team="Tottenham Hotspur", confidence=1.00, matched_text="tottenham", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is not None, "Should find alternative fixture (teams 2+3)"
    assert fixture is not None
    assert fixture['match_id'] == "2025-11-08-tottenham-manutd"
    assert {validated_teams[0].team, validated_teams[1].team} == {"Tottenham Hotspur", "Manchester United"}


def test_top2_invalid_but_teams_1_and_3_valid(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test alternative search: top 2 don't form fixture, but teams 1+3 do.

    Scenario:
    - Team 1: Chelsea
    - Team 2: Arsenal (not a valid fixture with Chelsea)
    - Team 3: Wolverhampton Wanderers
    - Valid fixture: Chelsea + Wolves (#1 + #3)
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    teams = [
        TeamMatch(team="Chelsea", confidence=0.95, matched_text="chelsea", source="ocr"),
        TeamMatch(team="Arsenal", confidence=0.90, matched_text="arsenal", source="ocr"),  # Not in same fixture
        TeamMatch(team="Wolverhampton Wanderers", confidence=0.85, matched_text="wolves", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is not None, "Should find alternative fixture (teams 1+3)"
    assert fixture is not None
    assert fixture['match_id'] == "2025-11-08-chelsea-wolves"
    assert {validated_teams[0].team, validated_teams[1].team} == {"Chelsea", "Wolverhampton Wanderers"}


def test_no_valid_fixture_in_top5_should_reject(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test rejection: no valid fixture found in any combination of top 5 teams.

    Scenario: All teams detected, but no pair forms a valid fixture.
    Should return None (reject scene).
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    # Create 5 teams where no pair forms a valid fixture
    # (using teams from different fixtures that don't play each other)
    teams = [
        TeamMatch(team="Tottenham Hotspur", confidence=0.95, matched_text="tottenham", source="ocr"),
        TeamMatch(team="West Ham United", confidence=0.90, matched_text="west ham", source="ocr"),
        TeamMatch(team="Everton", confidence=0.85, matched_text="everton", source="ocr"),
        TeamMatch(team="Sunderland", confidence=0.80, matched_text="sunderland", source="ocr"),
        TeamMatch(team="Chelsea", confidence=0.75, matched_text="chelsea", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is None, "Should reject when no valid fixture found"
    assert fixture is None


def test_only_one_team_detected_should_reject(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test edge case: only 1 team detected.

    Should reject (can't form a fixture with 1 team).
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    teams = [
        TeamMatch(team="Manchester United", confidence=0.95, matched_text="man utd", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is None
    assert fixture is None


def test_frame_0834_exact_scenario(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Exact reproduction of frame_0834 bug scenario.

    OCR text: "tottenham hotspur 2 manchester united ft..."
    Teams matched (in order):
    1. West Ham United (1.00) - "united" matches
    2. Manchester United (1.00)
    3. Tottenham Hotspur (1.00)

    Expected: Should find Man Utd + Tottenham (teams 2+3) as valid fixture.
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    # Exact team ordering from test_scene_501.py debug output
    teams = [
        TeamMatch(team="West Ham United", confidence=1.00, matched_text="united", source="ocr"),
        TeamMatch(team="Manchester United", confidence=1.00, matched_text="manchester united", source="ocr"),
        TeamMatch(team="Tottenham Hotspur", confidence=1.00, matched_text="tottenham hotspur", source="ocr")
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is not None, \
        "frame_0834 scenario should succeed with alternative search"
    assert fixture is not None
    assert fixture['match_id'] == "2025-11-08-tottenham-manutd", \
        f"Should find Tottenham vs Man Utd fixture, got: {fixture.get('match_id')}"

    # Verify correct teams (order doesn't matter, but both should be present)
    team_names = {validated_teams[0].team, validated_teams[1].team}
    assert team_names == {"Tottenham Hotspur", "Manchester United"}, \
        f"Should return Tottenham and Man Utd, got: {team_names}"


def test_multiple_valid_fixtures_picks_highest_confidence(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context):
    """
    Test tie-breaking: if multiple valid fixtures found, pick highest confidence pair.

    Scenario:
    - Teams 1+2: valid fixture, combined confidence = 1.80
    - Teams 3+4: valid fixture, combined confidence = 1.50
    - Should pick teams 1+2 (higher confidence)
    """
    processor = SceneProcessor(mock_ocr_reader, mock_team_matcher, fixture_matcher, episode_context)

    teams = [
        # High confidence valid fixture (Tottenham vs Man Utd)
        TeamMatch(team="Tottenham Hotspur", confidence=0.95, matched_text="tottenham", source="ocr"),
        TeamMatch(team="Manchester United", confidence=0.85, matched_text="man utd", source="ocr"),  # Combined: 1.80

        # Lower confidence valid fixture (West Ham vs Burnley)
        TeamMatch(team="West Ham United", confidence=0.80, matched_text="west ham", source="ocr"),
        TeamMatch(team="Burnley", confidence=0.70, matched_text="burnley", source="ocr")  # Combined: 1.50
    ]

    validated_teams, fixture = processor._validate_fixture_pair(teams)

    assert validated_teams is not None
    assert fixture is not None

    # Should pick the highest confidence fixture (Tottenham vs Man Utd, not West Ham vs Burnley)
    team_names = {validated_teams[0].team, validated_teams[1].team}
    assert team_names == {"Tottenham Hotspur", "Manchester United"}, \
        f"Should pick highest confidence fixture (Tottenham + Man Utd), got: {team_names}"
