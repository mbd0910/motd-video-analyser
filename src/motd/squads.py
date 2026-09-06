"""Squad lookup — which clubs a stretch of commentary is talking about.

The round-up runs matches back to back with no studio handover to separate them, so
the only thing in the transcript that says which match is on screen is who is named.
A player belongs to one club, which makes the squad list a check on a claimed timing
that the transcript alone cannot give.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

SQUADS_DIR = Path("data/squads")

# Short names collide across clubs and with ordinary words — "Reed", "King", "Wood" —
# so the index keeps only names long enough that a hit means something.
MIN_NAME_CHARS = 4

_WORD = re.compile(r"[^\W\d_][\w'\u2019-]*")

# Subtitles drop diacritics as often as they keep them, so both spellings have to reach
# the same key. Stroked and ligatured letters survive NFKD, so they are mapped by hand.
_STROKES = str.maketrans({
    "ø": "o", "đ": "d", "ð": "d", "ł": "l", "þ": "th", "æ": "ae", "œ": "oe", "ß": "ss",
})


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold().translate(_STROKES))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


class SquadError(Exception):
    """Raised when squad data is missing or unusable."""


def squads_path_for_season(season: str) -> Path:
    """Path to a season's squads file, from a season label like "2026-27"."""
    return SQUADS_DIR / f"premier_league_{season.replace('-', '_')}.json"


@dataclass(frozen=True, slots=True)
class SquadIndex:
    """Surname to the club codes that have a player of that name."""

    clubs_by_name: dict[str, frozenset[str]]

    @staticmethod
    def load(season: str) -> SquadIndex:
        path = squads_path_for_season(season)
        if not path.exists():
            raise SquadError(
                f"Squads file not found: {path}. Run `python -m motd fixtures sync`."
            )
        try:
            squads = json.loads(path.read_text())["squads"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise SquadError(f"Unusable squads file {path}: {exc}") from exc
        return SquadIndex.from_squads(squads)

    @staticmethod
    def from_squads(squads: dict[str, list[str]]) -> SquadIndex:
        clubs_by_name: dict[str, set[str]] = {}
        for code, names in squads.items():
            for name in names:
                key = _fold(name).strip()
                if len(key) >= MIN_NAME_CHARS:
                    clubs_by_name.setdefault(key, set()).add(code)
        if not clubs_by_name:
            raise SquadError("Squads file names no players")
        return SquadIndex({name: frozenset(codes) for name, codes in clubs_by_name.items()})

    def clubs_named_in(self, text: str) -> set[str]:
        """Every club with a player named in this text.

        A name shared by two clubs implicates both — the caller is asking whether a
        particular match was on screen, and an ambiguous hit still answers that.
        """
        clubs: set[str] = set()
        for word in _WORD.findall(text):
            clubs |= self.clubs_by_name.get(_fold(word), frozenset())
        return clubs
