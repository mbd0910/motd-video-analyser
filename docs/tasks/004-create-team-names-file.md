# Task 004: Create Team Names File

## Objective
Create a JSON file with all Premier League 2025/26 team names and variations for matching against OCR/transcription results.

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

## Validation Checklist
- [ ] File created at `data/teams/premier_league_2025_26.json`
- [ ] JSON is valid (Python can parse it)
- [ ] All 20 Premier League teams present (+ Charlton as bonus)

## Estimated Time
5 minutes

## Notes
- The `alternates` field includes common variations used in commentary
- The `code` field is the standard 3-letter abbreviation
- You can add more alternates if you notice OCR/transcription missing teams


## Future Enhancements
- Add pronunciation variations for Whisper ("Man U", "Man Yoo", etc.)
- Separate files for Championship, League One, League Two

## Next Task
[005-create-config-file.md](005-create-config-file.md)
