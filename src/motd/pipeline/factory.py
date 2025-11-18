"""
Service factory for centralized initialization of pipeline components.

Provides single source of truth for creating OCR reader, team matcher,
fixture matcher, and scene processor with configuration from config.yaml.
"""

from pathlib import Path
from typing import Dict, Any

from motd.ocr.reader import OCRReader
from motd.ocr.team_matcher import TeamMatcher
from motd.ocr.fixture_matcher import FixtureMatcher
from motd.ocr.scene_processor import SceneProcessor, EpisodeContext


class ServiceFactory:
    """
    Factory for creating pipeline services from configuration.

    Centralizes initialization logic and eliminates hardcoded file paths.
    All paths are loaded from config.yaml.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize factory with configuration dict.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config

    def create_ocr_reader(self) -> OCRReader:
        """
        Create OCRReader from config.

        Returns:
            Configured OCRReader instance
        """
        return OCRReader(self.config['ocr'])

    def create_team_matcher(self) -> TeamMatcher:
        """
        Create TeamMatcher from config.

        Returns:
            TeamMatcher with loaded team data
        """
        teams_path = Path(self.config['teams']['path'])
        return TeamMatcher(teams_path)

    def create_fixture_matcher(self) -> FixtureMatcher:
        """
        Create FixtureMatcher from config.

        Returns:
            FixtureMatcher with loaded fixtures and episode manifest
        """
        fixtures_path = Path(self.config['fixtures']['path'])
        manifest_path = Path(self.config['episodes']['manifest_path'])
        return FixtureMatcher(fixtures_path, manifest_path)

    def create_scene_processor(self, episode_id: str) -> SceneProcessor:
        """
        Create fully-initialized SceneProcessor for episode.

        Args:
            episode_id: Episode identifier (e.g., "motd_2025-26_2025-11-01")

        Returns:
            SceneProcessor with all dependencies injected
        """
        # Create dependencies
        ocr_reader = self.create_ocr_reader()
        team_matcher = self.create_team_matcher()
        fixture_matcher = self.create_fixture_matcher()

        # Build episode context
        expected_teams = fixture_matcher.get_expected_teams(episode_id)
        expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)

        context = EpisodeContext(
            episode_id=episode_id,
            expected_teams=expected_teams,
            expected_fixtures=expected_fixtures
        )

        # Create and return scene processor
        return SceneProcessor(
            ocr_reader=ocr_reader,
            team_matcher=team_matcher,
            fixture_matcher=fixture_matcher,
            context=context
        )
