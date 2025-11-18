"""Tests for VenueMatcher class - focused on real transcript patterns."""

import pytest

from motd.analysis.venue_matcher import VenueMatcher, VenueMatch


@pytest.fixture
def venue_matcher():
    """Create VenueMatcher instance with test data."""
    return VenueMatcher("data/venues/premier_league_2025_26.json")


def test_exact_stadium_match(venue_matcher):
    """Test exact stadium name match."""
    result = venue_matcher.match_venue("Anfield")

    assert result is not None
    assert result.team == "Liverpool"
    assert result.venue == "Anfield"
    assert result.confidence >= 0.85
    assert result.source == "stadium"


def test_stadium_with_preposition(venue_matcher):
    """Test 'at [venue]' pattern (common in transcripts)."""
    result = venue_matcher.match_venue("at Turf Moor")

    assert result is not None
    assert result.team == "Burnley"
    assert result.venue == "Turf Moor"
    assert result.confidence >= 0.85


def test_alias_match(venue_matcher):
    """Test shortened stadium names."""
    result = venue_matcher.match_venue("Emirates")

    assert result is not None
    assert result.team == "Arsenal"
    assert result.venue == "Emirates Stadium"


def test_get_venue_for_team(venue_matcher):
    """Test looking up venue by team name (for fixture matching)."""
    venue = venue_matcher.get_venue_for_team("Liverpool")
    assert venue == "Anfield"

    venue = venue_matcher.get_venue_for_team("Arsenal")
    assert venue == "Emirates Stadium"

    venue = venue_matcher.get_venue_for_team("Nonexistent Team")
    assert venue is None


def test_all_20_teams_have_venues(venue_matcher):
    """Test all 20 Premier League teams have venue data."""
    teams = [
        "Arsenal",
        "Aston Villa",
        "Bournemouth",
        "Brentford",
        "Brighton & Hove Albion",
        "Burnley",
        "Chelsea",
        "Crystal Palace",
        "Everton",
        "Fulham",
        "Leeds United",
        "Liverpool",
        "Manchester City",
        "Manchester United",
        "Newcastle United",
        "Nottingham Forest",
        "Sunderland",
        "Tottenham Hotspur",
        "West Ham United",
        "Wolverhampton Wanderers",
    ]

    for team in teams:
        venue = venue_matcher.get_venue_for_team(team)
        assert venue is not None, f"No venue found for {team}"
        assert isinstance(venue, str)
        assert len(venue) > 0


def test_no_match_returns_none(venue_matcher):
    """Test unrelated text returns None."""
    result = venue_matcher.match_venue("completely unrelated text")
    assert result is None


def test_venue_match_dataclass():
    """Test VenueMatch dataclass structure."""
    match = VenueMatch(
        venue="Anfield",
        team="Liverpool",
        confidence=1.0,
        matched_text="anfield",
        source="stadium",
    )

    assert match.venue == "Anfield"
    assert match.team == "Liverpool"
    assert match.confidence == 1.0
    assert match.matched_text == "anfield"
    assert match.source == "stadium"
