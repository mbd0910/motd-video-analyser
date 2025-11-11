# Task 009c: Implement Team Matcher

## Objective
Create fuzzy matching module to match OCR-extracted text against Premier League team names and variations.

## Prerequisites
- Task 009b completed (OCR reader working)
- Team data file: `data/teams/premier_league_2025_26.json`

## Why Fuzzy Matching?

OCR might extract:
- "Man Utd" → Should match "Manchester United"
- "BRIGHTON" → Should match "Brighton & Hove Albion"
- "Spurs" → Should match "Tottenham Hotspur"
- "Forest" → Should match "Nottingham Forest"
- "Brighton 2 - 0 Leeds" → Should extract both "Brighton & Hove Albion" and "Leeds United"

Fuzzy matching handles:
- Case variations (BRIGHTON vs Brighton)
- Abbreviations (Man Utd vs Manchester United)
- Partial matches (Brighton from "Brighton & Hove Albion")
- OCR errors (Leeds vs Leed5)

## Tasks

### 1. Create Team Matcher Module (45-60 min)
- [ ] Create `src/motd/ocr/team_matcher.py` with `TeamMatcher` class
- [ ] Load team data from JSON file
- [ ] Build searchable index of team names and alternates
- [ ] Implement fuzzy matching using `rapidfuzz` or `difflib`
- [ ] Return matches with confidence scores

### 2. Implement Fixture-Aware Matching (30-45 min)
- [ ] Add `candidate_teams` parameter to limit search space
- [ ] When candidates provided (from fixtures), search only those teams
- [ ] When no candidates provided, search all 20 teams
- [ ] Boost confidence when match found in candidate list
- [ ] Return whether match was fixture-validated

### 3. Handle Multiple Teams in Text (20-30 min)
- [ ] OCR might extract "Brighton 2-0 Leeds" as single text
- [ ] Implement logic to find multiple team names in one string
- [ ] Return all matched teams with positions in text
- [ ] Prioritize longer matches (e.g., "Manchester United" over "Manchester")

### 4. Test with Sample OCR Results (30-45 min)
- [ ] Use OCR results from 009b test frames
- [ ] Test matching various team name formats:
  - [ ] Full names: "Manchester United"
  - [ ] Abbreviations: "Man Utd"
  - [ ] Nicknames: "Spurs", "Gunners"
  - [ ] OCR errors: "Br1ghton", "Leed5"
- [ ] Test fixture-aware matching with 2025-11-01 fixtures
- [ ] Verify confidence scores are reasonable (>0.8 for good matches)

## Implementation Details

### Module Structure: `src/motd/ocr/team_matcher.py`

```python
"""Team name matching with fuzzy logic and fixture awareness."""

import json
from typing import List, Dict, Optional, Set
from pathlib import Path
from rapidfuzz import fuzz, process

class TeamMatcher:
    """Matches OCR text against team names using fuzzy matching."""

    def __init__(self, teams_path: Path):
        """
        Initialize team matcher.

        Args:
            teams_path: Path to teams JSON file
        """
        self.teams_data = self._load_teams(teams_path)
        self.search_index = self._build_search_index()

    def _load_teams(self, teams_path: Path) -> List[Dict]:
        """Load team data from JSON."""
        with open(teams_path) as f:
            data = json.load(f)
        return data['teams']

    def _build_search_index(self) -> Dict[str, str]:
        """
        Build searchable index mapping all name variations to canonical full name.

        Returns:
            Dict mapping search term → full team name
        """
        index = {}

        for team in self.teams_data:
            full_name = team['full']

            # Add full name
            index[full_name.lower()] = full_name

            # Add abbreviation
            if 'abbrev' in team:
                index[team['abbrev'].lower()] = full_name

            # Add codes
            if 'codes' in team:
                for code in team['codes']:
                    index[code.lower()] = full_name

            # Add alternates
            if 'alternates' in team:
                for alt in team['alternates']:
                    index[alt.lower()] = full_name

        return index

    def match(
        self,
        text: str,
        candidate_teams: Optional[List[str]] = None,
        threshold: float = 0.75
    ) -> List[Dict]:
        """
        Match text against team names using fuzzy matching.

        Args:
            text: OCR-extracted text
            candidate_teams: Optional list of expected team full names (from fixtures)
            threshold: Minimum fuzzy match score (0-1)

        Returns:
            List of matches, each dict with:
                - team: Canonical full team name
                - confidence: Match confidence (0-1)
                - matched_text: What text matched
                - fixture_validated: Whether match was in candidate_teams
        """
        if not text or not text.strip():
            return []

        # Determine search space
        if candidate_teams:
            # Build index for just candidate teams
            search_index = {
                k: v for k, v in self.search_index.items()
                if v in candidate_teams
            }
        else:
            search_index = self.search_index

        # Find fuzzy matches
        matches = process.extract(
            text.lower(),
            search_index.keys(),
            scorer=fuzz.partial_ratio,
            limit=5
        )

        # Format results
        results = []
        seen_teams = set()

        for matched_key, score, _ in matches:
            if score < (threshold * 100):  # rapidfuzz scores are 0-100
                continue

            team_name = search_index[matched_key]

            # Skip duplicates (same team matched via different alternates)
            if team_name in seen_teams:
                continue

            seen_teams.add(team_name)

            results.append({
                'team': team_name,
                'confidence': score / 100.0,
                'matched_text': matched_key,
                'fixture_validated': candidate_teams is not None and team_name in candidate_teams
            })

        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)

        return results

    def match_multiple(
        self,
        text: str,
        candidate_teams: Optional[List[str]] = None,
        threshold: float = 0.75,
        max_teams: int = 2
    ) -> List[Dict]:
        """
        Find multiple team names in text (e.g., "Brighton 2-0 Leeds").

        Returns top N teams, typically 2 for a fixture (home and away).
        """
        matches = self.match(text, candidate_teams, threshold)
        return matches[:max_teams]

    def get_candidate_teams(self, team_full_names: List[str]) -> List[str]:
        """
        Helper to validate team names exist.

        Args:
            team_full_names: List of full team names

        Returns:
            List of validated team names (filters out unknowns)
        """
        valid_teams = {team['full'] for team in self.teams_data}
        return [name for name in team_full_names if name in valid_teams]
```

### Test Script Example

Create `scripts/test_team_matcher.py`:

```python
"""Test team matcher with various text formats."""

from pathlib import Path
from src.motd.ocr.team_matcher import TeamMatcher

# Initialize matcher
teams_path = Path('data/teams/premier_league_2025_26.json')
matcher = TeamMatcher(teams_path)

# Test cases
test_texts = [
    "Manchester United",
    "Man Utd",
    "BRIGHTON",
    "Brighton 2-0 Leeds",
    "Spurs",
    "Forest",
    "Br1ghton",  # OCR error
    "The Gunners",
]

print("=== Testing Team Matching ===\n")

for text in test_texts:
    print(f"Input: '{text}'")
    matches = matcher.match(text)

    if matches:
        for match in matches[:2]:  # Show top 2
            print(f"  → {match['team']} (confidence: {match['confidence']:.2f})")
    else:
        print("  → No matches")
    print()

# Test fixture-aware matching
print("\n=== Testing Fixture-Aware Matching ===\n")

candidates = [
    "Brighton & Hove Albion",
    "Leeds United"
]

text = "Brighton 2 Leeds 0"
print(f"Input: '{text}'")
print(f"Expected teams: {candidates}")

matches = matcher.match_multiple(text, candidate_teams=candidates)
for match in matches:
    print(f"  → {match['team']}")
    print(f"     Confidence: {match['confidence']:.2f}")
    print(f"     Fixture validated: {match['fixture_validated']}")
```

## Success Criteria
- [ ] `src/motd/ocr/team_matcher.py` created with TeamMatcher class
- [ ] Loads team data from JSON successfully
- [ ] Fuzzy matching works for abbreviations (Man Utd → Manchester United)
- [ ] Fuzzy matching works for nicknames (Spurs → Tottenham Hotspur)
- [ ] Fuzzy matching handles OCR errors (Br1ghton → Brighton & Hove Albion)
- [ ] Fixture-aware matching limits search space to candidate teams
- [ ] Can find multiple teams in one text string
- [ ] Confidence scores are reasonable (>0.8 for good matches, >0.9 for exact)
- [ ] Returns fixture_validated flag correctly
- [ ] Code follows Python guidelines (type hints, docstrings)

## Estimated Time
1-1.5 hours:
- Implementation: 45-60 min
- Fixture-aware logic: 30-45 min
- Multiple team handling: 20-30 min
- Testing: 30-45 min

## Dependencies
```bash
# Add to requirements.txt if not present
rapidfuzz==3.5.2
```

Install with:
```bash
pip install rapidfuzz
```

## Notes
- **rapidfuzz vs difflib**: rapidfuzz is 10-100x faster, use it for 810 frames
- **Threshold tuning**: 0.75 is conservative, might need adjustment based on testing
- **Fixture-aware boost**: When candidates provided, can lower threshold slightly (more confident in context)
- **Partial matching**: "Brighton" from "Brighton & Hove Albion" should score high (partial_ratio)

## Output Files
- `src/motd/ocr/team_matcher.py` (new module)
- `scripts/test_team_matcher.py` (optional test script)

## Next Task
[009d-implement-fixture-matcher.md](009d-implement-fixture-matcher.md) - Fixture validation and confidence boosting
