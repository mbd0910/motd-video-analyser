#!/usr/bin/env python3
"""
Generate realistic short team names based on actual MOTD commentary patterns.

This replaces the algorithmic approach with manually curated short names
that commentators actually use.
"""

import json
from pathlib import Path


def get_realistic_short_names() -> dict[str, list[str]]:
    """
    Manually curated short names based on actual MOTD usage.

    Guidelines:
    - Only include names that commentators actually use
    - Focus on natural speech patterns, not algorithmic splits
    - Includes team nicknames that appear in commentary
    - Empty list = team is always called by full name (or abbrev from teams JSON)
    """
    return {
        "Arsenal": [],  # Always "Arsenal"
        "Aston Villa": ["Villa"],  # "Villa", never "Aston"
        "Bournemouth": [],  # Always "Bournemouth"
        "Brentford": [],  # Always "Brentford"
        "Brighton & Hove Albion": ["Brighton"],  # "Brighton", never "Albion" alone
        "Burnley": [],  # Always "Burnley"
        "Chelsea": [],  # Always "Chelsea"
        "Crystal Palace": ["Palace"],  # "Palace", never just "Crystal"
        "Everton": [],  # Always "Everton"
        "Fulham": [],  # Always "Fulham"
        "Leeds United": ["Leeds"],  # "Leeds", sometimes "United" but ambiguous
        "Liverpool": [],  # Always "Liverpool" (sometimes "Pool" in casual speech, but rare in MOTD)
        "Manchester City": ["Man City", "City"],  # "Man City" or "City", never just "Manchester"
        "Manchester United": ["Man United", "Man Utd"],  # "Man United" or "Man Utd", never just "Manchester"
        "Newcastle United": ["Newcastle"],  # "Newcastle", rarely "United" (too ambiguous)
        "Nottingham Forest": ["Forest", "Nottm Forest"],  # "Forest" or "Nottm Forest", sometimes "Nottingham"
        "Sunderland": [],  # Always "Sunderland"
        "Tottenham Hotspur": ["Tottenham", "Spurs"],  # "Tottenham" or "Spurs", never "Hotspur" alone
        "West Ham United": ["West Ham"],  # "West Ham", never just "West"
        "Wolverhampton Wanderers": ["Wolves"],  # "Wolves", rarely "Wolverhampton"
    }


def main():
    # Load teams JSON
    teams_json_path = Path(__file__).parent.parent / 'data' / 'teams' / 'premier_league_2025_26.json'

    with open(teams_json_path) as f:
        data = json.load(f)

    short_names_map = get_realistic_short_names()

    print("=" * 80)
    print("REALISTIC SHORT TEAM NAMES (manually curated)")
    print("=" * 80)
    print()

    # Track potential conflicts
    all_short_names = {}
    conflicts = []

    for team in data['teams']:
        full_name = team['full']
        short_names = short_names_map.get(full_name, [])

        # Show with visual indicator for empty
        display = short_names if short_names else ["(none - use full name)"]
        print(f"{full_name:30} → {display}")

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
        print("⚠️  POTENTIAL CONFLICTS (same short name for multiple teams)")
        print("=" * 80)
        print()
        for short_name, team1, team2 in conflicts:
            print(f"  '{short_name}' → {team1} AND {team2}")
        print()
        print("Note: Conflicts should be rare with manual curation")
    else:
        print()
        print("✅ No conflicts detected")

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
    print()
    print("Principles used:")
    print("- Only names that MOTD commentators actually use")
    print("- Team nicknames included where relevant")
    print("- No algorithmic word-splitting (no 'Aston', 'Hotspur', 'West', etc.)")
    print("- Empty list = always use full name or abbrev from teams JSON")


if __name__ == '__main__':
    main()
