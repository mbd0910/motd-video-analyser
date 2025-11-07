# Task 004: Create Team Names, Fixtures, and Episode Manifest

## Objective
Create JSON files for team names, match fixtures, and episode manifest to enable fixture-aware team identification.

## Prerequisites
- [003-install-python-dependencies.md](003-install-python-dependencies.md) completed

## Steps

### 1. Create the Team Names JSON
```bash
cat > data/teams/premier_league_2025_26.json << 'EOF'
{
  "teams": [
    {
      "full": "Arsenal",
      "abbrev": "Arsenal",
      "code": "ARS",
      "alternates": ["The Gunners", "Gunners"]
    },
    {
      "full": "Aston Villa",
      "abbrev": "Aston Villa",
      "code": "AVL",
      "alternates": ["Villa"]
    },
    {
      "full": "Bournemouth",
      "abbrev": "Bournemouth",
      "code": "BOU",
      "alternates": ["The Cherries", "Cherries", "AFC Bournemouth"]
    },
    {
      "full": "Brentford",
      "abbrev": "Brentford",
      "code": "BRE",
      "alternates": ["The Bees", "Bees"]
    },
    {
      "full": "Brighton & Hove Albion",
      "abbrev": "Brighton",
      "code": "BHA",
      "alternates": ["Brighton", "The Seagulls", "Seagulls"]
    },
    {
      "full": "Burnley",
      "abbrev": "Burnley",
      "code": "BUR",
      "alternates": ["The Clarets", "Clarets"]
    },
    {
      "full": "Chelsea",
      "abbrev": "Chelsea",
      "code": "CHE",
      "alternates": ["The Blues", "Blues"]
    },
    {
      "full": "Crystal Palace",
      "abbrev": "Crystal Palace",
      "code": "CRY",
      "alternates": ["Palace", "The Eagles", "Eagles"]
    },
    {
      "full": "Everton",
      "abbrev": "Everton",
      "code": "EVE",
      "alternates": ["The Toffees", "Toffees"]
    },
    {
      "full": "Fulham",
      "abbrev": "Fulham",
      "code": "FUL",
      "alternates": ["The Cottagers", "Cottagers"]
    },
    {
      "full": "Leeds United",
      "abbrev": "Leeds",
      "code": "LEE",
      "alternates": ["Leeds", "The Whites", "Whites", "United"]
    },
    {
      "full": "Liverpool",
      "abbrev": "Liverpool",
      "code": "LIV",
      "alternates": ["The Reds", "Reds"]
    },
    {
      "full": "Manchester City",
      "abbrev": "Man City",
      "code": "MCI",
      "alternates": ["Man City", "City", "The Citizens", "Citizens"]
    },
    {
      "full": "Manchester United",
      "abbrev": "Man Utd",
      "code": "MUN",
      "alternates": ["Man Utd", "Man United", "United", "The Red Devils", "Red Devils"]
    },
    {
      "full": "Newcastle United",
      "abbrev": "Newcastle",
      "code": "NEW",
      "alternates": ["Newcastle", "The Magpies", "Magpies"]
    },
    {
      "full": "Nottingham Forest",
      "abbrev": "Nott'm Forest",
      "code": "NFO",
      "alternates": ["Forest", "Nottm Forest", "Notts Forest", "Nott'm Forest"]
    },
    {
      "full": "Sunderland",
      "abbrev": "Sunderland",
      "code": "SUN",
      "alternates": ["The Black Cats", "Black Cats"]
    },
    {
      "full": "Tottenham Hotspur",
      "abbrev": "Tottenham",
      "code": "TOT",
      "alternates": ["Spurs", "Tottenham", "The Lilywhites", "Hotspur"]
    },
    {
      "full": "West Ham United",
      "abbrev": "West Ham",
      "code": "WHU",
      "alternates": ["West Ham", "The Hammers", "Hammers"]
    },
    {
      "full": "Wolverhampton Wanderers",
      "abbrev": "Wolves",
      "code": "WOL",
      "alternates": ["Wolves", "Wanderers"]
    }
  ]
}
EOF
```

### 2. Validate JSON
```bash
python -c "import json; data = json.load(open('data/teams/premier_league_2025_26.json')); print(f'Loaded {len(data[\"teams\"])} teams')"
```

Should output: `Loaded 20 teams`

### 3. Create Fixtures JSON
Create `data/fixtures/premier_league_2025_26.json` with match schedules for the gameweeks you're analyzing:
```bash
cat > data/fixtures/premier_league_2025_26.json << 'EOF'
{
  "season": "2025-26",
  "competition": "Premier League",
  "gameweeks": [
    {
      "gameweek": 1,
      "matches": [
        {
          "match_id": "2025-08-16-manutd-fulham",
          "date": "2025-08-16",
          "home_team": "Manchester United",
          "away_team": "Fulham",
          "kickoff": "20:00",
          "final_score": {"home": 1, "away": 0}
        }
        // ... add all fixtures for gameweeks you're analyzing
      ]
    }
  ]
}
EOF
```

**Note**: You'll populate this manually with actual fixture data. You can provide screenshots or copy-paste fixture lists, and I'll help format them into JSON.

### 4. Create Episode Manifest
Create `data/episodes/episode_manifest.json` to map video files to fixtures:
```bash
cat > data/episodes/episode_manifest.json << 'EOF'
{
  "episodes": [
    {
      "episode_id": "motd-2025-08-17",
      "video_filename": "MOTD_2025_08_17_S57E01.mp4",
      "video_source_url": "https://www.bbc.co.uk/iplayer/episode/...",
      "broadcast_date": "2025-08-17",
      "gameweek": 1,
      "expected_matches": [
        "2025-08-16-manutd-fulham"
        // ... list all match_ids expected in this episode
      ],
      "notes": "Opening weekend"
    }
  ]
}
EOF
```

### 5. Validate All Files
```bash
python -c "
import json
teams = json.load(open('data/teams/premier_league_2025_26.json'))
fixtures = json.load(open('data/fixtures/premier_league_2025_26.json'))
episodes = json.load(open('data/episodes/episode_manifest.json'))
print(f'✓ {len(teams[\"teams\"])} teams loaded')
print(f'✓ {len(fixtures[\"gameweeks\"])} gameweeks loaded')
print(f'✓ {len(episodes[\"episodes\"])} episodes loaded')
"
```

## Validation Checklist
- [ ] File created at `data/teams/premier_league_2025_26.json`
- [ ] File created at `data/fixtures/premier_league_2025_26.json`
- [ ] File created at `data/episodes/episode_manifest.json`
- [ ] All JSON files are valid (Python can parse them)
- [ ] All 20 Premier League teams present
- [ ] Fixtures cover all gameweeks you're analyzing
- [ ] Episode manifest links video files to correct fixtures

## Estimated Time
15-20 minutes (including manual fixture entry)

## Notes
- **Fixture data enables fixture-aware matching**: OCR searches only 12-16 teams (from expected fixtures) instead of all 20, improving accuracy from ~85-90% to 95%+
- **Episode manifest enables automation**: The `video_source_url` field allows future integration with yt-dlp for automated downloads
- You can provide fixture data via screenshots/copy-paste and I'll format it into JSON
- The `alternates` field includes common variations used in commentary
- You can add more alternates if you notice OCR/transcription missing teams

## Future Enhancements
- Automate fixture data retrieval via Football-Data.org API
- Add pronunciation variations for Whisper ("Man U", "Man Yoo", etc.)
- Separate files for Championship, League One, League Two

## Next Task
[005-create-config-file.md](005-create-config-file.md)
