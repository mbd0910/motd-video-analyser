"""Downloader module — fetches MOTD episodes from BBC iPlayer via yt-dlp.

Takes a programme URL or ID plus the broadcast date, and saves the video
under the episode_id the rest of the pipeline keys off.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from motd.episode import Episode

logger = logging.getLogger(__name__)

# yt-dlp writes these alongside an in-progress download; they are not the video.
_SIDECAR_SUFFIXES = frozenset({".part", ".ytdl", ".temp"})


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


def _find_video(out_dir: Path, episode_id: str) -> Path | None:
    """Locate an already-downloaded video, ignoring yt-dlp's in-progress files."""
    for path in sorted(out_dir.glob(f"{episode_id}.*")):
        if path.suffix.lower() not in _SIDECAR_SUFFIXES:
            return path
    return None


def download(
    url_or_id: str,
    broadcast_date: str,
    output_dir: str = "data/videos",
) -> DownloadResult:
    """Download an MOTD episode from BBC iPlayer.

    The broadcast date is supplied by the caller rather than read from
    yt-dlp metadata: BBC iPlayer omits release_date and upload_date
    entirely, leaving the date available only in the display title.

    Args:
        url_or_id: BBC iPlayer URL or programme ID.
        broadcast_date: Air date as YYYY-MM-DD.
        output_dir: Directory to save the downloaded video.

    Returns:
        DownloadResult with local video path and derived episode_id.

    Raises:
        DownloadError: If the date is malformed or the download fails.
    """
    url = _normalise_url(url_or_id)

    try:
        ep = Episode.from_broadcast_date(broadcast_date)
    except ValueError as exc:
        raise DownloadError(str(exc)) from exc

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Episode: %s (broadcast %s)", ep.episode_id, broadcast_date)

    existing = _find_video(out_dir, ep.episode_id)
    if existing:
        logger.info("Video already exists: %s", existing)
        return DownloadResult(video_path=str(existing), episode_id=ep.episode_id)

    # yt-dlp fills in the container extension, so no metadata round-trip is needed.
    out_template = str(out_dir / f"{ep.episode_id}.%(ext)s")
    logger.info("Downloading %s to %s", url, out_template)

    # Output is left attached to the terminal so a multi-GB download shows
    # yt-dlp's progress bar; the trade-off is that stderr is unavailable here.
    try:
        subprocess.run(["yt-dlp", "-o", out_template, url], check=True)
    except subprocess.CalledProcessError as exc:
        raise DownloadError(
            f"Failed to download video: yt-dlp exited with status {exc.returncode} "
            "(see output above)"
        ) from exc

    video_path = _find_video(out_dir, ep.episode_id)
    if not video_path:
        raise DownloadError(
            f"yt-dlp reported success but no video was found for {ep.episode_id} "
            f"in {out_dir}"
        )

    logger.info("Download complete: %s", video_path)
    return DownloadResult(video_path=str(video_path), episode_id=ep.episode_id)
