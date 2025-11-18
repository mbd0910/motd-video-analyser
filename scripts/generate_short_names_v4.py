#!/usr/bin/env python3
"""
Generate short team names including both shortened forms AND nicknames.

Based on internet research:
- https://www.sportsunfold.com/english-premier-league-all-team-nicknames/
- ESPN, NBC Sports, BBC Sport usage
- Common abbreviations and official nicknames

Includes both:
1. Short forms (Villa, Spurs, Man City, etc.)
2. Nicknames (The Gunners, The Blues, The Hammers, etc.)
"""

import json
from pathlib import Path


def get_short_names_and_nicknames() -> dict[str, list[str]]:
    """
    Short names AND nicknames based on research.

    It's OK to have duplicates across teams (e.g., "United", "The Blues").
    Context will disambiguate during detection.
    """
    return {
        "Arsenal": ["The Gunners", "Gunners"],

        "Aston Villa": ["Villa", "The Villans", "Villans"],

        "Bournemouth": ["The Cherries", "Cherries"],

        "Brentford": ["The Bees", "Bees"],

        "Brighton & Hove Albion": ["Brighton", "The Seagulls", "Seagulls", "The Albion"],

        "Burnley": ["The Clarets", "Clarets"],

        "Chelsea": ["The Blues", "Blues"],

        "Crystal Palace": ["Palace", "The Eagles", "Eagles", "The Glaziers"],

        "Everton": ["The Toffees", "Toffees", "The Blues", "Blues"],

        "Fulham": ["The Cottagers", "Cottagers"],

        "Leeds United": ["Leeds", "The Whites", "Whites", "The Peacocks", "United"],

        "Liverpool": ["The Reds", "Reds"],

        "Manchester City": ["Man City", "City", "The Citizens", "Citizens", "The Sky Blues", "Cityzens"],

        "Manchester United": ["Man United", "Man Utd", "United", "The Red Devils", "Red Devils"],

        "Newcastle United": ["Newcastle", "The Magpies", "Magpies", "United"],

        "Nottingham Forest": ["Forest", "Nottm Forest", "Nottingham"],

        "Sunderland": ["The Black Cats", "Black Cats"],

        "Tottenham Hotspur": ["Tottenham", "Spurs", "The Lilywhites"],

        "West Ham United": ["West Ham", "The Hammers", "Hammers", "The Irons", "Irons", "United"],

        "Wolverhampton Wanderers": ["Wolves", "The Wanderers", "Wanderers"],
    }


def main():
    # Load teams JSON
    teams_json_path = Path(__file__).parent.parent / 'data' / 'teams' / 'premier_league_2025_26.json'

    with open(teams_json_path) as f:
        data = json.load(f)

    short_names_map = get_short_names_and_nicknames()

    print("=" * 80)
    print("SHORT NAMES + NICKNAMES (2025/26 season)")
    print("=" * 80)
    print()
    print("Includes:")
    print("- Shortened forms (Villa, Spurs, Man City, etc.)")
    print("- Official nicknames (The Gunners, The Blues, etc.)")
    print("- Common variations from sports media")
    print()

    # Track shared names
    from collections import defaultdict
    name_to_teams = defaultdict(list)

    for team in data['teams']:
        full_name = team['full']
        short_names = short_names_map.get(full_name, [])

        print(f"{full_name:30} → {short_names}")

        for short_name in short_names:
            name_to_teams[short_name].append(full_name)

    # Report shared names
    shared = {name: teams for name, teams in name_to_teams.items() if len(teams) > 1}

    if shared:
        print()
        print("=" * 80)
        print("SHARED NAMES (context will disambiguate)")
        print("=" * 80)
        print()
        for name, teams in sorted(shared.items()):
            print(f"  '{name}' → {', '.join(teams)}")
    else:
        print()
        print("✅ No shared names")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total teams: {len(data['teams'])}")
    print(f"Total short names/nicknames: {sum(len(sn) for sn in short_names_map.values())}")
    print(f"Shared names: {len(shared)}")
    print()
    print("Note: Shared names are OK - transcript context will disambiguate")
    print("      (e.g., 'United' works when one team is in context)")


if __name__ == '__main__':
    main()
