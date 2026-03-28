"""Fixture loading for MOTD analysis pipeline."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from motd.models import Fixture, Score

DEFAULT_FIXTURES_PATH = Path("data/fixtures/premier_league_2025_26.json")


class FixtureProvider(ABC):
    """Interface for loading fixture data."""

    @abstractmethod
    def get_fixtures_for_date(self, date: str) -> list[Fixture]:
        """Return fixtures for a given broadcast date (YYYY-MM-DD)."""

    @abstractmethod
    def get_all_fixtures(self) -> list[Fixture]:
        """Return all available fixtures."""


class FileFixtureProvider(FixtureProvider):
    """Loads fixtures from a JSON file on disk."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def get_all_fixtures(self) -> list[Fixture]:
        if not self.path.exists():
            raise FileNotFoundError(f"Fixtures file not found: {self.path}")
        data = json.loads(self.path.read_text())
        return [self._parse_fixture(f) for f in data.get("fixtures", [])]

    def get_fixtures_for_date(self, date: str) -> list[Fixture]:
        return [f for f in self.get_all_fixtures() if f.date == date]

    @staticmethod
    def _parse_fixture(raw: dict) -> Fixture:  # type: ignore[type-arg]
        score = None
        raw_score = raw.get("final_score")
        if raw_score:
            score = Score(home=raw_score["home"], away=raw_score["away"])
        return Fixture(
            match_id=raw["match_id"],
            date=raw["date"],
            home_team=raw["home_team"],
            away_team=raw["away_team"],
            venue=raw.get("venue", ""),
            score=score,
        )
