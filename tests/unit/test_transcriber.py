"""Tests for the transcriber module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from motd.models import Transcript, TranscriptSegment
from motd.transcriber import (
    TranscriptionError,
    _assemble_transcript,
    _chunk_audio,
    _get_audio_duration,
    _parse_whisper_segments,
    _transcribe_chunk,
    transcribe,
)


class TestParseWhisperSegments:
    """Test parsing OpenAI Whisper API response segments with offset."""

    def test_segments_parsed_with_zero_offset(self) -> None:
        raw = [
            {"start": 0.0, "end": 5.5, "text": " Welcome to Match of the Day."},
            {"start": 5.5, "end": 12.0, "text": " First up, Liverpool."},
        ]
        segments = _parse_whisper_segments(raw, offset=0.0)
        assert len(segments) == 2
        assert segments[0].start == 0.0
        assert segments[0].end == 5.5
        assert segments[0].text == "Welcome to Match of the Day."
        assert segments[1].start == 5.5

    def test_segments_with_offset_applied(self) -> None:
        raw = [
            {"start": 0.0, "end": 3.0, "text": " Continuing coverage."},
            {"start": 3.0, "end": 8.0, "text": " And a goal!"},
        ]
        segments = _parse_whisper_segments(raw, offset=1200.0)
        assert segments[0].start == 1200.0
        assert segments[0].end == 1203.0
        assert segments[1].start == 1203.0
        assert segments[1].end == 1208.0

    def test_empty_segments_returns_empty_list(self) -> None:
        assert _parse_whisper_segments([], offset=0.0) == []

    def test_whitespace_only_segments_skipped(self) -> None:
        raw = [
            {"start": 0.0, "end": 1.0, "text": "   "},
            {"start": 1.0, "end": 2.0, "text": " Real text."},
        ]
        segments = _parse_whisper_segments(raw, offset=0.0)
        assert len(segments) == 1
        assert segments[0].text == "Real text."


class TestAssembleTranscript:
    """Test assembling a Transcript from multiple chunk results."""

    def test_single_chunk(self) -> None:
        chunks = [
            [
                TranscriptSegment(start=0.0, end=5.0, text="Hello"),
                TranscriptSegment(start=5.0, end=10.0, text="World"),
            ]
        ]
        transcript = _assemble_transcript(chunks, "ep1", duration=60.0)
        assert transcript.episode_id == "ep1"
        assert transcript.duration_seconds == 60.0
        assert len(transcript.segments) == 2

    def test_multiple_chunks_concatenated(self) -> None:
        chunks = [
            [TranscriptSegment(start=0.0, end=5.0, text="Chunk one")],
            [TranscriptSegment(start=1200.0, end=1205.0, text="Chunk two")],
        ]
        transcript = _assemble_transcript(chunks, "ep1", duration=2400.0)
        assert len(transcript.segments) == 2
        assert transcript.segments[0].text == "Chunk one"
        assert transcript.segments[1].text == "Chunk two"
        assert transcript.segments[1].start == 1200.0

    def test_empty_chunks_produce_empty_transcript(self) -> None:
        transcript = _assemble_transcript([], "ep1", duration=0.0)
        assert transcript.segments == []


class TestChunkAudio:
    """Test audio chunking via ffmpeg subprocess."""

    @patch("motd.transcriber.subprocess.run")
    def test_chunk_audio_calls_ffmpeg(self, mock_run: MagicMock, tmp_path: Path) -> None:
        video = tmp_path / "video.mp4"
        video.touch()
        output_dir = tmp_path / "chunks"
        output_dir.mkdir()

        # Create fake chunk files that ffmpeg would produce
        (output_dir / "chunk_000.mp3").touch()
        (output_dir / "chunk_001.mp3").touch()

        mock_run.return_value = MagicMock(returncode=0)

        chunks = _chunk_audio(str(video), str(output_dir), chunk_duration=600)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-segment_time" in cmd
        assert "600" in cmd
        assert len(chunks) == 2

    @patch("motd.transcriber.subprocess.run")
    def test_chunk_audio_zero_chunks_raises(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "chunks"
        output_dir.mkdir()
        # No chunk files created — simulates ffmpeg producing nothing
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(TranscriptionError, match="no audio chunks"):
            _chunk_audio(str(tmp_path / "video.mp4"), str(output_dir))

    @patch("motd.transcriber.subprocess.run")
    def test_chunk_audio_sorted_order(self, mock_run: MagicMock, tmp_path: Path) -> None:
        video = tmp_path / "video.mp4"
        video.touch()
        output_dir = tmp_path / "chunks"
        output_dir.mkdir()

        (output_dir / "chunk_002.mp3").touch()
        (output_dir / "chunk_000.mp3").touch()
        (output_dir / "chunk_001.mp3").touch()

        mock_run.return_value = MagicMock(returncode=0)
        chunks = _chunk_audio(str(video), str(output_dir), chunk_duration=600)

        assert chunks == [
            str(output_dir / "chunk_000.mp3"),
            str(output_dir / "chunk_001.mp3"),
            str(output_dir / "chunk_002.mp3"),
        ]


class TestTranscribeChunk:
    """Test sending a chunk to the OpenAI Whisper API."""

    @patch("motd.transcriber.openai")
    @patch("builtins.open", new_callable=MagicMock)
    def test_transcribe_chunk_returns_segments(
        self, mock_open: MagicMock, mock_openai: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.segments = [
            MagicMock(start=0.0, end=5.0, text=" Hello world."),
        ]
        mock_openai.OpenAI.return_value.audio.transcriptions.create.return_value = (
            mock_response
        )

        segments = _transcribe_chunk("/fake/chunk.mp3", model="whisper-1")
        assert len(segments) == 1
        assert segments[0]["start"] == 0.0
        assert segments[0]["text"] == " Hello world."


class TestGetAudioDuration:
    """Test ffprobe duration extraction."""

    @patch("motd.transcriber.subprocess.run")
    def test_non_numeric_output_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="N/A\n", stderr="")
        with pytest.raises(TranscriptionError, match="non-numeric duration"):
            _get_audio_duration("/fake/video.mp4")

    @patch("motd.transcriber.subprocess.run")
    def test_valid_duration_returned(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="5400.123\n", stderr="")
        assert _get_audio_duration("/fake/video.mp4") == 5400.123


class TestTranscribeIntegration:
    """Integration test for the full transcribe flow (all externals mocked)."""

    @patch("motd.transcriber._get_audio_duration")
    @patch("motd.transcriber._transcribe_chunk")
    @patch("motd.transcriber._chunk_audio")
    def test_full_transcribe_flow(
        self,
        mock_chunk: MagicMock,
        mock_transcribe: MagicMock,
        mock_duration: MagicMock,
        tmp_path: Path,
    ) -> None:
        video = tmp_path / "video.mp4"
        video.touch()

        mock_duration.return_value = 2000.0
        mock_chunk.return_value = ["/chunk_000.mp3", "/chunk_001.mp3"]
        mock_transcribe.side_effect = [
            [{"start": 0.0, "end": 5.0, "text": " First chunk."}],
            [{"start": 0.0, "end": 3.0, "text": " Second chunk."}],
        ]

        transcript = transcribe(str(video), "motd_2025-26_2025-11-01")

        assert isinstance(transcript, Transcript)
        assert transcript.episode_id == "motd_2025-26_2025-11-01"
        assert transcript.duration_seconds == 2000.0
        assert len(transcript.segments) == 2
        assert transcript.segments[0].text == "First chunk."
        # Second chunk offset = 1 * chunk_duration (default 1200)
        assert transcript.segments[1].start == 1200.0
        assert transcript.segments[1].end == 1203.0
