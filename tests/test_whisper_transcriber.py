"""Tests for Whisper transcriber vocabulary hints functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from motd.transcription.whisper_transcriber import WhisperTranscriber


class TestVocabularyHints:
    """Test vocabulary hints generation for Whisper transcription."""

    @pytest.fixture
    def mock_venues_data(self):
        """Mock venues JSON data."""
        return {
            "season": "2025-26",
            "competition": "Premier League",
            "venues": [
                {
                    "team": "Wolverhampton Wanderers",
                    "stadium": "Molineux Stadium",
                    "city": "Wolverhampton",
                    "aliases": ["Molineux"],
                },
                {
                    "team": "Brighton & Hove Albion",
                    "stadium": "Amex Stadium",
                    "city": "Brighton",
                    "aliases": ["Amex", "The Amex"],
                },
                {
                    "team": "Arsenal",
                    "stadium": "Emirates Stadium",
                    "city": "London",
                    "aliases": ["Emirates", "The Emirates"],
                },
            ],
        }

    @pytest.fixture
    def mock_teams_data(self):
        """Mock teams JSON data."""
        return {
            "season": "2025-26",
            "competition": "Premier League",
            "teams": [
                {
                    "full": "Wolverhampton Wanderers",
                    "abbrev": "Wolves",
                    "codes": ["WOL"],
                    "alternates": ["Wolves"],
                },
                {
                    "full": "Brighton & Hove Albion",
                    "abbrev": "Brighton",
                    "codes": ["BHA"],
                    "alternates": ["Brighton", "The Seagulls"],
                },
                {
                    "full": "Arsenal",
                    "abbrev": "Arsenal",
                    "codes": ["ARS"],
                    "alternates": ["The Gunners", "Gunners"],
                },
            ],
        }

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_vocabulary_hints_enabled_by_default(self, mock_model_class, mock_venues_data, mock_teams_data):
        """Test that vocabulary hints are enabled by default."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        def mock_json_load(file_handle):
            if not hasattr(mock_json_load, "call_count"):
                mock_json_load.call_count = 0
            mock_json_load.call_count += 1
            return mock_venues_data if mock_json_load.call_count == 1 else mock_teams_data

        with patch("json.load", side_effect=mock_json_load):
            transcriber = WhisperTranscriber()

            assert transcriber.enable_vocabulary_hints is True
            assert transcriber.initial_prompt is not None
            # hotwords is now None due to faster-whisper token limit issues
            assert transcriber.hotwords is None

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_vocabulary_hints_can_be_disabled(self, mock_model_class):
        """Test that vocabulary hints can be disabled via config."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        assert transcriber.enable_vocabulary_hints is False
        assert transcriber.initial_prompt is None
        assert transcriber.hotwords is None

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_build_vocabulary_hints_format(self, mock_model_class, mock_venues_data, mock_teams_data):
        """Test vocabulary hints have correct format."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        def mock_json_load(file_handle):
            if not hasattr(mock_json_load, "call_count"):
                mock_json_load.call_count = 0
            mock_json_load.call_count += 1
            return mock_venues_data if mock_json_load.call_count == 1 else mock_teams_data

        with patch("json.load", side_effect=mock_json_load):
            transcriber = WhisperTranscriber()

            # Check initial_prompt format
            assert "Match of the Day" in transcriber.initial_prompt
            assert "Premier League" in transcriber.initial_prompt
            assert "stadiums:" in transcriber.initial_prompt
            assert "Teams:" in transcriber.initial_prompt

            # hotwords should be None (disabled due to token limit issues)
            assert transcriber.hotwords is None

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_vocabulary_hints_include_priority_stadiums(self, mock_model_class, mock_venues_data, mock_teams_data):
        """Test that initial_prompt includes priority stadium names."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        def mock_json_load(file_handle):
            if not hasattr(mock_json_load, "call_count"):
                mock_json_load.call_count = 0
            mock_json_load.call_count += 1
            return mock_venues_data if mock_json_load.call_count == 1 else mock_teams_data

        with patch("json.load", side_effect=mock_json_load):
            transcriber = WhisperTranscriber()

            # Priority stadiums should be in initial_prompt (hardcoded for known misspellings)
            assert "Molineux" in transcriber.initial_prompt
            assert "The Amex" in transcriber.initial_prompt
            # Common stadiums for broader context
            assert "Anfield" in transcriber.initial_prompt
            assert "Old Trafford" in transcriber.initial_prompt

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_vocabulary_hints_include_priority_teams(self, mock_model_class, mock_venues_data, mock_teams_data):
        """Test that initial_prompt includes priority team names."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        def mock_json_load(file_handle):
            if not hasattr(mock_json_load, "call_count"):
                mock_json_load.call_count = 0
            mock_json_load.call_count += 1
            return mock_venues_data if mock_json_load.call_count == 1 else mock_teams_data

        with patch("json.load", side_effect=mock_json_load):
            transcriber = WhisperTranscriber()

            # Priority teams should be in initial_prompt (hardcoded for known misspellings)
            assert "Wolverhampton Wanderers" in transcriber.initial_prompt
            assert "Brighton" in transcriber.initial_prompt

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_transcribe_uses_initial_prompt_when_enabled(self, mock_model_class, tmp_path):
        """Test that transcribe() passes initial_prompt to Whisper when enabled."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock transcribe method
        mock_segments = []
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        mock_info.duration = 100.0
        mock_model.transcribe.return_value = (iter(mock_segments), mock_info)

        # Create dummy audio file
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_text("dummy audio data")

        with patch.object(WhisperTranscriber, "_build_vocabulary_hints") as mock_build_hints:
            # hotwords is None in the new implementation
            mock_build_hints.return_value = ("test prompt", None)

            transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": True})
            transcriber.transcribe(str(audio_file))

            # Verify transcribe was called with initial_prompt but NOT hotwords
            call_args = mock_model.transcribe.call_args
            assert call_args is not None
            assert "initial_prompt" in call_args.kwargs
            assert call_args.kwargs["initial_prompt"] == "test prompt"
            # hotwords should NOT be passed when it's None
            assert "hotwords" not in call_args.kwargs

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_transcribe_without_hints_when_disabled(self, mock_model_class, tmp_path):
        """Test that transcribe() does not pass hints when disabled."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock transcribe method
        mock_segments = []
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        mock_info.duration = 100.0
        mock_model.transcribe.return_value = (iter(mock_segments), mock_info)

        # Create dummy audio file
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_text("dummy audio data")

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})
        transcriber.transcribe(str(audio_file))

        # Verify transcribe was NOT called with hints
        call_args = mock_model.transcribe.call_args
        assert call_args is not None
        assert "initial_prompt" not in call_args.kwargs
        assert "hotwords" not in call_args.kwargs

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_build_hints_raises_on_missing_venues_file(self, mock_model_class):
        """Test that _build_vocabulary_hints raises if venues file missing."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Venues file not found"):
                WhisperTranscriber()

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_build_hints_raises_on_invalid_json(self, mock_model_class):
        """Test that _build_vocabulary_hints raises on invalid JSON."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"

            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                with pytest.raises(ValueError, match="Invalid JSON in venues file"):
                    WhisperTranscriber()

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_initial_prompt_under_token_limit(self, mock_model_class, mock_venues_data, mock_teams_data):
        """Test that initial_prompt stays under 224 token limit (~890 chars)."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        def mock_json_load(file_handle):
            if not hasattr(mock_json_load, "call_count"):
                mock_json_load.call_count = 0
            mock_json_load.call_count += 1
            return mock_venues_data if mock_json_load.call_count == 1 else mock_teams_data

        with patch("json.load", side_effect=mock_json_load):
            transcriber = WhisperTranscriber()

            # 224 tokens ≈ 890 characters (4 chars per token approximation)
            # Stay well under to be safe
            assert len(transcriber.initial_prompt) < 500, (
                f"initial_prompt too long ({len(transcriber.initial_prompt)} chars), "
                "risk of faster-whisper token overflow error"
            )


class TestSpellingCorrections:
    """Test post-processing spelling corrections for Whisper output."""

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_basic(self, mock_model_class):
        """Test basic spelling correction is applied."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        # Test basic correction
        result = transcriber._apply_spelling_corrections("And Vicky Sparks was at Molyneux.")
        assert result == "And Vicky Sparks was at Molineux."

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_preserves_case_title(self, mock_model_class):
        """Test spelling correction preserves title case."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        result = transcriber._apply_spelling_corrections("Molyneux is a great stadium")
        assert result == "Molineux is a great stadium"

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_preserves_case_lower(self, mock_model_class):
        """Test spelling correction preserves lowercase."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        result = transcriber._apply_spelling_corrections("the molyneux atmosphere")
        assert result == "the molineux atmosphere"

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_preserves_case_upper(self, mock_model_class):
        """Test spelling correction preserves uppercase."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        result = transcriber._apply_spelling_corrections("MOLYNEUX ROCKS")
        assert result == "MOLINEUX ROCKS"

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_multiple_occurrences(self, mock_model_class):
        """Test spelling correction handles multiple occurrences."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        result = transcriber._apply_spelling_corrections(
            "Molyneux hosts Wolves. Back to Molyneux for more action."
        )
        assert result == "Molineux hosts Wolves. Back to Molineux for more action."

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_no_match_unchanged(self, mock_model_class):
        """Test that text without misspellings is unchanged."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})

        original = "And Vicky Sparks was at Molineux."
        result = transcriber._apply_spelling_corrections(original)
        assert result == original

    @patch("motd.transcription.whisper_transcriber.WhisperModel")
    def test_spelling_correction_applied_in_process_segments(self, mock_model_class, tmp_path):
        """Test that spelling correction is applied during segment processing."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Create mock segment with misspelling
        mock_segment = Mock()
        mock_segment.text = " A familiar feeling at Molyneux. "
        mock_segment.start = 100.0
        mock_segment.end = 103.0

        # Create mock word with misspelling
        mock_word = Mock()
        mock_word.word = "Molyneux"
        mock_word.start = 102.0
        mock_word.end = 102.5
        mock_word.probability = 0.95
        mock_segment.words = [mock_word]

        # Create mock info
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.duration = 103.0

        transcriber = WhisperTranscriber(config={"enable_vocabulary_hints": False})
        result = transcriber._process_segments(iter([mock_segment]), mock_info)

        # Verify segment text is corrected
        assert result["segments"][0]["text"] == "A familiar feeling at Molineux."

        # Verify word text is corrected
        assert result["segments"][0]["words"][0]["word"] == "Molineux"
