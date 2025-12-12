"""Transcript formatting for LLM analysis.

Converts Whisper transcript.json to LLM-ready text format with
deduplication of consecutive identical segments (Whisper "stutters").
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationStats:
    """Statistics from transcript deduplication."""

    original_count: int
    deduplicated_count: int
    removed_count: int

    @property
    def removal_percentage(self) -> float:
        """Percentage of segments removed."""
        if self.original_count == 0:
            return 0.0
        return (self.removed_count / self.original_count) * 100


@dataclass
class FormattedTranscript:
    """Result of transcript formatting."""

    text: str
    segment_count: int
    duration_seconds: float
    deduplication_stats: DeduplicationStats


class TranscriptFormatter:
    """Formats Whisper transcripts for LLM analysis.

    Handles loading transcript.json, deduplicating consecutive identical
    segments (Whisper "stutters"), and formatting as timestamped text.
    """

    def __init__(self, cache_path: Path | str) -> None:
        """Initialise with path to episode cache folder.

        Args:
            cache_path: Path to episode cache folder (e.g., data/cache/motd_2025-26_2025-11-22/)
        """
        self.cache_path = Path(cache_path)
        self.transcript_path = self.cache_path / "transcript.json"

    def load_transcript(self) -> dict[str, Any]:
        """Load transcript.json from cache.

        Returns:
            Parsed transcript data with metadata and segments.

        Raises:
            FileNotFoundError: If transcript.json doesn't exist.
            json.JSONDecodeError: If transcript.json is invalid.
        """
        if not self.transcript_path.exists():
            raise FileNotFoundError(f"Transcript not found: {self.transcript_path}")

        with open(self.transcript_path) as f:
            return json.load(f)

    def deduplicate_segments(
        self, segments: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], DeduplicationStats]:
        """Remove consecutive duplicate segments (Whisper stutters).

        Whisper sometimes outputs the same text for slightly different
        audio segments. This merges consecutive segments with identical
        text, keeping the earliest timestamp.

        Args:
            segments: List of transcript segments from Whisper.

        Returns:
            Tuple of (deduplicated segments, statistics).
        """
        if not segments:
            return [], DeduplicationStats(0, 0, 0)

        deduplicated: list[dict[str, Any]] = []
        previous_text: str | None = None

        for segment in segments:
            text = segment.get("text", "").strip()

            # Skip empty segments
            if not text:
                continue

            # Skip if identical to previous segment
            if text == previous_text:
                logger.debug(
                    "Removing duplicate segment at %.2fs: %s",
                    segment.get("start", 0),
                    text[:50],
                )
                continue

            deduplicated.append(segment)
            previous_text = text

        original_count = len(segments)
        deduplicated_count = len(deduplicated)
        removed_count = original_count - deduplicated_count

        stats = DeduplicationStats(
            original_count=original_count,
            deduplicated_count=deduplicated_count,
            removed_count=removed_count,
        )

        if removed_count > 0:
            logger.info(
                "Deduplicated %d segments (%.1f%% removed)",
                removed_count,
                stats.removal_percentage,
            )

        return deduplicated, stats

    def format_as_text(self, segments: list[dict[str, Any]]) -> str:
        """Convert segments to timestamped text format.

        Format: [MM:SS.ss] Text content here

        Args:
            segments: List of transcript segments.

        Returns:
            Formatted text with timestamps.
        """
        lines: list[str] = []

        for segment in segments:
            start = segment.get("start", 0)
            text = segment.get("text", "").strip()

            if not text:
                continue

            timestamp = self._format_timestamp(start)
            lines.append(f"[{timestamp}] {text}")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS.ss timestamp.

        Args:
            seconds: Time in seconds.

        Returns:
            Formatted timestamp string.
        """
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"

    def format(self) -> FormattedTranscript:
        """Load, deduplicate, and format transcript.

        Main entry point that performs the full formatting pipeline.

        Returns:
            FormattedTranscript with text and statistics.

        Raises:
            FileNotFoundError: If transcript.json doesn't exist.
        """
        transcript_data = self.load_transcript()

        segments = transcript_data.get("segments", [])
        duration = transcript_data.get("duration", 0)

        deduplicated, stats = self.deduplicate_segments(segments)
        text = self.format_as_text(deduplicated)

        return FormattedTranscript(
            text=text,
            segment_count=stats.deduplicated_count,
            duration_seconds=duration,
            deduplication_stats=stats,
        )
