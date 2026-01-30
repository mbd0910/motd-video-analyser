"""Tests for TranscriptFormatter."""

import json
import pytest
from pathlib import Path

from motd.llm.transcript_formatter import (
    TranscriptFormatter,
    DeduplicationStats,
    FormattedTranscript,
)


class TestDeduplicationStats:
    """Tests for DeduplicationStats dataclass."""

    def test_removal_percentage_normal(self):
        """Test removal percentage calculation."""
        stats = DeduplicationStats(
            original_count=100,
            deduplicated_count=88,
            removed_count=12,
        )
        assert stats.removal_percentage == 12.0

    def test_removal_percentage_zero_original(self):
        """Test removal percentage with zero original segments."""
        stats = DeduplicationStats(
            original_count=0,
            deduplicated_count=0,
            removed_count=0,
        )
        assert stats.removal_percentage == 0.0

    def test_removal_percentage_no_removal(self):
        """Test removal percentage when nothing removed."""
        stats = DeduplicationStats(
            original_count=50,
            deduplicated_count=50,
            removed_count=0,
        )
        assert stats.removal_percentage == 0.0


class TestTranscriptFormatterDeduplication:
    """Tests for segment deduplication."""

    def test_deduplicate_empty_list(self):
        """Test deduplication of empty segment list."""
        formatter = TranscriptFormatter("/fake/path")
        segments, stats = formatter.deduplicate_segments([])

        assert segments == []
        assert stats.original_count == 0
        assert stats.deduplicated_count == 0
        assert stats.removed_count == 0

    def test_deduplicate_no_duplicates(self):
        """Test deduplication when no duplicates exist."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "First segment"},
            {"start": 1.0, "text": "Second segment"},
            {"start": 2.0, "text": "Third segment"},
        ]

        result, stats = formatter.deduplicate_segments(segments)

        assert len(result) == 3
        assert stats.original_count == 3
        assert stats.deduplicated_count == 3
        assert stats.removed_count == 0

    def test_deduplicate_consecutive_duplicates(self):
        """Test removal of consecutive duplicate segments."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "First segment"},
            {"start": 1.0, "text": "Duplicate text"},
            {"start": 1.5, "text": "Duplicate text"},  # Duplicate
            {"start": 2.0, "text": "Duplicate text"},  # Duplicate
            {"start": 3.0, "text": "Third segment"},
        ]

        result, stats = formatter.deduplicate_segments(segments)

        assert len(result) == 3
        assert result[0]["text"] == "First segment"
        assert result[1]["text"] == "Duplicate text"
        assert result[2]["text"] == "Third segment"
        assert stats.removed_count == 2

    def test_deduplicate_non_consecutive_same_text(self):
        """Test that non-consecutive same text is preserved."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "Repeated text"},
            {"start": 1.0, "text": "Different text"},
            {"start": 2.0, "text": "Repeated text"},  # Not consecutive, keep it
        ]

        result, stats = formatter.deduplicate_segments(segments)

        assert len(result) == 3
        assert stats.removed_count == 0

    def test_deduplicate_skips_empty_text(self):
        """Test that empty text segments are skipped."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "First segment"},
            {"start": 1.0, "text": ""},
            {"start": 2.0, "text": "   "},  # Whitespace only
            {"start": 3.0, "text": "Second segment"},
        ]

        result, stats = formatter.deduplicate_segments(segments)

        assert len(result) == 2
        assert result[0]["text"] == "First segment"
        assert result[1]["text"] == "Second segment"

    def test_deduplicate_strips_whitespace(self):
        """Test that text is stripped before comparison."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "  Same text  "},
            {"start": 1.0, "text": "Same text"},  # Should be detected as duplicate
        ]

        result, stats = formatter.deduplicate_segments(segments)

        assert len(result) == 1
        assert stats.removed_count == 1


class TestTranscriptFormatterTimestamp:
    """Tests for timestamp formatting."""

    def test_format_timestamp_zero(self):
        """Test timestamp formatting for zero seconds."""
        formatter = TranscriptFormatter("/fake/path")
        assert formatter._format_timestamp(0) == "00:00.00"

    def test_format_timestamp_seconds_only(self):
        """Test timestamp formatting for seconds only."""
        formatter = TranscriptFormatter("/fake/path")
        assert formatter._format_timestamp(45.5) == "00:45.50"

    def test_format_timestamp_minutes_and_seconds(self):
        """Test timestamp formatting with minutes."""
        formatter = TranscriptFormatter("/fake/path")
        assert formatter._format_timestamp(125.75) == "02:05.75"

    def test_format_timestamp_large_value(self):
        """Test timestamp formatting for large values (>60 mins)."""
        formatter = TranscriptFormatter("/fake/path")
        # 75 minutes 30.25 seconds = 4530.25 seconds
        assert formatter._format_timestamp(4530.25) == "75:30.25"


class TestTranscriptFormatterHallucinationCorrection:
    """Tests for timestamp hallucination correction."""

    def test_no_words_uses_segment_start(self):
        """Test that segment start is used when no words available."""
        formatter = TranscriptFormatter("/fake/path")
        segment = {"start": 11.37, "text": "Some text"}

        result = formatter._get_corrected_start_time(segment)

        assert result == 11.37

    def test_single_word_uses_segment_start(self):
        """Test that segment start is used with only one word."""
        formatter = TranscriptFormatter("/fake/path")
        segment = {
            "start": 11.37,
            "text": "Hello",
            "words": [{"word": "Hello", "start": 11.37, "end": 11.89}],
        }

        result = formatter._get_corrected_start_time(segment)

        assert result == 11.37

    def test_normal_gap_uses_segment_start(self):
        """Test that normal word gaps use segment start time."""
        formatter = TranscriptFormatter("/fake/path")
        segment = {
            "start": 9.23,
            "text": "Welcome to",
            "words": [
                {"word": "Welcome", "start": 9.23, "end": 9.61},
                {"word": "to", "start": 9.61, "end": 9.91},
            ],
        }

        result = formatter._get_corrected_start_time(segment)

        assert result == 9.23

    def test_hallucination_gap_uses_second_word(self):
        """Test that large gaps between first and second word use second word start."""
        formatter = TranscriptFormatter("/fake/path")
        # Real example: "It's" hallucinated at 11.37, actual speech at 51.86
        segment = {
            "start": 11.37,
            "end": 53.52,
            "text": "It's been a terrific day",
            "words": [
                {"word": "It's", "start": 11.37, "end": 11.89},
                {"word": "been", "start": 51.86, "end": 51.98},
                {"word": "a", "start": 51.98, "end": 52.08},
            ],
        }

        result = formatter._get_corrected_start_time(segment)

        # Should use second word's start time
        assert result == 51.86

    def test_hallucination_gap_threshold(self):
        """Test that gap must exceed threshold to trigger correction."""
        formatter = TranscriptFormatter("/fake/path")

        # Gap of exactly 5 seconds (at threshold)
        segment_at_threshold = {
            "start": 10.0,
            "text": "Test",
            "words": [
                {"word": "Test", "start": 10.0, "end": 10.5},
                {"word": "text", "start": 15.5, "end": 16.0},  # 5.0s gap
            ],
        }

        # Gap of 5.1 seconds (above threshold)
        segment_above_threshold = {
            "start": 10.0,
            "text": "Test",
            "words": [
                {"word": "Test", "start": 10.0, "end": 10.5},
                {"word": "text", "start": 15.6, "end": 16.0},  # 5.1s gap
            ],
        }

        # At threshold: uses segment start
        assert formatter._get_corrected_start_time(segment_at_threshold) == 10.0

        # Above threshold: uses second word start
        assert formatter._get_corrected_start_time(segment_above_threshold) == 15.6


class TestTranscriptFormatterFormatAsText:
    """Tests for text formatting."""

    def test_format_as_text_basic(self):
        """Test basic text formatting."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 8.5, "text": "Welcome to Match of the Day."},
            {"start": 53.52, "text": "Seven games on the way."},
        ]

        result = formatter.format_as_text(segments)

        expected = (
            "[00:08.50] Welcome to Match of the Day.\n"
            "[00:53.52] Seven games on the way."
        )
        assert result == expected

    def test_format_as_text_empty_segments(self):
        """Test formatting with empty segments."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {"start": 0.0, "text": "First"},
            {"start": 1.0, "text": ""},
            {"start": 2.0, "text": "Second"},
        ]

        result = formatter.format_as_text(segments)

        assert "[00:00.00] First" in result
        assert "[00:02.00] Second" in result
        assert result.count("\n") == 1  # Only one newline between two lines

    def test_format_as_text_with_hallucination_correction(self):
        """Test that format_as_text applies hallucination correction."""
        formatter = TranscriptFormatter("/fake/path")
        segments = [
            {
                "start": 9.23,
                "text": "Welcome to Match of the Day.",
                "words": [
                    {"word": "Welcome", "start": 9.23, "end": 9.61},
                    {"word": "to", "start": 9.61, "end": 9.91},
                ],
            },
            {
                "start": 11.37,  # Wrong start time
                "text": "It's been a terrific day.",
                "words": [
                    {"word": "It's", "start": 11.37, "end": 11.89},
                    {"word": "been", "start": 51.86, "end": 51.98},  # Actual start
                ],
            },
        ]

        result = formatter.format_as_text(segments)

        # First segment should use 9.23
        assert "[00:09.23] Welcome to Match of the Day." in result
        # Second segment should use corrected time 51.86
        assert "[00:51.86] It's been a terrific day." in result


class TestTranscriptFormatterIntegration:
    """Integration tests using real transcript structure."""

    def test_format_full_pipeline(self, tmp_path: Path):
        """Test full format pipeline with mock transcript."""
        # Create mock transcript.json
        transcript_data = {
            "metadata": {"model_size": "large-v3"},
            "duration": 5043.33,
            "segments": [
                {"id": 0, "start": 8.5, "end": 10.16, "text": "Welcome to Match of the Day."},
                {"id": 1, "start": 10.5, "end": 53.44, "text": "The Premier League returned."},
                {"id": 2, "start": 53.52, "end": 54.76, "text": "Seven games on the way."},
                # Consecutive duplicates (Whisper stutter)
                {"id": 3, "start": 1264.06, "end": 1266.76, "text": "Heroic defending."},
                {"id": 4, "start": 1266.90, "end": 1268.12, "text": "Heroic defending."},
                {"id": 5, "start": 1268.12, "end": 1268.18, "text": "Heroic defending."},
                {"id": 6, "start": 1270.0, "end": 1272.0, "text": "Great save."},
            ],
        }

        transcript_path = tmp_path / "transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(transcript_data, f)

        formatter = TranscriptFormatter(tmp_path)
        result = formatter.format()

        # Check deduplication worked
        assert result.deduplication_stats.original_count == 7
        assert result.deduplication_stats.removed_count == 2
        assert result.deduplication_stats.deduplicated_count == 5

        # Check text format
        assert "[00:08.50] Welcome to Match of the Day." in result.text
        assert "[21:04.06] Heroic defending." in result.text  # 1264.06 seconds
        assert result.text.count("Heroic defending") == 1  # Only one occurrence

        # Check metadata
        assert result.duration_seconds == 5043.33
        assert result.segment_count == 5

    def test_format_missing_transcript(self, tmp_path: Path):
        """Test that FileNotFoundError is raised for missing transcript."""
        formatter = TranscriptFormatter(tmp_path)

        with pytest.raises(FileNotFoundError):
            formatter.format()
