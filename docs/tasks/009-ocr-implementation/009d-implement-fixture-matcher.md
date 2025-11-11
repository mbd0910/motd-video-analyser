# Task 009d: Implement Fixture Matcher

## Objective
Create fixture matcher to validate OCR results against expected fixtures for an episode, boosting confidence and reducing false positives.

## Prerequisites
- Task 009c completed (team matcher working)
- Episode manifest: `data/episodes/episode_manifest.json` (created in 009a)
- Fixtures data: `data/fixtures/premier_league_2025_26.json`

## Why Fixture Matching?

**Problem**: OCR might detect team names that aren't in this week's episode
- False positive: Detects "Arsenal" but they're not in this week's fixtures
- Ambiguous text: "Manchester" could be Man City or Man Utd - fixtures tell us which is expected

**Solution**: Fixture-aware validation
- Load expected fixtures for episode
- Validate OCR results against expected teams
- Boost confidence when fixture confirms OCR
- Flag unexpected teams as warnings

**Example**:
- Episode: 2025-11-01
- Expected fixtures: Brighton vs Leeds, Burnley vs Arsenal, etc. (7 matches = 14 teams)
- OCR detects "Brighton" → Fixture matcher confirms: ✅ Brighton expected
- OCR detects "West Ham" → Fixture matcher flags: ⚠️ West Ham not expected this week

## Tasks

### 1. Create Fixture Matcher Module (45-60 min)
- [ ] Create `src/motd/ocr/fixture_matcher.py` with `FixtureMatcher` class
- [ ] Load fixtures data from JSON
- [ ] Load episode manifest from JSON
- [ ] Get expected fixtures for given episode_id
- [ ] Extract expected teams from fixtures (home + away)
- [ ] Provide candidate teams list for team matcher

### 2. Implement Match Validation (30-45 min)
- [ ] Validate OCR-detected teams against expected teams
- [ ] Boost confidence when team is expected
- [ ] Flag teams not in expected fixtures
- [ ] Identify likely fixture from detected teams (if home + away both found)

### 3. Create Fixture Lookup Helpers (20-30 min)
- [ ] Get fixture by match_id
- [ ] Get fixture by team names (home + away)
- [ ] Get all expected teams for episode (flat list)
- [ ] Format fixture information for OCR output

### 4. Test with 2025-11-01 Episode (20-30 min)
- [ ] Load episode manifest and fixtures
- [ ] Verify 7 expected matches loaded correctly
- [ ] Test validation with expected teams (Brighton, Leeds, etc.)
- [ ] Test validation with unexpected team (West Ham, etc.)
- [ ] Verify confidence boost logic works

## Implementation Details

### Module Structure: `src/motd/ocr/fixture_matcher.py`

```python
"""Fixture matching for validating OCR results against expected matches."""

import json
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path

class FixtureMatcher:
    """Validates OCR-detected teams against expected fixtures."""

    def __init__(self, fixtures_path: Path, manifest_path: Path):
        """
        Initialize fixture matcher.

        Args:
            fixtures_path: Path to fixtures JSON
            manifest_path: Path to episode manifest JSON
        """
        self.fixtures = self._load_fixtures(fixtures_path)
        self.manifest = self._load_manifest(manifest_path)

        # Build lookup indices
        self.fixtures_by_id = {f['match_id']: f for f in self.fixtures}
        self.episodes_by_id = {e['episode_id']: e for e in self.manifest['episodes']}

    def _load_fixtures(self, path: Path) -> List[Dict]:
        """Load fixtures from JSON."""
        with open(path) as f:
            data = json.load(f)
        return data['fixtures']

    def _load_manifest(self, path: Path) -> Dict:
        """Load episode manifest from JSON."""
        with open(path) as f:
            return json.load(f)

    def get_expected_fixtures(self, episode_id: str) -> List[Dict]:
        """
        Get expected fixtures for an episode.

        Args:
            episode_id: Episode identifier (e.g., "motd_2025-26_2025-11-01")

        Returns:
            List of fixture dicts with match details

        Raises:
            ValueError: If episode_id not found in manifest
        """
        if episode_id not in self.episodes_by_id:
            raise ValueError(f"Episode not found: {episode_id}")

        episode = self.episodes_by_id[episode_id]
        match_ids = episode['expected_matches']

        fixtures = []
        for match_id in match_ids:
            if match_id in self.fixtures_by_id:
                fixtures.append(self.fixtures_by_id[match_id])
            else:
                # Warning: expected match not found in fixtures
                pass

        return fixtures

    def get_expected_teams(self, episode_id: str) -> List[str]:
        """
        Get flat list of all expected team names for episode.

        Returns:
            List of team full names (home + away from all fixtures)
        """
        fixtures = self.get_expected_fixtures(episode_id)

        teams = set()
        for fixture in fixtures:
            teams.add(fixture['home_team'])
            teams.add(fixture['away_team'])

        return sorted(teams)

    def validate_teams(
        self,
        detected_teams: List[str],
        episode_id: str
    ) -> Dict:
        """
        Validate detected teams against expected fixtures.

        Args:
            detected_teams: List of team full names from OCR/team matcher
            episode_id: Episode identifier

        Returns:
            Dict with:
                - expected_teams: All expected teams for episode
                - validated_teams: Detected teams that are expected
                - unexpected_teams: Detected teams not in fixtures
                - confidence_boost: Multiplier for confidence (e.g., 1.1 if validated)
        """
        expected = set(self.get_expected_teams(episode_id))
        detected = set(detected_teams)

        validated = detected & expected  # Intersection
        unexpected = detected - expected  # Detected but not expected

        # Boost confidence if teams validate
        confidence_boost = 1.1 if validated and not unexpected else 1.0

        return {
            'expected_teams': sorted(expected),
            'validated_teams': sorted(validated),
            'unexpected_teams': sorted(unexpected),
            'confidence_boost': confidence_boost
        }

    def identify_fixture(
        self,
        team1: str,
        team2: str,
        episode_id: str
    ) -> Optional[Dict]:
        """
        Identify fixture from two team names.

        Args:
            team1: First team full name
            team2: Second team full name
            episode_id: Episode identifier

        Returns:
            Fixture dict if found, None otherwise
        """
        fixtures = self.get_expected_fixtures(episode_id)

        for fixture in fixtures:
            home, away = fixture['home_team'], fixture['away_team']

            # Match regardless of order (could be home/away or away/home)
            if (team1 == home and team2 == away) or (team1 == away and team2 == home):
                return fixture

        return None

    def get_fixture_by_id(self, match_id: str) -> Optional[Dict]:
        """Get fixture by match_id."""
        return self.fixtures_by_id.get(match_id)
```

### Integration with Team Matcher

In OCR pipeline, use fixture matcher to provide candidates:

```python
from src.motd.ocr.fixture_matcher import FixtureMatcher
from src.motd.ocr.team_matcher import TeamMatcher

# Initialize
fixture_matcher = FixtureMatcher(
    Path('data/fixtures/premier_league_2025_26.json'),
    Path('data/episodes/episode_manifest.json')
)

team_matcher = TeamMatcher(Path('data/teams/premier_league_2025_26.json'))

# Get expected teams for episode
episode_id = "motd_2025-26_2025-11-01"
candidate_teams = fixture_matcher.get_expected_teams(episode_id)

# Use candidates in team matching (limits search space)
ocr_text = "Brighton 2-0 Leeds"
matches = team_matcher.match_multiple(
    ocr_text,
    candidate_teams=candidate_teams
)

# Validate results
detected_teams = [m['team'] for m in matches]
validation = fixture_matcher.validate_teams(detected_teams, episode_id)

print(f"Validated: {validation['validated_teams']}")
print(f"Unexpected: {validation['unexpected_teams']}")
print(f"Confidence boost: {validation['confidence_boost']}")
```

### Test Script Example

Create `scripts/test_fixture_matcher.py`:

```python
"""Test fixture matcher with 2025-11-01 episode."""

from pathlib import Path
from src.motd.ocr.fixture_matcher import FixtureMatcher

# Initialize
matcher = FixtureMatcher(
    Path('data/fixtures/premier_league_2025_26.json'),
    Path('data/episodes/episode_manifest.json')
)

episode_id = "motd_2025-26_2025-11-01"

print("=== Expected Fixtures ===\n")
fixtures = matcher.get_expected_fixtures(episode_id)
for fixture in fixtures:
    print(f"{fixture['home_team']} vs {fixture['away_team']}")

print("\n=== Expected Teams ===\n")
teams = matcher.get_expected_teams(episode_id)
print(f"Total teams: {len(teams)}")
for team in teams:
    print(f"  - {team}")

print("\n=== Validation Tests ===\n")

# Test with expected teams
detected = ["Brighton & Hove Albion", "Leeds United"]
validation = matcher.validate_teams(detected, episode_id)
print(f"Detected: {detected}")
print(f"Validated: {validation['validated_teams']}")
print(f"Unexpected: {validation['unexpected_teams']}")
print(f"Confidence boost: {validation['confidence_boost']}")

# Test with unexpected team
print("\n")
detected = ["Brighton & Hove Albion", "West Ham United"]
validation = matcher.validate_teams(detected, episode_id)
print(f"Detected: {detected}")
print(f"Validated: {validation['validated_teams']}")
print(f"Unexpected: {validation['unexpected_teams']}")
print(f"Confidence boost: {validation['confidence_boost']}")

# Test fixture identification
print("\n=== Fixture Identification ===\n")
fixture = matcher.identify_fixture(
    "Brighton & Hove Albion",
    "Leeds United",
    episode_id
)
if fixture:
    print(f"Found: {fixture['match_id']}")
    print(f"Score: {fixture['score']}")
```

## Success Criteria
- [ ] `src/motd/ocr/fixture_matcher.py` created with FixtureMatcher class
- [ ] Loads fixtures and episode manifest successfully
- [ ] Gets expected fixtures for episode (7 matches for 2025-11-01)
- [ ] Gets expected teams list (14 teams for 2025-11-01)
- [ ] Validates detected teams against expected teams
- [ ] Identifies unexpected teams correctly
- [ ] Applies confidence boost when teams validate
- [ ] Can identify fixture from two team names
- [ ] Handles missing episode_id gracefully (raises ValueError)
- [ ] Code follows Python guidelines (type hints, docstrings)

## Estimated Time
1 hour:
- Implementation: 45-60 min
- Match validation: 30-45 min
- Helpers: 20-30 min
- Testing: 20-30 min

## Notes
- **Episode manifest is critical**: Links episode_id to expected match_ids
- **Confidence boost factor**: 1.1 (10% boost) is conservative, can tune based on results
- **Unexpected teams**: Could be valid (e.g., mention of other match in studio discussion) or false positive
- **Fixture order doesn't matter**: Brighton vs Leeds = Leeds vs Brighton for matching

## Output Files
- `src/motd/ocr/fixture_matcher.py` (new module)
- `scripts/test_fixture_matcher.py` (optional test script)

## Next Task
[009e-create-ocr-cli.md](009e-create-ocr-cli.md) - Wire up all components into CLI command
