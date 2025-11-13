"""Test team matcher with various text formats."""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.motd.ocr.team_matcher import TeamMatcher


def main():
    """Test team matcher on various input formats."""
    # Initialise matcher
    teams_path = Path(__file__).parent.parent / 'data' / 'teams' / 'premier_league_2025_26.json'

    print("Initialising team matcher...")
    matcher = TeamMatcher(teams_path)
    print(f"✓ Team matcher initialised ({len(matcher.get_all_teams())} teams loaded)\n")

    # Test cases covering various formats and OCR scenarios
    test_cases = [
        ("Manchester United", "Full team name"),
        ("Man Utd", "Common abbreviation"),
        ("BRIGHTON", "All caps"),
        ("brighton", "All lowercase"),
        ("Brighton 2-0 Leeds", "Scoreboard with score"),
        ("Spurs", "Nickname"),
        ("Forest", "Partial name"),
        ("Br1ghton", "OCR error (1 instead of i)"),
        ("The Gunners", "Alternative name"),
        ("LIV", "Three-letter code"),
        ("AST", "Three-letter code (Aston Villa)"),
        ("BUR", "Three-letter code (Burnley)"),
        ("ARS", "Three-letter code (Arsenal)"),
    ]

    print(f"{'='*70}")
    print("Testing Team Matching (No Fixture Context)")
    print(f"{'='*70}\n")

    for text, description in test_cases:
        print(f"Input: '{text}' ({description})")
        matches = matcher.match(text)

        if matches:
            for i, match in enumerate(matches[:2], 1):  # Show top 2
                print(f"  {i}. {match['team']}")
                print(f"     Confidence: {match['confidence']:.2f}")
                print(f"     Matched via: {match['matched_text']}")
        else:
            print("  ✗ No matches")
        print()

    # Test fixture-aware matching
    print(f"\n{'='*70}")
    print("Testing Fixture-Aware Matching")
    print(f"{'='*70}\n")

    # Simulate a fixture from reconnaissance: Brighton vs Arsenal
    candidates = [
        "Brighton & Hove Albion",
        "Arsenal"
    ]

    fixture_tests = [
        "Brighton 2 Arsenal 0",
        "BHA 2 ARS 0",
        "Brighton vs Arsenal",
    ]

    for text in fixture_tests:
        print(f"Input: '{text}'")
        print(f"Expected teams: Brighton & Hove Albion, Arsenal\n")

        matches = matcher.match_multiple(text, candidate_teams=candidates, max_teams=2)

        if len(matches) == 2:
            print(f"  ✓ Found both teams:")
            for match in matches:
                print(f"    • {match['team']}")
                print(f"      Confidence: {match['confidence']:.2f}")
                print(f"      Fixture validated: {match['fixture_validated']}")
        else:
            print(f"  ⚠ Found {len(matches)}/2 teams:")
            for match in matches:
                print(f"    • {match['team']} (confidence: {match['confidence']:.2f})")
        print()

    # Test from actual OCR results (from 009b tests)
    print(f"\n{'='*70}")
    print("Testing Real OCR Extractions (from 009b)")
    print(f"{'='*70}\n")

    ocr_results = [
        ("LIV", "scene_154 - Liverpool scoreboard"),
        ("AST", "scene_154 - Aston Villa scoreboard"),
        ("BUR", "scene_277 - Burnley scoreboard"),
        ("ARS", "scene_277 - Arsenal scoreboard"),
    ]

    for text, description in ocr_results:
        print(f"{description}")
        print(f"OCR text: '{text}'")

        matches = matcher.match(text, threshold=0.70)  # Lower threshold for 3-letter codes

        if matches:
            best_match = matches[0]
            print(f"  → {best_match['team']} (confidence: {best_match['confidence']:.2f})")
        else:
            print("  ✗ No match")
        print()

    print(f"{'='*70}")
    print("Test complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
