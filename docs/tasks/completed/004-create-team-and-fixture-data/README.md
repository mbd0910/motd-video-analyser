# Task 004: Create Team Names, Fixtures, and Episode Manifest

## Objective
Create JSON files for team names, match fixtures, and episode manifest to enable fixture-aware team identification.

## Prerequisites
- [003-install-python-dependencies.md](003-install-python-dependencies.md) completed

## Implementation Decisions
- **Changed `code` to `codes` array**: Support multiple 3-letter code variations (e.g., Forest: NFO/FOR/NOT)
- **Removed gameweek grouping**: Flat date-indexed fixture structure (gameweeks not needed for matching)
- **Removed `video_filename` from manifest**: Keeps manifest focused on metadata, not implementation details
- **Episode notes describe context**: Not analysis results (which we're trying to discover)

## Steps

### 1. Create missing directories
- [x] Create `data/fixtures/` directory
- [x] Create `data/episodes/` directory

### 2. Create the Team Names JSON
- [x] Create `data/teams/premier_league_2025_26.json` with all 20 teams
- [x] Each team includes `codes` array (plural) with multiple 3-letter variations

Example structure:
```json
{
  "season": "2025-26",
  "competition": "Premier League",
  "teams": [
    {
      "full": "Arsenal",
      "abbrev": "Arsenal",
      "codes": ["ARS"],
      "alternates": ["The Gunners", "Gunners"]
    },
    {
      "full": "Nottingham Forest",
      "abbrev": "Nott'm Forest",
      "codes": ["NFO", "FOR", "NOT"],
      "alternates": ["Forest", "Nottm Forest", "Notts Forest"]
    },
    // ... 17 more teams with similar structure
  ]
}
```

See [data/teams/premier_league_2025_26.json](../../data/teams/premier_league_2025_26.json) for complete file.

### 3. Create Fixtures JSON
- [x] Create `data/fixtures/premier_league_2025_26.json` with flat date-indexed structure
- [x] Populate with 2025-11-01 fixtures (7 matches)

Example structure (flat, no gameweek grouping):
```json
{
  "season": "2025-26",
  "competition": "Premier League",
  "matches": [
    {
      "match_id": "2025-11-01-brighton-leeds",
      "date": "2025-11-01",
      "home_team": "Brighton & Hove Albion",
      "away_team": "Leeds United",
      "kickoff": "15:00",
      "final_score": {"home": 3, "away": 0}
    },
    // ... 6 more matches from 2025-11-01
  ]
}
```

See [data/fixtures/premier_league_2025_26.json](../../data/fixtures/premier_league_2025_26.json) for complete file.

### 4. Create Episode Manifest
- [x] Create `data/episodes/episode_manifest.json` without video_filename or gameweek fields
- [x] Link episode to 7 expected match IDs from fixtures

Example structure:
```json
{
  "season": "2025-26",
  "competition": "Premier League",
  "episodes": [
    {
      "episode_id": "motd-2025-11-01",
      "broadcast_date": "2025-11-01",
      "video_source_url": "https://www.bbc.co.uk/iplayer/episode/m002ltfz/...",
      "expected_matches": [
        "2025-11-01-brighton-leeds",
        // ... 6 more match IDs
      ],
      "notes": "Saturday 3pm/5:30pm/8pm fixtures"
    }
  ]
}
```

See [data/episodes/episode_manifest.json](../../data/episodes/episode_manifest.json) for complete file.

### 5. Validate All Files
- [x] Run comprehensive validation script

```bash
python << 'EOF'
import json

teams = json.load(open('data/teams/premier_league_2025_26.json'))
fixtures = json.load(open('data/fixtures/premier_league_2025_26.json'))
episodes = json.load(open('data/episodes/episode_manifest.json'))

# Validate structure
assert all('codes' in t for t in teams['teams']), "All teams must have 'codes' array"
assert 'gameweeks' not in fixtures, "Fixtures should be flat (no gameweek grouping)"
assert 'video_filename' not in episodes['episodes'][0], "No video_filename in manifest"

# Validate counts
print(f'✓ {len(teams["teams"])} teams loaded')
print(f'✓ {len(fixtures["matches"])} matches loaded')
print(f'✓ {len(episodes["episodes"])} episodes loaded')

# Cross-validate
fixture_ids = {m['match_id'] for m in fixtures['matches']}
episode_ids = set(episodes['episodes'][0]['expected_matches'])
assert episode_ids.issubset(fixture_ids), "All episode matches exist in fixtures"
print(f'✓ All validations passed')
EOF
```

## Validation Checklist
- [x] Directories created: `data/fixtures/`, `data/episodes/`
- [x] File created at `data/teams/premier_league_2025_26.json`
- [x] File created at `data/fixtures/premier_league_2025_26.json`
- [x] File created at `data/episodes/episode_manifest.json`
- [x] All JSON files are valid (Python can parse them)
- [x] All 20 Premier League teams present with `codes` arrays
- [x] Teams use `codes` (plural) not `code` (singular)
- [x] Fixtures use flat date-indexed structure (no gameweek grouping)
- [x] Episode manifest has no `video_filename` or `gameweek` fields
- [x] Episode manifest links to 7 correct match IDs from fixtures
- [x] All fixture team names exist in teams JSON
- [x] Comprehensive validation script passes

## Estimated Time
15-20 minutes (including manual fixture entry)

## Notes
- **`codes` array improvement**: Using plural `codes` instead of singular `code` allows OCR to match multiple 3-letter variations (e.g., Forest can appear as NFO, FOR, or NOT in BBC graphics)
- **Fixture data enables fixture-aware matching**: OCR searches only 14 teams (from day's fixtures) instead of all 20, improving accuracy from ~85-90% to 95%+
- **Flat date-indexed fixtures**: No gameweek grouping needed - fixture lookup by broadcast date is sufficient for matching
- **Episode manifest simplification**: Removed `video_filename` (implementation detail) and `gameweek` (not needed for lookup)
- **Episode notes are for context**: Describe the broadcast (e.g., "Saturday fixtures"), not analysis results we're discovering
- **Extensibility**: More fixtures and episodes can be added to these files as needed

## Future Enhancements
- Automate fixture data retrieval via Football-Data.org API
- Add pronunciation variations for Whisper ("Man U", "Man Yoo", etc.)
- Separate files for Championship, League One, League Two

## Next Task
[005-create-config-file.md](005-create-config-file.md)
