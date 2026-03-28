"""Episode resolution — derives identity and cache paths from an episode ID.

Consolidates episode ID format, season derivation, and cache path
construction into a single frozen dataclass. No other module needs
to know the episode_id string format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CACHE_DIR = Path("data/cache")

_EPISODE_ID_RE = re.compile(r"^motd_(\d{4}-\d{2})_(\d{4}-\d{2}-\d{2})$")


@dataclass(frozen=True, slots=True)
class Episode:
    """Resolved episode identity and cache paths.

    Constructed via from_id() or from_broadcast_date() — never directly.
    """

    episode_id: str
    broadcast_date: str
    season: str
    cache_dir: Path
    transcript_path: Path
    analysis_path: Path

    @staticmethod
    def from_id(
        episode_id: str,
        cache_base: Path = DEFAULT_CACHE_DIR,
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
            analysis_path=ep_cache / "analysis.json",
        )

    @staticmethod
    def from_broadcast_date(
        broadcast_date: str,
        cache_base: Path = DEFAULT_CACHE_DIR,
    ) -> Episode:
        """Derive episode identity from a broadcast date (YYYY-MM-DD).

        Season runs Aug-May: dates Aug-Dec belong to YYYY-(YY+1),
        dates Jan-Jul belong to (YYYY-1)-YY.
        """
        year = int(broadcast_date[:4])
        month = int(broadcast_date[5:7])
        start_year = year if month >= 8 else year - 1
        end_yy = (start_year + 1) % 100
        season = f"{start_year}-{end_yy:02d}"
        episode_id = f"motd_{season}_{broadcast_date}"
        ep_cache = cache_base / episode_id
        return Episode(
            episode_id=episode_id,
            broadcast_date=broadcast_date,
            season=season,
            cache_dir=ep_cache,
            transcript_path=ep_cache / "transcript.json",
            analysis_path=ep_cache / "analysis.json",
        )

    def ensure_cache_dir(self) -> None:
        """Create the episode cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
