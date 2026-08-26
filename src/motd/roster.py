"""Studio roster — who presented and punditted an episode.

Kept in its own committed file rather than on the analysis, because the analysis is
rewritten wholesale by every `analyse` run while a roster is typed in by hand once.
`roster apply` joins the two without going near the API.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from motd.episode import Episode
from motd.models import EpisodeRoster

logger = logging.getLogger(__name__)

ROSTERS_DIR = Path("data/rosters")


class RosterError(Exception):
    """Raised when a roster file is missing, malformed, or disagrees with its season."""


def roster_path_for_season(season: str) -> Path:
    """Path to a season's roster file, from a season label like "2026-27"."""
    return ROSTERS_DIR / f"motd_{season.replace('-', '_')}.json"


class RosterBook:
    """A season's episode rosters, keyed by episode_id."""

    def __init__(self, season: str, rosters: dict[str, EpisodeRoster]) -> None:
        self.season = season
        self._by_episode = rosters

    @staticmethod
    def load(path: Path | str) -> RosterBook:
        path = Path(path)
        if not path.exists():
            raise RosterError(f"Roster file not found: {path}")
        try:
            raw = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise RosterError(f"Malformed JSON in {path}: {exc}") from exc

        try:
            season = raw["season"]
            episodes = raw["episodes"]
        except (KeyError, TypeError) as exc:
            raise RosterError(f"{path} must have 'season' and 'episodes' keys") from exc

        rosters = {}
        for episode_id, entry in episodes.items():
            # A typo'd key would otherwise sit unread for a season: nothing else
            # joins on it, so a roster that matches no episode looks like no roster.
            try:
                ep = Episode.from_id(episode_id)
            except ValueError as exc:
                raise RosterError(f"{path}: {exc}") from exc
            if ep.season != season:
                raise RosterError(
                    f"{path}: {episode_id} is season {ep.season}, file declares {season}"
                )
            try:
                rosters[episode_id] = EpisodeRoster.model_validate(entry)
            except ValueError as exc:
                raise RosterError(f"{path}: roster for {episode_id} is invalid: {exc}") from exc

        return RosterBook(season, rosters)

    @staticmethod
    def for_season(season: str) -> RosterBook:
        return RosterBook.load(roster_path_for_season(season))

    def get(self, episode_id: str) -> EpisodeRoster | None:
        return self._by_episode.get(episode_id)

    def episode_ids(self) -> list[str]:
        return sorted(self._by_episode)


def roster_for_episode(episode_id: str, season: str) -> EpisodeRoster | None:
    """The episode's roster, or None if the season has no file or no entry for it.

    Deliberately quiet: `analyse` is a billed call and must not die because optional
    metadata is absent. Use RosterBook directly where a missing file is an error.
    """
    try:
        book = RosterBook.for_season(season)
    except RosterError as exc:
        logger.info("No roster for %s: %s", episode_id, exc)
        return None
    roster = book.get(episode_id)
    if roster is None:
        logger.info("No roster entry for %s in %s", episode_id, roster_path_for_season(season))
    return roster
