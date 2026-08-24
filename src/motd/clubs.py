"""Club directory — resolves a club's canonical name and venue from its code.

Keyed by the three-letter code rather than the season, because codes are
stable across promotion and relegation while club rosters are not.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

DEFAULT_CLUBS_PATH = Path("data/teams/premier_league.json")


class Venue(BaseModel):
    """A club's home ground and the ways commentary refers to it."""

    stadium: str
    city: str
    aliases: list[str] = []
    additional_references: list[str] = []


class Club(BaseModel):
    """A club's canonical name, the codes and nicknames it appears under, and its ground.

    `fpl_code` is FPL's own club id, stable across seasons — unlike the `id` in
    the same payload, which is a 1-20 alphabetical rank that reshuffles on every
    promotion. Relegated clubs kept for history have none.
    """

    full: str
    abbrev: str
    codes: list[str]
    fpl_code: int | None = None
    alternates: list[str] = []
    venue: Venue


class ClubDirectory:
    """Lookup from club code to canonical club data."""

    def __init__(self, clubs: dict[str, Club]) -> None:
        self._by_code = {code: club for club in clubs.values() for code in club.codes}

    @staticmethod
    def load(path: Path | str = DEFAULT_CLUBS_PATH) -> ClubDirectory:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Club directory not found: {path}")
        raw = json.loads(path.read_text())
        return ClubDirectory({k: Club.model_validate(v) for k, v in raw["clubs"].items()})

    def by_code(self, code: str) -> Club:
        """Raises KeyError if the code is unknown — a newly promoted club needs adding."""
        try:
            return self._by_code[code]
        except KeyError:
            raise KeyError(
                f"Unknown club code {code!r}. Add it to {DEFAULT_CLUBS_PATH}."
            ) from None

    def codes(self) -> set[str]:
        return set(self._by_code)
