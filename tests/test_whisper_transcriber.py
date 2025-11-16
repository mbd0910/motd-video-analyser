"""
Tests for WhisperTranscriber - audio transcription with faster-whisper.

Testing strategy:
- Mock WhisperModel to avoid loading 1.5GB model
- Test device selection (CUDA, MPS, CPU fallback)
- Test model loading with different sizes
- Test transcription happy path
- Test configuration options (word_timestamps, language)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from motd.transcription.whisper_transcriber import WhisperTranscriber


class TestWhisperTranscriber:
    """Test suite for WhisperTranscriber class."""

    @pytest.fixture
    def audio_path(self, tmp_path):
        """Create a mock audio file."""
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"fake audio content")
        return str(audio)

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_initialization_default_config(self, mock_model_class):
        """Test WhisperTranscriber initializes with default config."""
        transcriber = WhisperTranscriber({})

        assert transcriber.model_size == "large-v3"
        assert transcriber.language == "en"

        # Verify model was loaded
        mock_model_class.assert_called_once()
        call_kwargs = mock_model_class.call_args[1]
        assert call_kwargs['model_size_or_path'] == "large-v3"

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_initialization_custom_config(self, mock_model_class):
        """Test WhisperTranscriber initializes with custom config."""
        config = {
            'model_size': 'medium',
            'language': 'es',
            'device': 'cpu',
            'word_timestamps': False
        }

        transcriber = WhisperTranscriber(config)

        assert transcriber.model_size == "medium"
        assert transcriber.language == "es"

        # Verify model loaded with correct params
        call_kwargs = mock_model_class.call_args[1]
        assert call_kwargs['model_size_or_path'] == "medium"
        assert call_kwargs['device'] == "cpu"

    @patch('torch.cuda.is_available', return_value=True)
    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_device_selection_cuda_available(
        self,
        mock_model_class,
        mock_cuda
    ):
        """Test device selection when CUDA is available."""
        config = {'device': 'auto'}
        transcriber = WhisperTranscriber(config)

        # Should select CUDA when available
        call_kwargs = mock_model_class.call_args[1]
        assert call_kwargs['device'] == "cuda"
        assert transcriber.device == "cuda"

    @patch('torch.cuda.is_available', return_value=False)
    @patch('torch.backends.mps.is_available', return_value=True)
    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_device_selection_mps_available(
        self,
        mock_model_class,
        mock_mps,
        mock_cuda
    ):
        """Test device selection when MPS (Apple Silicon) is available."""
        config = {'device': 'auto'}
        transcriber = WhisperTranscriber(config)

        # Should select MPS when CUDA unavailable but MPS available
        call_kwargs = mock_model_class.call_args[1]
        # Note: faster-whisper doesn't support MPS, should fall back to CPU
        assert call_kwargs['device'] == "cpu"
        assert transcriber.device == "cpu"

    @patch('torch.cuda.is_available', return_value=False)
    @patch('torch.backends.mps.is_available', return_value=False)
    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_device_selection_cpu_fallback(
        self,
        mock_model_class,
        mock_mps,
        mock_cuda
    ):
        """Test device selection falls back to CPU."""
        config = {'device': 'auto'}
        transcriber = WhisperTranscriber(config)

        # Should fall back to CPU
        call_kwargs = mock_model_class.call_args[1]
        assert call_kwargs['device'] == "cpu"
        assert transcriber.device == "cpu"

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_device_explicit_override(self, mock_model_class):
        """Test explicit device override."""
        config = {'device': 'cuda'}
        transcriber = WhisperTranscriber(config)

        call_kwargs = mock_model_class.call_args[1]
        assert call_kwargs['device'] == "cuda"

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_transcribe_success(self, mock_model_class, audio_path):
        """Test successful transcription."""
        # Setup mock model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock transcription result
        mock_segments = [
            MagicMock(
                id=0,
                text=" This is a test.",
                start=0.0,
                end=2.5,
                words=[
                    MagicMock(word=" This", start=0.0, end=0.5, probability=0.99),
                    MagicMock(word=" is", start=0.5, end=0.8, probability=0.98),
                    MagicMock(word=" a", start=0.8, end=1.0, probability=0.97),
                    MagicMock(word=" test.", start=1.0, end=2.5, probability=0.96),
                ]
            ),
            MagicMock(
                id=1,
                text=" Second segment.",
                start=2.5,
                end=5.0,
                words=[
                    MagicMock(word=" Second", start=2.5, end=3.0, probability=0.95),
                    MagicMock(word=" segment.", start=3.0, end=5.0, probability=0.94),
                ]
            )
        ]

        mock_info = MagicMock(duration=5.0)
        mock_model.transcribe.return_value = (mock_segments, mock_info)

        # Execute
        transcriber = WhisperTranscriber({})
        result = transcriber.transcribe(audio_path)

        # Verify transcribe was called
        mock_model.transcribe.assert_called_once()
        call_args = mock_model.transcribe.call_args
        assert call_args[0][0] == audio_path
        assert call_args[1]['language'] == "en"
        assert call_args[1]['word_timestamps'] is True

        # Verify result structure
        assert result['language'] == "en"
        assert result['duration'] == 5.0
        assert result['segment_count'] == 2
        assert len(result['segments']) == 2

        # Verify first segment
        seg0 = result['segments'][0]
        assert seg0['id'] == 0
        assert seg0['text'] == " This is a test."
        assert seg0['start'] == 0.0
        assert seg0['end'] == 2.5
        assert len(seg0['words']) == 4
        assert seg0['words'][0]['word'] == " This"
        assert seg0['words'][0]['probability'] == 0.99

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_transcribe_without_word_timestamps(
        self,
        mock_model_class,
        audio_path
    ):
        """Test transcription without word-level timestamps."""
        config = {'word_timestamps': False}

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock segment without words
        mock_segment = MagicMock(
            id=0,
            text=" Test segment.",
            start=0.0,
            end=2.0,
            words=[]
        )
        mock_info = MagicMock(duration=2.0)
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        # Execute
        transcriber = WhisperTranscriber(config)
        result = transcriber.transcribe(audio_path)

        # Verify word_timestamps=False was passed
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs['word_timestamps'] is False

        # Verify result has no words
        assert result['segments'][0]['words'] == []

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_transcribe_file_not_found(self, mock_model_class):
        """Test transcription fails when audio file doesn't exist."""
        transcriber = WhisperTranscriber({})

        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.transcribe("/nonexistent/audio.wav")

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_transcribe_model_error(self, mock_model_class, audio_path):
        """Test transcription handles model errors gracefully."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock transcription failure
        mock_model.transcribe.side_effect = RuntimeError("Model error")

        transcriber = WhisperTranscriber({})

        with pytest.raises(RuntimeError, match="Transcription failed"):
            transcriber.transcribe(audio_path)

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_different_model_sizes(self, mock_model_class):
        """Test different model sizes can be loaded."""
        model_sizes = ['tiny', 'base', 'small', 'medium', 'large', 'large-v3']

        for size in model_sizes:
            mock_model_class.reset_mock()
            config = {'model_size': size}
            transcriber = WhisperTranscriber(config)

            call_kwargs = mock_model_class.call_args[1]
            assert call_kwargs['model_size_or_path'] == size
            assert transcriber.model_size == size

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_segment_conversion(self, mock_model_class, audio_path):
        """Test internal segment conversion from faster-whisper format."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock segment with word details
        mock_segment = MagicMock(
            id=0,
            text=" Test",
            start=1.0,
            end=2.0,
            words=[
                MagicMock(word=" Test", start=1.0, end=2.0, probability=0.95)
            ]
        )
        mock_info = MagicMock(duration=2.0)
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        transcriber = WhisperTranscriber({})
        result = transcriber.transcribe(audio_path)

        # Verify segment was converted correctly
        seg = result['segments'][0]
        assert seg['id'] == 0
        assert seg['text'] == " Test"
        assert seg['start'] == 1.0
        assert seg['end'] == 2.0
        assert seg['words'][0]['word'] == " Test"
        assert seg['words'][0]['start'] == 1.0
        assert seg['words'][0]['end'] == 2.0
        assert seg['words'][0]['probability'] == 0.95


class TestWhisperTranscriberEdgeCases:
    """Test edge cases and error conditions."""

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_empty_audio_file(self, mock_model_class, tmp_path):
        """Test transcription handles empty audio file."""
        audio = tmp_path / "empty.wav"
        audio.write_bytes(b"")  # Empty file

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock empty transcription result
        mock_info = MagicMock(duration=0.0)
        mock_model.transcribe.return_value = ([], mock_info)

        transcriber = WhisperTranscriber({})
        result = transcriber.transcribe(str(audio))

        assert result['segment_count'] == 0
        assert result['segments'] == []
        assert result['duration'] == 0.0

    @patch('motd.transcription.whisper_transcriber.WhisperModel')
    def test_very_long_audio(self, mock_model_class, tmp_path):
        """Test transcription handles very long audio (many segments)."""
        audio = tmp_path / "long.wav"
        audio.write_bytes(b"fake long audio")

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Generate 1000 mock segments
        mock_segments = [
            MagicMock(
                id=i,
                text=f" Segment {i}",
                start=float(i * 2),
                end=float(i * 2 + 2),
                words=[]
            )
            for i in range(1000)
        ]
        mock_info = MagicMock(duration=2000.0)
        mock_model.transcribe.return_value = (mock_segments, mock_info)

        transcriber = WhisperTranscriber({})
        result = transcriber.transcribe(str(audio))

        assert result['segment_count'] == 1000
        assert len(result['segments']) == 1000
        assert result['duration'] == 2000.0
