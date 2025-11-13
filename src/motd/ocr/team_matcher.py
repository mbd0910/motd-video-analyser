"""Team name matching with fuzzy logic and fixture awareness."""

import json
from typing import List, Dict, Optional, Set
from pathlib import Path
from rapidfuzz import fuzz, process
import logging

logger = logging.getLogger(__name__)


class TeamMatcher:
    """Matches OCR text against team names using fuzzy matching."""

    def __init__(self, teams_path: Path):
        """
        Initialise team matcher.

        Args:
            teams_path: Path to teams JSON file
        """
        self.teams_path = teams_path
        self.teams_data = self._load_teams(teams_path)
        self.search_index = self._build_search_index()

        logger.info(
            f"Team matcher initialised with {len(self.teams_data)} teams, "
            f"{len(self.search_index)} search terms"
        )

    def _load_teams(self, teams_path: Path) -> List[Dict]:
        """
        Load team data from JSON.

        Args:
            teams_path: Path to teams JSON file

        Returns:
            List of team dicts

        Raises:
            FileNotFoundError: If teams file doesn't exist
            json.JSONDecodeError: If teams file is invalid JSON
        """
        if not teams_path.exists():
            raise FileNotFoundError(f"Teams file not found: {teams_path}")

        with open(teams_path) as f:
            data = json.load(f)

        if 'teams' not in data:
            raise ValueError(f"Teams file missing 'teams' key: {teams_path}")

        logger.debug(f"Loaded {len(data['teams'])} teams from {teams_path}")
        return data['teams']

    def _build_search_index(self) -> Dict[str, str]:
        """
        Build searchable index mapping all name variations to canonical full name.

        Returns:
            Dict mapping search term → full team name

        Example:
            {
                "manchester united": "Manchester United",
                "man utd": "Manchester United",
                "mun": "Manchester United",
                "mufc": "Manchester United",
                ...
            }
        """
        index = {}

        for team in self.teams_data:
            full_name = team['full']

            # Add full name (lowercased for matching)
            index[full_name.lower()] = full_name

            # Add abbreviation (e.g., "Man Utd")
            if 'abbrev' in team:
                index[team['abbrev'].lower()] = full_name

            # Add codes (e.g., "MUN", "MUFC")
            if 'codes' in team:
                for code in team['codes']:
                    index[code.lower()] = full_name

            # Add alternates (e.g., "Man United", "Manchester Utd")
            if 'alternates' in team:
                for alt in team['alternates']:
                    index[alt.lower()] = full_name

        logger.debug(
            f"Built search index with {len(index)} variations for "
            f"{len(self.teams_data)} teams"
        )

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
            threshold: Minimum fuzzy match score (0-1, default 0.75)

        Returns:
            List of matches sorted by confidence (highest first), each dict with:
                - team: Canonical full team name
                - confidence: Match confidence (0-1)
                - matched_text: What text matched
                - fixture_validated: Whether match was in candidate_teams

        Example:
            >>> matcher.match("Man Utd")
            [{'team': 'Manchester United', 'confidence': 0.95,
              'matched_text': 'man utd', 'fixture_validated': False}]

            >>> matcher.match("Brighton", candidate_teams=["Brighton & Hove Albion", "Leeds United"])
            [{'team': 'Brighton & Hove Albion', 'confidence': 0.92,
              'matched_text': 'brighton & hove albion', 'fixture_validated': True}]
        """
        if not text or not text.strip():
            return []

        # Determine search space
        if candidate_teams:
            # Build index for just candidate teams (fixture-aware matching)
            search_index = {
                k: v for k, v in self.search_index.items()
                if v in candidate_teams
            }
            logger.debug(
                f"Fixture-aware matching: searching {len(search_index)} variations "
                f"for {len(candidate_teams)} candidate teams"
            )
        else:
            search_index = self.search_index

        if not search_index:
            logger.warning(
                f"Empty search index for text '{text}' "
                f"(candidate_teams: {candidate_teams})"
            )
            return []

        # Find fuzzy matches using partial_ratio
        # partial_ratio handles partial matches ("Brighton" from "Brighton & Hove Albion")
        matches = process.extract(
            text.lower(),
            search_index.keys(),
            scorer=fuzz.partial_ratio,
            limit=5  # Get top 5 matches
        )

        # Format results
        results = []
        seen_teams = set()

        for matched_key, score, _ in matches:
            # rapidfuzz returns 0-100, normalize threshold (0-1 → 0-100) for comparison
            if score < (threshold * 100):
                continue

            team_name = search_index[matched_key]

            # Skip duplicates (same team matched via different alternates)
            if team_name in seen_teams:
                continue

            seen_teams.add(team_name)

            # Boost confidence if fixture-validated
            confidence = score / 100.0
            if candidate_teams is not None and team_name in candidate_teams:
                # Small boost for fixture validation (max 5%)
                confidence = min(1.0, confidence + 0.05)

            results.append({
                'team': team_name,
                'confidence': confidence,
                'matched_text': matched_key,
                'fixture_validated': candidate_teams is not None and team_name in candidate_teams
            })

            logger.debug(
                f"Matched '{text}' → '{team_name}' "
                f"(confidence: {confidence:.2f}, validated: "
                f"{candidate_teams is not None and team_name in candidate_teams})"
            )

        # Sort by confidence (highest first)
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

        Useful for extracting both home and away teams from scoreboard graphics.

        Args:
            text: OCR-extracted text
            candidate_teams: Optional list of expected team full names
            threshold: Minimum fuzzy match score (0-1)
            max_teams: Maximum number of teams to return (default 2 for home/away)

        Returns:
            Top N teams sorted by confidence, typically 2 for a fixture.

        Example:
            >>> matcher.match_multiple("Brighton 2-0 Leeds", max_teams=2)
            [
                {'team': 'Brighton & Hove Albion', 'confidence': 0.95, ...},
                {'team': 'Leeds United', 'confidence': 0.92, ...}
            ]
        """
        matches = self.match(text, candidate_teams, threshold)
        return matches[:max_teams]

    def get_candidate_teams(self, team_full_names: List[str]) -> List[str]:
        """
        Helper to validate team names exist in the dataset.

        Filters out unknown team names (e.g., from incorrect fixture data).

        Args:
            team_full_names: List of full team names to validate

        Returns:
            List of validated team names (only those that exist in teams data)

        Example:
            >>> matcher.get_candidate_teams([
            ...     "Manchester United",
            ...     "Fake Team FC",
            ...     "Liverpool"
            ... ])
            ["Manchester United", "Liverpool"]
        """
        valid_teams = {team['full'] for team in self.teams_data}
        validated = [name for name in team_full_names if name in valid_teams]

        if len(validated) < len(team_full_names):
            invalid = set(team_full_names) - set(validated)
            logger.warning(
                f"Filtered out {len(invalid)} invalid team names: {invalid}"
            )

        return validated

    def get_all_teams(self) -> List[str]:
        """
        Get list of all team full names.

        Returns:
            List of all canonical team names

        Example:
            >>> matcher.get_all_teams()
            ["Manchester United", "Liverpool", "Arsenal", ...]
        """
        return [team['full'] for team in self.teams_data]
