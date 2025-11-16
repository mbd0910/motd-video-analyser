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
            'audio': {
                'sample_rate': 22050,
                'channels': 2
            }
        }
        extractor = AudioExtractor(config)
        assert extractor.sample_rate == 22050
        assert extractor.channels == 2

    @patch('subprocess.run')
    @patch('subprocess.check_output')
    def test_extract_success(
        self,
        mock_check_output,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test successful audio extraction."""
        # Mock ffprobe output (duration query)
        mock_check_output.return_value = b'120.5\n'

        # Mock ffmpeg successful run
        mock_run.return_value = MagicMock(returncode=0)

        # Create fake output file
        Path(audio_path).write_bytes(b'fake audio data' * 1000)

        result = extractor.extract(video_path, audio_path)

        # Verify ffmpeg was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'ffmpeg' in call_args
        assert '-i' in call_args
        assert video_path in call_args
        assert audio_path in call_args

        # Verify result structure
        assert result['video_path'] == video_path
        assert result['audio_path'] == audio_path
        assert result['duration_seconds'] == 120.5
        assert 'output_size_mb' in result
        assert result['sample_rate'] == 16000

    @patch('subprocess.run')
    def test_extract_video_not_found(self, mock_run, extractor, audio_path):
        """Test extraction fails gracefully when video doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            extractor.extract("/nonexistent/video.mp4", audio_path)

        # ffmpeg should not be called
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('subprocess.check_output')
    def test_extract_ffmpeg_failure(
        self,
        mock_check_output,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test extraction handles ffmpeg failures."""
        # Mock ffprobe success
        mock_check_output.return_value = b'120.5\n'

        # Mock ffmpeg failure
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffmpeg'],
            stderr=b'Error: Invalid format'
        )

        with pytest.raises(RuntimeError, match="Failed to extract audio"):
            extractor.extract(video_path, audio_path)

    @patch('subprocess.run')
    @patch('subprocess.check_output')
    def test_extract_creates_output_directory(
        self,
        mock_check_output,
        mock_run,
        extractor,
        video_path,
        tmp_path
    ):
        """Test extraction creates output directory if it doesn't exist."""
        # Mock ffprobe
        mock_check_output.return_value = b'60.0\n'

        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0)

        # Use nested output path
        audio_path = tmp_path / "nested" / "dir" / "audio.wav"

        # Create fake output after ffmpeg "runs"
        def create_audio(*args, **kwargs):
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(b'audio')
            return MagicMock(returncode=0)

        mock_run.side_effect = create_audio

        result = extractor.extract(video_path, str(audio_path))

        # Verify directory was created
        assert audio_path.parent.exists()
        assert result['audio_path'] == str(audio_path)

    @patch('subprocess.run')
    @patch('subprocess.check_output')
    def test_extract_force_overwrite(
        self,
        mock_check_output,
        mock_run,
        extractor,
        video_path,
        audio_path
    ):
        """Test force flag overwrites existing audio file."""
        # Create existing audio file
        Path(audio_path).write_text("old audio")

        # Mock ffprobe
        mock_check_output.return_value = b'90.0\n'

        # Mock ffmpeg success (overwrites file)
        def overwrite_audio(*args, **kwargs):
            Path(audio_path).write_bytes(b'new audio')
            return MagicMock(returncode=0)

        mock_run.side_effect = overwrite_audio

        result = extractor.extract(video_path, audio_path, force=True)

        # Verify ffmpeg was called (not skipped)
        mock_run.assert_called_once()
        assert result['audio_path'] == audio_path

    @patch('subprocess.check_output')
    def test_get_duration_success(self, mock_check_output, extractor, video_path):
        """Test getting video duration with ffprobe."""
        mock_check_output.return_value = b'123.456\n'

        duration = extractor._get_duration(video_path)

        assert duration == 123.456
        mock_check_output.assert_called_once()
        call_args = mock_check_output.call_args[0][0]
        assert 'ffprobe' in call_args
        assert video_path in call_args

    @patch('subprocess.check_output')
    def test_get_duration_ffprobe_failure(
        self,
        mock_check_output,
        extractor,
        video_path
    ):
        """Test duration extraction handles ffprobe failures."""
        mock_check_output.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffprobe'],
            stderr=b'Invalid file'
        )

        with pytest.raises(RuntimeError, match="Failed to get video duration"):
            extractor._get_duration(video_path)

    @patch('subprocess.check_output')
    def test_get_duration_invalid_output(
        self,
        mock_check_output,
        extractor,
        video_path
    ):
        """Test duration extraction handles invalid ffprobe output."""
        mock_check_output.return_value = b'not a number\n'

        with pytest.raises(ValueError):
            extractor._get_duration(video_path)


class TestAudioExtractorIntegration:
    """Integration-style tests (still mocked, but testing full flow)."""

    @patch('subprocess.run')
    @patch('subprocess.check_output')
    def test_full_extraction_flow(
        self,
        mock_check_output,
        mock_run,
        tmp_path
    ):
        """Test complete extraction flow from video to audio."""
        # Setup
        extractor = AudioExtractor({})
        video = tmp_path / "video.mp4"
        video.write_text("video")
        audio = tmp_path / "cache" / "audio.wav"

        # Mock ffprobe (duration)
        mock_check_output.return_value = b'300.0\n'

        # Mock ffmpeg (creates audio file)
        def create_audio(*args, **kwargs):
            audio.parent.mkdir(parents=True, exist_ok=True)
            audio.write_bytes(b'x' * 10485760)  # 10 MB
            return MagicMock(returncode=0)

        mock_run.side_effect = create_audio

        # Execute
        result = extractor.extract(str(video), str(audio))

        # Verify
        assert audio.exists()
        assert result['duration_seconds'] == 300.0
        assert result['output_size_mb'] == pytest.approx(10.0, rel=0.1)
        assert result['sample_rate'] == 16000
        assert result['channels'] == 1
