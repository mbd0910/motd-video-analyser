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

from motd.episode import Episode

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

    try:
        metadata = json.loads(meta_result.stdout)
    except json.JSONDecodeError as e:
        raise DownloadError(f"Failed to parse yt-dlp metadata: {e}") from e
    broadcast_date = _parse_broadcast_date(metadata)
    ep = Episode.from_broadcast_date(broadcast_date)
    ext = metadata.get("ext", "mp4")
    video_path = out_dir / f"{ep.episode_id}.{ext}"

    logger.info("Episode: %s (broadcast %s)", ep.episode_id, broadcast_date)

    # Step 2: Download (skip if already exists)
    if video_path.exists():
        logger.info("Video already exists: %s", video_path)
        return DownloadResult(video_path=str(video_path), episode_id=ep.episode_id)

    logger.info("Downloading to %s", video_path)
    # Output is left attached to the terminal so a multi-GB download shows
    # yt-dlp's progress bar; the trade-off is that stderr is unavailable here.
    try:
        subprocess.run(
            ["yt-dlp", "-o", str(video_path), url],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DownloadError(
            f"Failed to download video: yt-dlp exited with status {exc.returncode} "
            "(see output above)"
        ) from exc

    logger.info("Download complete: %s", video_path)
    return DownloadResult(video_path=str(video_path), episode_id=ep.episode_id)
