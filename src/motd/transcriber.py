"""Transcriber module — converts video audio to structured transcript.

Extracts audio via ffmpeg, chunks it for the OpenAI Whisper API,
and assembles a continuous Transcript with correct timestamp offsets.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import openai

from motd.models import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when transcription fails."""

DEFAULT_CHUNK_DURATION = 1200  # 20 minutes in seconds
DEFAULT_MODEL = "whisper-1"


def transcribe(
    video_path: str,
    episode_id: str,
    *,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    model: str = DEFAULT_MODEL,
) -> Transcript:
    """Transcribe a video file and return a structured Transcript.

    Args:
        video_path: Path to the video file.
        episode_id: Episode identifier for the transcript.
        chunk_duration: Duration of each audio chunk in seconds.
        model: OpenAI Whisper model to use.

    Returns:
        Transcript with timestamped segments.
    """
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    duration = _get_audio_duration(video_path)
    logger.info("Transcribing %s (%.0fs) with model=%s", video.name, duration, model)

    with TemporaryDirectory(prefix="motd_chunks_") as tmp_dir:
        chunk_paths = _chunk_audio(video_path, tmp_dir, chunk_duration=chunk_duration)
        logger.info("Split into %d chunk(s)", len(chunk_paths))

        all_segments: list[list[TranscriptSegment]] = []
        for i, chunk_path in enumerate(chunk_paths):
            offset = i * chunk_duration
            logger.info("Transcribing chunk %d/%d (offset=%ds)", i + 1, len(chunk_paths), offset)

            raw_segments = _transcribe_chunk(chunk_path, model=model)
            parsed = _parse_whisper_segments(raw_segments, offset=float(offset))
            all_segments.append(parsed)

    transcript = _assemble_transcript(all_segments, episode_id, duration=duration)
    logger.info("Transcription complete: %d segments", len(transcript.segments))
    return transcript


def _chunk_audio(
    video_path: str, output_dir: str, *, chunk_duration: int = DEFAULT_CHUNK_DURATION
) -> list[str]:
    """Split video audio into MP3 chunks using ffmpeg.

    Args:
        video_path: Path to the video file.
        output_dir: Directory to write chunk files.
        chunk_duration: Duration of each chunk in seconds.

    Returns:
        Sorted list of chunk file paths.
    """
    output_pattern = str(Path(output_dir) / "chunk_%03d.mp3")
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "64k",
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        output_pattern,
        "-loglevel", "warning",
        "-y",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise TranscriptionError(
            f"ffmpeg audio chunking failed: {e.stderr or e}"
        ) from e

    chunks = sorted(Path(output_dir).glob("chunk_*.mp3"))
    if not chunks:
        raise TranscriptionError(
            "ffmpeg produced no audio chunks — input file may be empty or invalid"
        )
    return [str(c) for c in chunks]


def _transcribe_chunk(chunk_path: str, *, model: str = DEFAULT_MODEL) -> list[dict]:
    """Send a single audio chunk to the OpenAI Whisper API.

    Args:
        chunk_path: Path to the audio chunk file.
        model: Whisper model name.

    Returns:
        List of segment dicts with start, end, text keys.
    """
    client = openai.OpenAI()

    with open(chunk_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="verbose_json",
        )

    return [
        {"start": seg.start, "end": seg.end, "text": seg.text}
        for seg in (response.segments or [])
    ]


def _parse_whisper_segments(
    raw_segments: list[dict], offset: float
) -> list[TranscriptSegment]:
    """Parse Whisper API segments and apply timestamp offset.

    Args:
        raw_segments: List of dicts with start, end, text from the API.
        offset: Seconds to add to each timestamp (chunk start time).

    Returns:
        List of TranscriptSegment with adjusted timestamps.
    """
    result = []
    for seg in raw_segments:
        text = seg["text"].strip()
        if not text:
            continue
        result.append(
            TranscriptSegment(
                start=seg["start"] + offset,
                end=seg["end"] + offset,
                text=text,
            )
        )
    return result


def _assemble_transcript(
    chunk_segments: list[list[TranscriptSegment]],
    episode_id: str,
    *,
    duration: float,
) -> Transcript:
    """Assemble a Transcript from multiple chunk results.

    Args:
        chunk_segments: List of segment lists, one per chunk.
        episode_id: Episode identifier.
        duration: Total duration in seconds.

    Returns:
        Assembled Transcript.
    """
    segments = [seg for chunk in chunk_segments for seg in chunk]
    return Transcript(
        episode_id=episode_id,
        duration_seconds=duration,
        segments=segments,
    )


def _get_audio_duration(file_path: str) -> float:
    """Get duration of an audio/video file using ffprobe.

    Args:
        file_path: Path to the file.

    Returns:
        Duration in seconds.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise TranscriptionError(
            f"ffprobe duration check failed: {e.stderr or e}"
        ) from e
    try:
        return float(result.stdout.strip())
    except ValueError as e:
        raise TranscriptionError(
            f"ffprobe returned non-numeric duration: {result.stdout.strip()!r}"
        ) from e
