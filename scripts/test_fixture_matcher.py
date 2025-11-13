"""Test fixture matcher with 2025-11-01 episode."""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.motd.ocr.fixture_matcher import FixtureMatcher


def main():
    """Test fixture matcher on 2025-11-01 episode data."""
    # Initialise
    fixtures_path = Path(__file__).parent.parent / 'data' / 'fixtures' / 'premier_league_2025_26.json'
    manifest_path = Path(__file__).parent.parent / 'data' / 'episodes' / 'episode_manifest.json'

    print("Initialising fixture matcher...")
    matcher = FixtureMatcher(fixtures_path, manifest_path)
    print(f"✓ Fixture matcher initialised\n")

    episode_id = "motd-2025-11-01"

    # Test 1: Get expected fixtures
    print(f"{'='*70}")
    print(f"Test 1: Expected Fixtures for {episode_id}")
    print(f"{'='*70}\n")

    fixtures = matcher.get_expected_fixtures(episode_id)
    print(f"Found {len(fixtures)} expected matches:\n")

    for i, fixture in enumerate(fixtures, 1):
        print(f"{i}. {fixture['home_team']} vs {fixture['away_team']}")
        print(f"   Match ID: {fixture['match_id']}")
        print(f"   Score: {fixture.get('score', 'N/A')}")
        print()

    # Test 2: Get expected teams
    print(f"\n{'='*70}")
    print(f"Test 2: Expected Teams (Flat List)")
    print(f"{'='*70}\n")

    teams = matcher.get_expected_teams(episode_id)
    print(f"Total expected teams: {len(teams)}\n")

    for team in teams:
        print(f"  • {team}")

    # Test 3: Validate expected teams (should pass)
    print(f"\n{'='*70}")
    print(f"Test 3: Validation - Expected Teams")
    print(f"{'='*70}\n")

    detected = ["Brighton & Hove Albion", "Arsenal"]
    print(f"Detected teams: {detected}\n")

    validation = matcher.validate_teams(detected, episode_id)
    print(f"Validated teams: {validation['validated_teams']}")
    print(f"Unexpected teams: {validation['unexpected_teams']}")
    print(f"Confidence boost: {validation['confidence_boost']}")

    if validation['validated_teams'] and not validation['unexpected_teams']:
        print("✓ Both teams validated!")
    else:
        print("✗ Validation issues")

    # Test 4: Validate with unexpected team (should flag warning)
    print(f"\n{'='*70}")
    print(f"Test 4: Validation - Unexpected Team")
    print(f"{'='*70}\n")

    detected = ["Brighton & Hove Albion", "West Ham United"]
    print(f"Detected teams: {detected}\n")

    validation = matcher.validate_teams(detected, episode_id)
    print(f"Validated teams: {validation['validated_teams']}")
    print(f"Unexpected teams: {validation['unexpected_teams']}")
    print(f"Confidence boost: {validation['confidence_boost']}")

    if validation['unexpected_teams']:
        print(f"⚠ Warning: Unexpected teams detected: {validation['unexpected_teams']}")
    else:
        print("✓ All teams validated")

    # Test 5: Fixture identification (both teams detected)
    print(f"\n{'='*70}")
    print(f"Test 5: Fixture Identification")
    print(f"{'='*70}\n")

    test_pairs = [
        ("Brighton & Hove Albion", "Leeds United"),  # Real fixture
        ("Burnley", "Arsenal"),  # Real fixture
        ("Liverpool", "Aston Villa"),  # Real fixture
        ("Brighton & Hove Albion", "West Ham United"),  # Not a real fixture
    ]

    for team1, team2 in test_pairs:
        print(f"Searching for: {team1} vs {team2}")
        fixture = matcher.identify_fixture(team1, team2, episode_id)

        if fixture:
            print(f"  ✓ Found: {fixture['match_id']}")
            print(f"    {fixture['home_team']} vs {fixture['away_team']}")
            print(f"    Score: {fixture.get('score', 'N/A')}")
        else:
            print(f"  ✗ No fixture found (not in this episode)")
        print()

    # Test 6: Integration example (simulating OCR pipeline)
    print(f"\n{'='*70}")
    print(f"Test 6: Integration Example (OCR Pipeline Simulation)")
    print(f"{'='*70}\n")

    print("Scenario: OCR detects 'Brighton' and 'Arsenal' from scoreboard\n")

    # Step 1: Get candidate teams for episode
    candidate_teams = matcher.get_expected_teams(episode_id)
    print(f"Step 1: Got {len(candidate_teams)} candidate teams for episode")

    # Step 2: Simulate team matching (would come from TeamMatcher)
    detected_teams = ["Brighton & Hove Albion", "Arsenal"]
    print(f"Step 2: Team matcher found: {detected_teams}")

    # Step 3: Validate against fixtures
    validation = matcher.validate_teams(detected_teams, episode_id)
    print(f"Step 3: Fixture validation:")
    print(f"  Validated: {validation['validated_teams']}")
    print(f"  Confidence boost: {validation['confidence_boost']}")

    # Step 4: Identify specific fixture
    if len(detected_teams) == 2:
        fixture = matcher.identify_fixture(detected_teams[0], detected_teams[1], episode_id)
        if fixture:
            print(f"Step 4: Identified fixture: {fixture['match_id']}")
            print(f"  {fixture['home_team']} vs {fixture['away_team']}")
            print(f"  Score: {fixture.get('score', 'N/A')}")
        else:
            print(f"Step 4: Could not identify specific fixture")

    print(f"\n{'='*70}")
    print("Test complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
