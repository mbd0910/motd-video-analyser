"""Downloader module — fetches MOTD episodes from BBC iPlayer via yt-dlp.

Accepts a programme URL or ID, downloads the video, and extracts
episode metadata to derive the episode_id.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DownloadResult:
    """Result of downloading an episode."""

    video_path: str
    episode_id: str


def download(url_or_id: str) -> DownloadResult:
    """Download an MOTD episode from BBC iPlayer.

    Args:
        url_or_id: BBC iPlayer URL or programme ID.

    Returns:
        DownloadResult with local video path and derived episode_id.
    """
    raise NotImplementedError("Downloader not yet implemented — see issue #23")
