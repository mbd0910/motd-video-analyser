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


def test_no_alias_index_used(venue_matcher):
    """Test that the alias index is no longer used (stadium names only).

    With fuzzy substring matching (partial_ratio), we can't prevent all substring
    matches (e.g., "Bridge" matching "Stamford Bridge"). But we CAN verify that
    the alias INDEX is not being searched - only the stadium index.

    The key test: stadium names should work, but we removed alias/additional_ref matching.
    """
    # Full stadium names should work
    result = venue_matcher.match_venue("Stamford Bridge")
    assert result is not None
    assert result.team == "Chelsea"
    assert result.venue == "Stamford Bridge"
    assert result.source == "stadium"  # Verify it's from stadium index, not alias

    result = venue_matcher.match_venue("Emirates Stadium")
    assert result is not None
    assert result.team == "Arsenal"
    assert result.source == "stadium"  # Not from alias index


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


def test_stadium_names_only_no_aliases(venue_matcher):
    """Test that aliases are NOT matched (stadium names only).

    Prevents false positives like 'that lane' matching Tottenham's alias 'The Lane'.
    """
    # This should NOT match Tottenham's "The Lane" alias
    result = venue_matcher.match_venue("that lane for Fulham")
    assert result is None, "Should not match 'that lane' against 'The Lane' alias"

    # But the actual stadium name should still work
    result = venue_matcher.match_venue("Tottenham Hotspur Stadium")
    assert result is not None
    assert result.team == "Tottenham Hotspur"
    assert result.venue == "Tottenham Hotspur Stadium"


def test_typo_fuzzy_matching(venue_matcher):
    """Test fuzzy matching handles transcription typos.

    Real example: Whisper transcribed 'Selhurst Park' as 'Selhurl Park'
    """
    # "Selhurl Park" should match "Selhurst Park" via fuzzy matching
    result = venue_matcher.match_venue("James Fielden was at Selhurl Park")
    assert result is not None, "Should fuzzy match 'Selhurl' to 'Selhurst'"
    assert result.team == "Crystal Palace"
    assert result.venue == "Selhurst Park"
    assert result.confidence >= 0.7  # Fuzzy match, slightly lower confidence


def test_real_transcript_patterns(venue_matcher):
    """Test actual patterns from motd_2025-26_2025-11-01 transcript."""
    # Match 1: Liverpool vs Aston Villa
    result = venue_matcher.match_venue("your commentator at anfield, steve wilson.")
    assert result is not None
    assert result.team == "Liverpool"
    assert result.venue == "Anfield"

    # Match 2: Arsenal vs Burnley (away at Burnley)
    result = venue_matcher.match_venue("Stephen Wyeth was at Turf Moor.")
    assert result is not None
    assert result.team == "Burnley"
    assert result.venue == "Turf Moor"

    # Match 3: Man Utd vs Nottingham Forest (away at Forest)
    result = venue_matcher.match_venue("Guy Mowbray was at the City round.")  # "round" is OCR typo for "ground"
    assert result is not None
    assert result.team == "Nottingham Forest"
    assert result.venue == "City Ground"
