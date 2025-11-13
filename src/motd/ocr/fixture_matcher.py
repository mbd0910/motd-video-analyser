"""Fixture matching for validating OCR results against expected matches."""

import json
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FixtureMatcher:
    """Validates OCR-detected teams against expected fixtures."""

    def __init__(self, fixtures_path: Path, manifest_path: Path):
        """
        Initialise fixture matcher.

        Args:
            fixtures_path: Path to fixtures JSON
            manifest_path: Path to episode manifest JSON

        Raises:
            FileNotFoundError: If files don't exist
            ValueError: If JSON structure is invalid
        """
        self.fixtures_path = fixtures_path
        self.manifest_path = manifest_path

        self.fixtures = self._load_fixtures(fixtures_path)
        self.manifest = self._load_manifest(manifest_path)

        # Build lookup indices for fast access
        self.fixtures_by_id = {f['match_id']: f for f in self.fixtures}
        self.episodes_by_id = {e['episode_id']: e for e in self.manifest['episodes']}

        logger.info(
            f"Fixture matcher initialised: {len(self.fixtures)} fixtures, "
            f"{len(self.episodes_by_id)} episodes"
        )

    def _load_fixtures(self, path: Path) -> List[Dict]:
        """
        Load fixtures from JSON.

        Args:
            path: Path to fixtures JSON file

        Returns:
            List of fixture dicts

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON structure is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Fixtures file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        if 'fixtures' not in data:
            raise ValueError(
                f"Fixtures file missing 'fixtures' key: {path}"
            )

        fixtures = data['fixtures']
        logger.debug(f"Loaded {len(fixtures)} fixtures from {path}")
        return fixtures

    def _load_manifest(self, path: Path) -> Dict:
        """
        Load episode manifest from JSON.

        Args:
            path: Path to episode manifest JSON file

        Returns:
            Manifest dict

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON structure is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Episode manifest not found: {path}")

        with open(path) as f:
            data = json.load(f)

        if 'episodes' not in data:
            raise ValueError(f"Manifest missing 'episodes' key: {path}")

        logger.debug(
            f"Loaded manifest with {len(data['episodes'])} episodes from {path}"
        )
        return data

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
            available = list(self.episodes_by_id.keys())
            raise ValueError(
                f"Episode not found: {episode_id}. "
                f"Available episodes: {available}"
            )

        episode = self.episodes_by_id[episode_id]
        match_ids = episode['expected_matches']

        fixtures = []
        missing_matches = []

        for match_id in match_ids:
            if match_id in self.fixtures_by_id:
                fixtures.append(self.fixtures_by_id[match_id])
            else:
                missing_matches.append(match_id)

        if missing_matches:
            logger.warning(
                f"Episode {episode_id} expects matches not found in fixtures: "
                f"{missing_matches}"
            )

        logger.debug(
            f"Episode {episode_id}: found {len(fixtures)}/{len(match_ids)} fixtures"
        )

        return fixtures

    def get_expected_teams(self, episode_id: str) -> List[str]:
        """
        Get flat list of all expected team names for episode.

        Args:
            episode_id: Episode identifier

        Returns:
            Sorted list of team full names (home + away from all fixtures)

        Raises:
            ValueError: If episode_id not found
        """
        fixtures = self.get_expected_fixtures(episode_id)

        teams = set()
        for fixture in fixtures:
            teams.add(fixture['home_team'])
            teams.add(fixture['away_team'])

        logger.debug(
            f"Episode {episode_id}: {len(teams)} expected teams from "
            f"{len(fixtures)} fixtures"
        )

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

        Example:
            >>> matcher.validate_teams(["Brighton & Hove Albion", "Leeds United"], episode_id)
            {
                'expected_teams': ['Arsenal', 'Brighton & Hove Albion', ...],
                'validated_teams': ['Brighton & Hove Albion', 'Leeds United'],
                'unexpected_teams': [],
                'confidence_boost': 1.1
            }
        """
        expected = set(self.get_expected_teams(episode_id))
        detected = set(detected_teams)

        validated = detected & expected  # Intersection: teams that are expected
        unexpected = detected - expected  # Teams detected but not expected

        # Boost confidence if:
        # - At least one team validates
        # - No unexpected teams detected (clean match)
        confidence_boost = 1.1 if validated and not unexpected else 1.0

        logger.debug(
            f"Validation for {episode_id}: "
            f"{len(validated)} validated, {len(unexpected)} unexpected"
        )

        if unexpected:
            logger.warning(
                f"Unexpected teams detected for {episode_id}: {sorted(unexpected)}"
            )

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

        Useful when OCR extracts both teams from a scoreboard (e.g., "Brighton 2-0 Leeds").

        Args:
            team1: First team full name
            team2: Second team full name
            episode_id: Episode identifier

        Returns:
            Fixture dict if found, None otherwise

        Example:
            >>> matcher.identify_fixture("Brighton & Hove Albion", "Leeds United", episode_id)
            {
                'match_id': 'PL_2025-26_GW10_001',
                'home_team': 'Brighton & Hove Albion',
                'away_team': 'Leeds United',
                'score': '2-0',
                ...
            }
        """
        fixtures = self.get_expected_fixtures(episode_id)

        for fixture in fixtures:
            home, away = fixture['home_team'], fixture['away_team']

            # Match regardless of order (could be home/away or away/home)
            # OCR doesn't know which team is home vs away
            if (team1 == home and team2 == away) or (team1 == away and team2 == home):
                logger.debug(
                    f"Identified fixture: {fixture['match_id']} "
                    f"({home} vs {away})"
                )
                return fixture

        logger.debug(
            f"No fixture found for {team1} vs {team2} in episode {episode_id}"
        )
        return None

    def get_fixture_by_id(self, match_id: str) -> Optional[Dict]:
        """
        Get fixture by match_id.

        Args:
            match_id: Match identifier (e.g., "PL_2025-26_GW10_001")

        Returns:
            Fixture dict if found, None otherwise
        """
        return self.fixtures_by_id.get(match_id)

    def get_all_fixtures(self) -> List[Dict]:
        """
        Get all fixtures in the dataset.

        Returns:
            List of all fixture dicts
        """
        return self.fixtures

    def get_all_episodes(self) -> List[Dict]:
        """
        Get all episodes in the manifest.

        Returns:
            List of all episode dicts
        """
        return self.manifest['episodes']
