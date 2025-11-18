#!/usr/bin/env python3
"""
Generate short team names using the algorithmic logic from RunningOrderDetector.

This script extracts what the current _get_team_short_names() method generates
for all 20 Premier League teams, to be reviewed before migrating to teams JSON.
"""

import json
from pathlib import Path


def get_team_short_names(team_name: str) -> list[str]:
    """
    Get common short name variations for a team.

    This is a copy of the logic from running_order_detector.py:339-372
    """
    short_names = []

    # Handle multi-word teams (e.g., "Manchester United" → "United", "Man United")
    parts = team_name.split()
    if len(parts) >= 2:
        # Last word (e.g., "United", "City", "Villa")
        short_names.append(parts[-1])

        # First word (e.g., "Manchester", "Aston")
        if parts[0] not in ['Brighton', 'Crystal']:  # Avoid ambiguous ones
            short_names.append(parts[0])

        # Common abbreviations
        if 'Manchester' in team_name:
            short_names.append('Man ' + parts[-1])  # "Man United", "Man City"
        if 'Tottenham' in team_name:
            short_names.append('Spurs')
        if 'Wolverhampton' in team_name:
            short_names.append('Wolves')
        if 'Brighton' in team_name:
            short_names.append('Brighton')

    return short_names


def main():
    # Load teams JSON
    teams_json_path = Path(__file__).parent.parent / 'data' / 'teams' / 'premier_league_2025_26.json'

    with open(teams_json_path) as f:
        data = json.load(f)

    print("=" * 80)
    print("SHORT TEAM NAMES GENERATED FROM ALGORITHMIC LOGIC")
    print("=" * 80)
    print()

    # Track potential conflicts
    all_short_names = {}
    conflicts = []

    for team in data['teams']:
        full_name = team['full']
        short_names = get_team_short_names(full_name)

        print(f"{full_name:30} → {short_names}")

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
        print("Note: Conflicts aren't necessarily bad - context usually disambiguates")
    else:
        print()
        print("✅ No conflicts detected")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total teams: {len(data['teams'])}")
    print(f"Total short names generated: {len(all_short_names)}")
    print(f"Potential conflicts: {len(conflicts)}")
    print()
    print("Next steps:")
    print("1. Review the short names above")
    print("2. Check if any teams are missing important short names")
    print("3. Decide how to handle conflicts (keep, remove, or add context)")
    print("4. Approve for migration to teams JSON")


if __name__ == '__main__':
    main()
