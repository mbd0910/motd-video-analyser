"""Episode resolution — derives identity and file paths from an episode ID.

Consolidates episode ID format, season derivation, and cache path
construction into a single frozen dataclass. No other module needs
to know the episode_id string format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path

DEFAULT_CACHE_DIR = Path("data/cache")
# Analyses are committed, unlike everything else the pipeline writes: they are the
# record the site is built from, and re-deriving one costs an API call against a
# transcript iPlayer stops serving once the episode expires.
DEFAULT_ANALYSIS_DIR = Path("data/analysis")

_EPISODE_ID_RE = re.compile(r"^motd_(\d{4}-\d{2})_(\d{4}-\d{2}-\d{2})$")
_BROADCAST_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_broadcast_date(broadcast_date: str) -> None:
    """Reject anything date.fromisoformat would accept but slicing would misread."""
    if not _BROADCAST_DATE_RE.match(broadcast_date):
        raise ValueError(
            f"Invalid broadcast date: {broadcast_date!r}. Expected format: YYYY-MM-DD"
        )
    try:
        _date.fromisoformat(broadcast_date)
    except ValueError as exc:
        raise ValueError(f"Invalid broadcast date: {broadcast_date!r} ({exc})") from exc


def season_for_date(date: str) -> str:
    """Season label (YYYY-YY) for a date (YYYY-MM-DD).

    Season runs Aug-May: dates Aug-Dec belong to YYYY-(YY+1),
    dates Jan-Jul belong to (YYYY-1)-YY.
    """
    year = int(date[:4])
    month = int(date[5:7])
    start_year = year if month >= 8 else year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


@dataclass(frozen=True, slots=True)
class Episode:
    """Resolved episode identity, cache paths and analysis output path.

    Constructed via from_id() or from_broadcast_date() — never directly.
    """

    episode_id: str
    broadcast_date: str
    season: str
    cache_dir: Path
    transcript_path: Path
    analysis_path: Path
    subtitles_path: Path

    @staticmethod
    def from_id(
        episode_id: str,
        cache_base: Path = DEFAULT_CACHE_DIR,
        analysis_base: Path = DEFAULT_ANALYSIS_DIR,
    ) -> Episode:
        """Resolve from an existing episode_id string.

        Raises:
            ValueError: If episode_id doesn't match motd_YYYY-YY_YYYY-MM-DD.
        """
        m = _EPISODE_ID_RE.match(episode_id)
        if not m:
            raise ValueError(
                f"Invalid episode_id: {episode_id!r}. "
                "Expected format: motd_YYYY-YY_YYYY-MM-DD"
            )
        season, broadcast_date = m.group(1), m.group(2)
        ep_cache = cache_base / episode_id
        return Episode(
            episode_id=episode_id,
            broadcast_date=broadcast_date,
            season=season,
            cache_dir=ep_cache,
            transcript_path=ep_cache / "transcript.json",
            analysis_path=analysis_base / f"{episode_id}.json",
            subtitles_path=ep_cache / "subtitles.ttml",
        )

    @staticmethod
    def from_broadcast_date(
        broadcast_date: str,
        cache_base: Path = DEFAULT_CACHE_DIR,
        analysis_base: Path = DEFAULT_ANALYSIS_DIR,
    ) -> Episode:
        """Derive episode identity from a broadcast date (YYYY-MM-DD).

        Raises:
            ValueError: If broadcast_date is not a valid YYYY-MM-DD date.
        """
        _validate_broadcast_date(broadcast_date)
        season = season_for_date(broadcast_date)
        episode_id = f"motd_{season}_{broadcast_date}"
        ep_cache = cache_base / episode_id
        return Episode(
            episode_id=episode_id,
            broadcast_date=broadcast_date,
            season=season,
            cache_dir=ep_cache,
            transcript_path=ep_cache / "transcript.json",
            analysis_path=analysis_base / f"{episode_id}.json",
            subtitles_path=ep_cache / "subtitles.ttml",
        )

    def ensure_cache_dir(self) -> None:
        """Create the episode cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
