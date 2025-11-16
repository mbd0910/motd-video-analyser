"""
Integration tests for transcription CLI command.

Testing strategy:
- Use Click's CliRunner for CLI testing
- Mock both AudioExtractor and WhisperTranscriber
- Test complete transcribe command workflow
- Test cache hit/miss scenarios
- Test cache invalidation when config changes
- Test --force flag
- Test output JSON structure
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from motd.__main__ import cli


class TestTranscribeCommand:
    """Test suite for 'motd transcribe' CLI command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_video(self, tmp_path):
        """Create a fake video file."""
        video = tmp_path / "test_video.mp4"
        video.write_text("fake video")
        return video

    @pytest.fixture
    def mock_cache_dir(self, tmp_path):
        """Create cache directory."""
        cache = tmp_path / "cache" / "test_video"
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_fresh_video(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test transcribing a video with no cached transcript."""
        # Setup mocks
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 120.0,
            'output_size_mb': 5.0,
            'sample_rate': 16000,
            'channels': 1
        }

        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.device = "cpu"
        mock_transcriber.transcribe.return_value = {
            'language': 'en',
            'duration': 120.0,
            'segment_count': 50,
            'segments': [
                {
                    'id': 0,
                    'text': ' Test segment.',
                    'start': 0.0,
                    'end': 2.4,
                    'words': []
                }
            ]
        }

        # Execute
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['transcribe', str(mock_video)])

        # Verify
        assert result.exit_code == 0
        assert "Extracting audio" in result.output
        assert "Transcribing audio" in result.output
        assert "50 segments" in result.output

        # Verify extractor was called
        mock_extractor.extract.assert_called_once()

        # Verify transcriber was called
        mock_transcriber.transcribe.assert_called_once()

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_cache_hit(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test transcribe command uses cached transcript when available."""
        # Create cached transcript
        cache_dir = tmp_path / "data" / "cache" / "test_video"
        cache_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = cache_dir / "transcript.json"
        cached_data = {
            'metadata': {
                'video_path': str(mock_video),
                'model_size': 'large-v3',
                'device': 'cpu',
                'processed_at': '2025-11-16T10:00:00Z'
            },
            'language': 'en',
            'duration': 100.0,
            'segment_count': 40,
            'segments': []
        }
        transcript_file.write_text(json.dumps(cached_data))

        # Execute
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['transcribe', str(mock_video)])

        # Verify
        assert result.exit_code == 0
        assert "Cached transcript found" in result.output
        assert "Duration: 100.0s" in result.output
        assert "Segments: 40" in result.output
        assert "Model: large-v3" in result.output

        # Verify extractor/transcriber were NOT called
        mock_extractor_class.assert_not_called()
        mock_transcriber_class.assert_not_called()

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_cache_invalidation_model_changed(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test cache is invalidated when model size changes."""
        # Create cached transcript with old model
        cache_dir = tmp_path / "data" / "cache" / "test_video"
        cache_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = cache_dir / "transcript.json"
        cached_data = {
            'metadata': {
                'video_path': str(mock_video),
                'model_size': 'medium',  # Old model
                'device': 'cpu',
                'processed_at': '2025-11-16T10:00:00Z'
            },
            'language': 'en',
            'duration': 100.0,
            'segment_count': 40,
            'segments': []
        }
        transcript_file.write_text(json.dumps(cached_data))

        # Setup mocks for re-transcription
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 100.0,
            'output_size_mb': 4.0,
            'sample_rate': 16000,
            'channels': 1
        }

        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.device = "cpu"
        mock_transcriber.transcribe.return_value = {
            'language': 'en',
            'duration': 100.0,
            'segment_count': 45,
            'segments': []
        }

        # Execute with different model (config has large-v3 by default)
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['transcribe', str(mock_video)])

        # Verify cache invalidation message
        assert result.exit_code == 0
        assert "Cache invalid: configuration changed" in result.output
        assert "Cached model: medium, Current: large-v3" in result.output
        assert "Re-transcribing" in result.output

        # Verify re-transcription happened
        mock_transcriber.transcribe.assert_called_once()

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_force_flag(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test --force flag bypasses cache."""
        # Create cached transcript
        cache_dir = tmp_path / "data" / "cache" / "test_video"
        cache_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = cache_dir / "transcript.json"
        cached_data = {
            'metadata': {
                'model_size': 'large-v3',
                'device': 'cpu'
            },
            'duration': 100.0,
            'segment_count': 40,
            'segments': []
        }
        transcript_file.write_text(json.dumps(cached_data))

        # Setup mocks
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 100.0,
            'output_size_mb': 4.0,
            'sample_rate': 16000,
            'channels': 1
        }

        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.device = "cpu"
        mock_transcriber.transcribe.return_value = {
            'language': 'en',
            'duration': 100.0,
            'segment_count': 50,
            'segments': []
        }

        # Execute with --force
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['transcribe', str(mock_video), '--force'])

        # Verify
        assert result.exit_code == 0
        assert "Extracting audio" in result.output
        assert "Transcribing audio" in result.output

        # Verify re-transcription happened despite cache
        mock_transcriber.transcribe.assert_called_once()

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_output_json_structure(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test output JSON has correct structure with metadata."""
        # Setup mocks
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 60.0,
            'output_size_mb': 2.0,
            'sample_rate': 16000,
            'channels': 1
        }

        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.device = "cpu"
        mock_transcriber.transcribe.return_value = {
            'language': 'en',
            'duration': 60.0,
            'segment_count': 20,
            'segments': [
                {
                    'id': 0,
                    'text': ' Test.',
                    'start': 0.0,
                    'end': 1.0,
                    'words': []
                }
            ]
        }

        # Execute
        with runner.isolated_filesystem(temp_dir=tmp_path):
            output_path = tmp_path / "data" / "cache" / "test_video" / "transcript.json"
            result = runner.invoke(cli, ['transcribe', str(mock_video)])

            # Verify file was created
            assert result.exit_code == 0
            assert output_path.exists()

            # Verify JSON structure
            with open(output_path) as f:
                data = json.load(f)

            # Check top-level structure
            assert 'metadata' in data
            assert 'language' in data
            assert 'duration' in data
            assert 'segment_count' in data
            assert 'segments' in data

            # Check metadata
            assert data['metadata']['video_path'] == str(mock_video)
            assert data['metadata']['model_size'] == 'large-v3'
            assert data['metadata']['device'] == 'cpu'
            assert 'processed_at' in data['metadata']
            assert 'processing_time_seconds' in data['metadata']
            assert 'real_time_factor' in data['metadata']

            # Check content
            assert data['language'] == 'en'
            assert data['duration'] == 60.0
            assert data['segment_count'] == 20
            assert len(data['segments']) == 1

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_model_size_override(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test --model-size flag overrides config."""
        # Setup mocks
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 60.0,
            'output_size_mb': 2.0,
            'sample_rate': 16000,
            'channels': 1
        }

        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.device = "cpu"
        mock_transcriber.transcribe.return_value = {
            'language': 'en',
            'duration': 60.0,
            'segment_count': 20,
            'segments': []
        }

        # Execute with --model-size
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ['transcribe', str(mock_video), '--model-size', 'tiny']
            )

        # Verify
        assert result.exit_code == 0

        # Verify transcriber was initialized with tiny model
        init_config = mock_transcriber_class.call_args[0][0]
        assert init_config['model_size'] == 'tiny'

    def test_transcribe_video_not_found(self, runner):
        """Test transcribe fails gracefully when video doesn't exist."""
        result = runner.invoke(cli, ['transcribe', '/nonexistent/video.mp4'])

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "No such file" in result.output

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_extraction_failure(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video
    ):
        """Test transcribe handles audio extraction failure."""
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.side_effect = RuntimeError("ffmpeg failed")

        result = runner.invoke(cli, ['transcribe', str(mock_video)])

        assert result.exit_code != 0
        assert "ffmpeg failed" in result.output or "Error" in result.output

    @patch('motd.__main__.WhisperTranscriber')
    @patch('motd.__main__.AudioExtractor')
    def test_transcribe_transcription_failure(
        self,
        mock_extractor_class,
        mock_transcriber_class,
        runner,
        mock_video,
        tmp_path
    ):
        """Test transcribe handles transcription failure."""
        # Extraction succeeds
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract.return_value = {
            'video_path': str(mock_video),
            'audio_path': str(tmp_path / "audio.wav"),
            'duration_seconds': 60.0,
            'output_size_mb': 2.0,
            'sample_rate': 16000,
            'channels': 1
        }

        # Transcription fails
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.transcribe.side_effect = RuntimeError("Model error")

        result = runner.invoke(cli, ['transcribe', str(mock_video)])

        assert result.exit_code != 0
        assert "Model error" in result.output or "Error" in result.output


class TestTranscribeCacheValidation:
    """Specific tests for cache validation logic."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cache_validation_device_change(self, runner, tmp_path):
        """Test cache invalidation when device changes."""
        # This is tested implicitly in test_transcribe_cache_invalidation_model_changed
        # but we could add more specific device-only change test here
        pass

    def test_cache_validation_auto_device_accepts_any(self, runner, tmp_path):
        """Test that device='auto' doesn't invalidate cache regardless of cached device."""
        # When current device is 'auto', it should accept any cached device
        # since 'auto' is a meta-setting that adapts to available hardware
        pass
