"""Transcriber module — converts video audio to structured transcript.

Extracts audio via ffmpeg, chunks it for the OpenAI Whisper API,
and assembles a continuous Transcript with correct timestamp offsets.
"""

from __future__ import annotations

from motd.models import Transcript


def transcribe(video_path: str, episode_id: str) -> Transcript:
    """Transcribe a video file and return a structured Transcript.

    Args:
        video_path: Path to the video file.
        episode_id: Episode identifier for the transcript.

    Returns:
        Transcript with timestamped segments.
    """
    raise NotImplementedError("Transcriber not yet implemented — see issue #20")
