#!/usr/bin/env python3
"""
Generate short team names based on internet research of commonly used forms.

Sources:
- https://www.sportsunfold.com/english-premier-league-all-team-nicknames/
- ESPN, NBC Sports, and other sports media usage
- Common abbreviations in articles and commentary

For 2025/26 season teams only (Burnley, Leeds, Sunderland promoted).
"""

import json
from pathlib import Path


def get_research_based_short_names() -> dict[str, list[str]]:
    """
    Short names based on internet research and media usage.

    Guidelines:
    - Include commonly used shortened forms from sports media
    - Include widely recognized nicknames
    - Based on actual usage in articles, not just official nicknames
    """
    return {
        # Single-word teams - typically use full name or nickname
        "Arsenal": [],  # "Arsenal" or "The Gunners"
        "Bournemouth": [],  # "Bournemouth" or "The Cherries"
        "Brentford": [],  # "Brentford" or "The Bees"
        "Burnley": [],  # "Burnley" or "The Clarets"
        "Chelsea": [],  # "Chelsea" or "The Blues"
        "Everton": [],  # "Everton" or "The Toffees"
        "Fulham": [],  # "Fulham" or "The Cottagers"
        "Liverpool": [],  # "Liverpool" or "The Reds"
        "Sunderland": [],  # "Sunderland" or "The Black Cats"

        # Multi-word teams with common shortened forms
        "Aston Villa": ["Villa"],  # Very common: "Villa"
        "Brighton & Hove Albion": ["Brighton"],  # Always shortened to "Brighton"
        "Crystal Palace": ["Palace"],  # Common: "Palace"
        "Leeds United": ["Leeds"],  # Common: "Leeds"
        "Manchester City": ["Man City", "City"],  # Very common: "Man City" or "City"
        "Manchester United": ["Man United", "Man Utd", "United"],  # "Man United", "Man Utd", or "United"
        "Newcastle United": ["Newcastle"],  # Common: "Newcastle"
        "Nottingham Forest": ["Forest", "Nottm Forest"],  # "Forest" or "Nottm Forest"
        "Tottenham Hotspur": ["Tottenham", "Spurs"],  # "Tottenham" or very common "Spurs"
        "West Ham United": ["West Ham"],  # "West Ham"
        "Wolverhampton Wanderers": ["Wolves"],  # Almost always "Wolves"
    }


def main():
    # Load teams JSON
    teams_json_path = Path(__file__).parent.parent / 'data' / 'teams' / 'premier_league_2025_26.json'

    with open(teams_json_path) as f:
        data = json.load(f)

    short_names_map = get_research_based_short_names()

    print("=" * 80)
    print("SHORT TEAM NAMES (based on internet research - 2025/26 season)")
    print("=" * 80)
    print()
    print("Sources:")
    print("- Sports media usage (ESPN, NBC Sports, BBC Sport)")
    print("- Common abbreviations in articles")
    print("- Premier League team nickname databases")
    print()

    # Track potential conflicts
    all_short_names = {}
    conflicts = []

    for team in data['teams']:
        full_name = team['full']
        short_names = short_names_map.get(full_name, [])

        # Show with visual indicator for empty
        if short_names:
            print(f"{full_name:30} → {short_names}")
        else:
            print(f"{full_name:30} → (use full name)")

        # Track conflicts (same short name for multiple teams)
        for short_name in short_names:
            if short_name in all_short_names:
                conflict = (short_name, all_short_names[short_name], full_name)
                if conflict not in conflicts:
                    conflicts.append(conflict)
            else:
                all_short_names[short_name] = full_name

    # Report conflicts
    if conflicts:
        print()
        print("=" * 80)
        print("⚠️  POTENTIAL CONFLICTS")
        print("=" * 80)
        print()
        for short_name, team1, team2 in conflicts:
            print(f"  '{short_name}' → {team1} AND {team2}")
            if short_name in ["City", "United"]:
                print(f"    → Note: '{short_name}' is acceptable with context")
    else:
        print()
        print("✅ No ambiguous conflicts")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total teams: {len(data['teams'])}")
    print(f"Teams with short names: {sum(1 for sn in short_names_map.values() if sn)}")
    print(f"Teams without short names: {sum(1 for sn in short_names_map.values() if not sn)}")
    print(f"Total short names: {len(all_short_names)}")
    print(f"Conflicts: {len(conflicts)}")


if __name__ == '__main__':
    main()
