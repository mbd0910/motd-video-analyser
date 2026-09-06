"""Studio roster — who presented and punditted an episode.

Two sources joined at read time. BBC credits the presenter, the pundits (as
"Expert") and the editor, and `data/metadata/` holds that verbatim; `data/rosters/`
holds only what they omit — guests above all, who appear on screen uncredited.

Kept off the analysis because that file is rewritten wholesale by every `analyse`
run, which would fight a correction. `publisher` joins the two on the way out, so
fixing a roster costs a re-publish rather than a billed re-analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from motd.episode import Episode
from motd.models import EpisodeMetadata, EpisodeRoster, RosterOverride

logger = logging.getLogger(__name__)

ROSTERS_DIR = Path("data/rosters")

PRESENTER_ROLE = "Presenter"
# BBC's word for a pundit. Their credits carry no role for a guest at all.
PUNDIT_ROLE = "Expert"
EDITOR_ROLE = "Editor"


class RosterError(Exception):
    """Raised when a roster file is missing, malformed, or disagrees with its season."""


def roster_path_for_season(season: str) -> Path:
    """Path to a season's roster file, from a season label like "2026-27"."""
    return ROSTERS_DIR / f"motd_{season.replace('-', '_')}.json"


def from_credits(
    metadata: EpisodeMetadata, override: RosterOverride | None = None
) -> EpisodeRoster | None:
    """Build a roster from BBC's credits, with the hand-entered file layered on top.

    Returns None when neither source names a presenter, which is what an episode
    whose credits have not been fetched looks like.
    """
    override = override or RosterOverride()

    presenter = override.presenter or next(iter(metadata.named_for_role(PRESENTER_ROLE)), None)
    if presenter is None:
        return None

    pundits = override.pundits
    if pundits is None:
        pundits = [name for name in metadata.named_for_role(PUNDIT_ROLE) if name != presenter]

    return EpisodeRoster(
        presenter=presenter,
        pundits=pundits,
        guests=override.guests,
        editor=override.editor or next(iter(metadata.named_for_role(EDITOR_ROLE)), None),
    )


class RosterBook:
    """A season's hand-entered roster overrides, keyed by episode_id."""

    def __init__(self, season: str, overrides: dict[str, RosterOverride]) -> None:
        self.season = season
        self._by_episode = overrides

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

        overrides = {}
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
                overrides[episode_id] = RosterOverride.model_validate(entry)
            except ValueError as exc:
                raise RosterError(f"{path}: roster for {episode_id} is invalid: {exc}") from exc

        return RosterBook(season, overrides)

    @staticmethod
    def for_season(season: str) -> RosterBook:
        return RosterBook.load(roster_path_for_season(season))

    def get(self, episode_id: str) -> RosterOverride | None:
        return self._by_episode.get(episode_id)

    def episode_ids(self) -> list[str]:
        return sorted(self._by_episode)


def roster_for_episode(episode_id: str, season: str) -> EpisodeRoster | None:
    """The episode's roster, or None if BBC's credits have not been fetched for it.

    Deliberately quiet: `publish` must not die because optional metadata is absent.
    Use `from_credits` directly where a missing roster is an error.
    """
    from motd.programme import ProgrammeError
    from motd.programme import load as load_metadata

    try:
        metadata = load_metadata(episode_id)
    except ProgrammeError as exc:
        logger.warning("No usable metadata for %s: %s", episode_id, exc)
        return None
    if metadata is None:
        logger.info("No metadata for %s — run `motd metadata` to fetch its credits", episode_id)
        return None

    override = None
    try:
        override = RosterBook.for_season(season).get(episode_id)
    except RosterError as exc:
        logger.info("No roster overrides for %s: %s", episode_id, exc)

    roster = from_credits(metadata, override)
    if roster is None:
        logger.warning("%s: BBC credits name no presenter", episode_id)
    return roster
