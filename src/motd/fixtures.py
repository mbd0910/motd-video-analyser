"""Fixture loading for MOTD analysis pipeline."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from motd.models import Fixture, Score

FIXTURES_DIR = Path("data/fixtures")


def fixtures_path_for_season(season: str) -> Path:
    """Path to a season's fixtures file, from a season label like "2026-27"."""
    return FIXTURES_DIR / f"premier_league_{season.replace('-', '_')}.json"


class FixtureProvider(ABC):
    """Interface for loading fixture data."""

    @abstractmethod
    def get_fixtures_for_date(self, date: str) -> list[Fixture]:
        """Return fixtures for a given broadcast date (YYYY-MM-DD)."""

    @abstractmethod
    def get_all_fixtures(self) -> list[Fixture]:
        """Return all available fixtures."""

    def get_candidates(self, broadcast_date: str) -> list[Fixture]:
        """Return every fixture the episode broadcast on this date could have shown.

        The window is the gameweek, not the day: an episode shows the day's own
        matches, a Friday or Saturday game held over, and brief round-ups of games
        an earlier episode already covered. Deliberately wider than any one episode
        needs — narrowing it is the analyser's job, not the loader's.
        """
        return candidates_for_broadcast(self.get_all_fixtures(), broadcast_date)


def candidates_for_broadcast(fixtures: list[Fixture], broadcast_date: str) -> list[Fixture]:
    """Fixtures in the broadcast date's gameweek that had kicked off by that date.

    Falls back to same-date fixtures when the file predates gameweek numbering.
    """
    on_the_day = [f for f in fixtures if f.date == broadcast_date]
    gameweeks = {f.gameweek for f in on_the_day if f.gameweek is not None}
    if not gameweeks:
        return sorted(on_the_day, key=_broadcast_sequence)

    candidates = [
        f for f in fixtures if f.gameweek in gameweeks and f.date <= broadcast_date
    ]
    return sorted(candidates, key=_broadcast_sequence)


def _broadcast_sequence(fixture: Fixture) -> tuple[str, str, str]:
    return (fixture.date, fixture.kickoff or "", fixture.match_id)


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
        try:
            fpl_code = raw["fpl_code"]
            match_id = raw["match_id"]
            date = raw["date"]
            home_team = raw["home_team"]
            away_team = raw["away_team"]
            home_code = raw["home_code"]
            away_code = raw["away_code"]
        except KeyError as e:
            raise ValueError(
                f"Fixture missing required field {e}: {raw}"
            ) from e
        score = None
        raw_score = raw.get("final_score")
        if raw_score:
            try:
                score = Score(home=raw_score["home"], away=raw_score["away"])
            except (KeyError, TypeError) as e:
                raise ValueError(
                    f"Fixture has malformed final_score: {raw_score}"
                ) from e
        return Fixture(
            fpl_code=fpl_code,
            match_id=match_id,
            date=date,
            home_team=home_team,
            away_team=away_team,
            home_code=home_code,
            away_code=away_code,
            venue=raw.get("venue", ""),
            score=score,
            gameweek=raw.get("gameweek"),
            kickoff=raw.get("kickoff"),
            played=raw.get("played", score is not None),
        )
