"""
Unit tests for TeamMatcher false positive cases.

Test cases based on real bugs discovered during Episode 02 processing.
"""

import pytest
from pathlib import Path
from motd.ocr.team_matcher import TeamMatcher


@pytest.fixture
def team_matcher():
    """Initialize TeamMatcher with Premier League 2025-26 teams."""
    teams_path = Path("data/teams/premier_league_2025_26.json")
    return TeamMatcher(teams_path)


def test_tottenham_vs_west_ham_false_positive(team_matcher):
    """
    Test for false positive: "ham" in "Tottenham" matching "West Ham United".

    Real bug from Episode 02, frame_0834 (Spurs vs Man Utd FT graphic):
    - OCR text: "Tottenham Hotspur 2 Manchester United FT"
    - Expected: Tottenham Hotspur, Manchester United
    - Actual (before fix): West Ham United, Manchester United
    - Root cause: Fuzzy matcher matches "ham" substring

    Expected behavior after fix:
    - "Tottenham Hotspur" should rank higher than "West Ham United"
    - When matching full team names, prefer longer/exact matches over substrings
    """
    # Simulate OCR text from frame_0834
    ocr_text = "Tottenham Hotspur 2 Manchester United FT Mbeumo 32', de Ligt 90'+6'"

    # Expected teams for Episode 02 (fixture-aware matching)
    candidate_teams = [
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
    ]

    # Match teams
    results = team_matcher.match_multiple(
        text=ocr_text,
        candidate_teams=candidate_teams,
        threshold=0.75,
        max_teams=3  # Get top 3 to see ranking
    )

    # Extract team names
    matched_teams = [r['team'] for r in results]

    print(f"\nOCR text: {ocr_text}")
    print(f"Matched teams (ranked):")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['team']} (confidence: {result['confidence']:.2f})")

    # CRITICAL: Tottenham Hotspur should be in top 2
    assert "Tottenham Hotspur" in matched_teams[:2], \
        f"Tottenham Hotspur should be in top 2, got: {matched_teams[:2]}"

    # CRITICAL: Manchester United should be in top 2
    assert "Manchester United" in matched_teams[:2], \
        f"Manchester United should be in top 2, got: {matched_teams[:2]}"

    # CRITICAL: West Ham United should NOT be in top 2 (it's a false positive)
    assert "West Ham United" not in matched_teams[:2], \
        f"West Ham United should NOT be in top 2 (false positive), got: {matched_teams[:2]}"

    # Check correct ranking: Tottenham and Man Utd should be #1 and #2
    # (order doesn't matter, but both should be top 2)
    assert set(matched_teams[:2]) == {"Tottenham Hotspur", "Manchester United"}, \
        f"Expected {{Tottenham Hotspur, Manchester United}}, got: {set(matched_teams[:2])}"


def test_substring_matching_prioritization(team_matcher):
    """
    Test that full word/team name matches are prioritized over substring matches.

    Cases:
    - "ham" should match "West Ham United", not "Tottenham"
    - "Tottenham Hotspur" should match "Tottenham Hotspur", not "ham" → "West Ham"
    - "Manchester" should match "Manchester United"/"Manchester City", not substring in other teams
    """
    # Case 1: Full team name should trump substring
    results1 = team_matcher.match("Tottenham Hotspur", threshold=0.7)
    assert results1[0]['team'] == "Tottenham Hotspur", \
        f"Expected Tottenham Hotspur as top match, got: {results1[0]['team']}"

    # Case 2: Short substring should still match if it's the only option
    results2 = team_matcher.match("ham united", threshold=0.7)
    assert results2[0]['team'] == "West Ham United", \
        f"Expected West Ham United for 'ham united', got: {results2[0]['team']}"

    # Case 3: When text contains both teams, both should be detected correctly
    results3 = team_matcher.match_multiple(
        "Tottenham vs West Ham",
        threshold=0.7,
        max_teams=2
    )
    matched = {r['team'] for r in results3}
    assert matched == {"Tottenham Hotspur", "West Ham United"}, \
        f"Expected both teams, got: {matched}"


def test_episode_02_frame_0834_exact_scenario(team_matcher):
    """
    Exact reproduction of Episode 02 frame_0834 bug.

    This test uses the EXACT OCR text and candidate teams from the failing scenario.
    If this test passes, frame_0834 should be detected correctly in the pipeline.
    """
    # EXACT OCR text from debug logs (line 2025-11-20 20:35:12,112)
    ocr_text = "tottenham hotspur 2 manchester united ft mbeumo 32', de ligt 90'+6''"

    # EXACT candidate teams for Episode 02 (from fixture manifest)
    candidate_teams = [
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
    ]

    # Use the EXACT threshold from pipeline (0.75)
    results = team_matcher.match(
        text=ocr_text,
        candidate_teams=candidate_teams,
        threshold=0.75
    )

    # Top 2 teams should be Tottenham and Man Utd (in any order)
    top_2_teams = {results[0]['team'], results[1]['team']}

    assert top_2_teams == {"Tottenham Hotspur", "Manchester United"}, \
        f"Expected {{Tottenham Hotspur, Manchester United}}, got: {top_2_teams}. " \
        f"Full results: {[(r['team'], r['confidence']) for r in results]}"

    # Verify they form a valid fixture (this is checked by FixtureMatcher in the pipeline)
    # For Episode 02, Tottenham vs Man Utd is fixture "2025-11-08-tottenham-manutd"
    assert "Tottenham Hotspur" in top_2_teams
    assert "Manchester United" in top_2_teams
