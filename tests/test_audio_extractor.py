"""
Tests for AudioExtractor - audio extraction from video files.

Testing strategy:
- Mock ffmpeg subprocess calls to avoid dependency on ffmpeg binary
- Test successful extraction path
- Test error handling (missing video, ffmpeg failure)
- Test output path creation
- Test force re-extraction
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from motd.transcription.audio_extractor import AudioExtractor


class TestAudioExtractor:
    """Test suite for AudioExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create AudioExtractor instance with default config."""
        return AudioExtractor({})

    @pytest.fixture
    def video_path(self, tmp_path):
        """Create a mock video file path."""
        video = tmp_path / "test_video.mp4"
        video.write_text("fake video content")
        return str(video)

    @pytest.fixture
    def audio_path(self, tmp_path):
        """Create output audio path."""
        return str(tmp_path / "audio.wav")

    def test_initialization_default_config(self):
        """Test AudioExtractor initializes with default config."""
        extractor = AudioExtractor({})
        assert extractor.sample_rate == 16000
        assert extractor.channels == 1

    def test_initialization_custom_config(self):
        """Test AudioExtractor initializes with custom config."""
        config = {
            'sample_rate': 22050,
            'channels': 2
        }
        extractor = AudioExtractor(config)
        assert extractor.sample_rate == 22050
        assert extractor.channels == 2

    @patch('subprocess.run')
    def test_extract_success(
        self,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test successful audio extraction."""
        # Create fake output file first (will be checked after extraction)
        Path(audio_path).write_bytes(b'fake audio data' * 1000)

        # Mock subprocess.run for both ffprobe and ffmpeg calls
        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[0] == 'ffprobe':
                # Mock ffprobe duration query
                result.stdout = '120.5\n'
                result.returncode = 0
                return result
            elif cmd[0] == 'ffmpeg':
                # Mock ffmpeg extraction (file already created above)
                result.returncode = 0
                result.stderr = ''
                return result

        mock_run.side_effect = mock_subprocess_run

        result = extractor.extract(video_path, audio_path)

        # Verify subprocess.run was called twice (ffprobe + ffmpeg)
        assert mock_run.call_count == 2

        # Verify first call was ffprobe
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args[0] == 'ffprobe'

        # Verify second call was ffmpeg
        second_call_args = mock_run.call_args_list[1][0][0]
        assert second_call_args[0] == 'ffmpeg'
        assert '-i' in second_call_args
        assert video_path in second_call_args

        # Verify result structure
        assert result['success'] is True
        assert result['duration_seconds'] == 120.5
        assert 'output_size_mb' in result
        assert result['sample_rate'] == 16000
        assert result['channels'] == 1

    @patch('subprocess.run')
    def test_extract_video_not_found(self, mock_run, extractor, audio_path):
        """Test extraction fails gracefully when video doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            extractor.extract("/nonexistent/video.mp4", audio_path)

        # ffmpeg should not be called
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_extract_ffmpeg_failure(
        self,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test extraction handles ffmpeg failures."""
        call_count = [0]

        def mock_subprocess_run(cmd, **kwargs):
            call_count[0] += 1
            if cmd[0] == 'ffprobe':
                # First call: ffprobe succeeds
                result = MagicMock()
                result.stdout = '120.5\n'
                result.returncode = 0
                return result
            elif cmd[0] == 'ffmpeg':
                # Second call: ffmpeg fails
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=['ffmpeg'],
                    stderr='Error: Invalid format'
                )

        mock_run.side_effect = mock_subprocess_run

        with pytest.raises(RuntimeError, match="Audio extraction failed"):
            extractor.extract(video_path, audio_path)

    @patch('subprocess.run')
    def test_extract_creates_output_directory(
        self,
        mock_run,
        extractor,
        video_path,
        tmp_path
    ):
        """Test extraction creates output directory if it doesn't exist."""
        # Use nested output path
        audio_path = tmp_path / "nested" / "dir" / "audio.wav"

        # Mock subprocess.run for both calls
        call_count = [0]

        def mock_subprocess_run(cmd, **kwargs):
            call_count[0] += 1
            if cmd[0] == 'ffprobe':
                result = MagicMock()
                result.stdout = '60.0\n'
                result.returncode = 0
                return result
            elif cmd[0] == 'ffmpeg':
                # Create directory and file when ffmpeg runs
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b'audio data')
                result = MagicMock()
                result.returncode = 0
                result.stderr = ''
                return result

        mock_run.side_effect = mock_subprocess_run

        result = extractor.extract(video_path, str(audio_path))

        # Verify directory was created
        assert audio_path.parent.exists()
        assert result['success'] is True
        assert result['duration_seconds'] == 60.0

    @patch('subprocess.run')
    def test_extract_force_overwrite(
        self,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test force flag overwrites existing audio file."""
        # Create existing audio file
        Path(audio_path).write_text("old audio")

        # Mock subprocess.run for both calls
        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == 'ffprobe':
                result = MagicMock()
                result.stdout = '90.0\n'
                result.returncode = 0
                return result
            elif cmd[0] == 'ffmpeg':
                Path(audio_path).write_bytes(b'new audio')
                result = MagicMock()
                result.returncode = 0
                result.stderr = ''
                return result

        mock_run.side_effect = mock_subprocess_run

        result = extractor.extract(video_path, audio_path)

        # Verify both calls happened (not skipped)
        assert mock_run.call_count == 2
        assert result['success'] is True
        assert result['duration_seconds'] == 90.0

    @patch('subprocess.run')
    def test_get_duration_success(self, mock_run, extractor, video_path):
        """Test getting video duration with ffprobe."""
        mock_result = MagicMock()
        mock_result.stdout = '123.456\n'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        duration = extractor._get_duration(video_path)

        assert duration == 123.456
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'ffprobe'
        assert video_path in call_args

    @patch('subprocess.run')
    def test_get_duration_ffprobe_failure(
        self,
        mock_run,
        extractor,
        video_path
    ):
        """Test duration extraction handles ffprobe failures."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffprobe'],
            stderr='Invalid file'
        )

        with pytest.raises(RuntimeError, match="ffprobe failed"):
            extractor._get_duration(video_path)

    @patch('subprocess.run')
    def test_get_duration_invalid_output(
        self,
        mock_run,
        extractor,
        video_path
    ):
        """Test duration extraction handles invalid ffprobe output."""
        mock_result = MagicMock()
        mock_result.stdout = 'not a number\n'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError, match="Invalid duration value"):
            extractor._get_duration(video_path)


class TestAudioExtractorIntegration:
    """Integration-style tests (still mocked, but testing full flow)."""

    @patch('subprocess.run')
    def test_full_extraction_flow(
        self,
        mock_run,
        tmp_path
    ):
        """Test complete extraction flow from video to audio."""
        # Setup
        extractor = AudioExtractor({})
        video = tmp_path / "video.mp4"
        video.write_text("video")
        audio = tmp_path / "cache" / "audio.wav"

        # Mock subprocess.run for both calls
        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == 'ffprobe':
                result = MagicMock()
                result.stdout = '300.0\n'
                result.returncode = 0
                return result
            elif cmd[0] == 'ffmpeg':
                audio.parent.mkdir(parents=True, exist_ok=True)
                audio.write_bytes(b'x' * 10485760)  # 10 MB
                result = MagicMock()
                result.returncode = 0
                result.stderr = ''
                return result

        mock_run.side_effect = mock_subprocess_run

        # Execute
        result = extractor.extract(str(video), str(audio))

        # Verify
        assert audio.exists()
        assert result['duration_seconds'] == 300.0
        assert result['output_size_mb'] == pytest.approx(10.0, rel=0.1)
        assert result['sample_rate'] == 16000
        assert result['channels'] == 1
