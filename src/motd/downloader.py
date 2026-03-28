"""Downloader module — fetches MOTD episodes from BBC iPlayer via yt-dlp.

Accepts a programme URL or ID, downloads the video, and extracts
episode metadata to derive the episode_id.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when a download operation fails."""


@dataclass
class DownloadResult:
    """Result of downloading an episode."""

    video_path: str
    episode_id: str


def _normalise_url(url_or_id: str) -> str:
    """Convert a programme ID to a full iPlayer URL, or pass URLs through."""
    if url_or_id.startswith(("http://", "https://")):
        return url_or_id
    return f"https://www.bbc.co.uk/iplayer/episode/{url_or_id}"


def _parse_broadcast_date(metadata: dict[str, object]) -> str:
    """Extract broadcast date (YYYY-MM-DD) from yt-dlp metadata.

    Prefers release_date, falls back to upload_date.
    """
    raw = metadata.get("release_date") or metadata.get("upload_date")
    if not raw or not isinstance(raw, str) or len(raw) != 8:
        raise DownloadError("Could not determine broadcast date from metadata")
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _derive_season(broadcast_date: str) -> str:
    """Derive the football season from a broadcast date.

    Season runs Aug–May. Dates Aug–Dec belong to YYYY-(YY+1),
    dates Jan–Jul belong to (YYYY-1)-YY.
    """
    year = int(broadcast_date[:4])
    month = int(broadcast_date[5:7])
    if month >= 8:
        start_year = year
    else:
        start_year = year - 1
    end_yy = (start_year + 1) % 100
    return f"{start_year}-{end_yy:02d}"


def _derive_episode_id(broadcast_date: str) -> str:
    """Derive episode_id from broadcast date."""
    season = _derive_season(broadcast_date)
    return f"motd_{season}_{broadcast_date}"


def parse_episode_id(episode_id: str) -> tuple[str, str]:
    """Extract broadcast_date and season from an episode_id.

    Expected format: motd_YYYY-YY_YYYY-MM-DD

    Returns:
        (broadcast_date, season) tuple.

    Raises:
        ValueError: If the episode_id doesn't match the expected format.
    """
    parts = episode_id.split("_")
    if len(parts) >= 3:
        return parts[2], parts[1]
    raise ValueError(
        f"Cannot derive date from episode_id: {episode_id}. "
        "Expected format: motd_YYYY-YY_YYYY-MM-DD"
    )


def download(url_or_id: str, output_dir: str = "data/videos") -> DownloadResult:
    """Download an MOTD episode from BBC iPlayer.

    Args:
        url_or_id: BBC iPlayer URL or programme ID.
        output_dir: Directory to save the downloaded video.

    Returns:
        DownloadResult with local video path and derived episode_id.

    Raises:
        DownloadError: If metadata fetch or download fails.
    """
    url = _normalise_url(url_or_id)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch metadata
    logger.info("Fetching metadata: %s", url)
    try:
        meta_result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"Failed to fetch metadata: {exc.stderr}") from exc

    metadata = json.loads(meta_result.stdout)
    broadcast_date = _parse_broadcast_date(metadata)
    episode_id = _derive_episode_id(broadcast_date)
    ext = metadata.get("ext", "mp4")
    video_path = out_dir / f"{episode_id}.{ext}"

    logger.info("Episode: %s (broadcast %s)", episode_id, broadcast_date)

    # Step 2: Download (skip if already exists)
    if video_path.exists():
        logger.info("Video already exists: %s", video_path)
        return DownloadResult(video_path=str(video_path), episode_id=episode_id)

    logger.info("Downloading to %s", video_path)
    try:
        subprocess.run(
            ["yt-dlp", "-o", str(video_path), url],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"Failed to download video: {exc.stderr}") from exc

    logger.info("Download complete: %s", video_path)
    return DownloadResult(video_path=str(video_path), episode_id=episode_id)
