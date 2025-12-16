"""Unit tests for scoreboard validation logic (TDD - RED phase)."""

import pytest
from motd.ocr.reader import OCRReader


class TestScoreboardValidation:
    """
    Test suite for validate_scoreboard() method.

    BBC scoreboards follow format: "BBC [CODE] [SCORE]|[SCORE] [CODE]"
    Example: "BBC LIV 0|0 FOR"

    Validation requirements:
    1. Exactly 2 distinct 3-character team codes (from premier_league_2025_26.json)
    2. Score pattern (lenient): \d+\s*[-–—|]?\s*\d+
    """

    @pytest.fixture(scope="class")
    def ocr_reader(self):
        """Create OCRReader instance for testing (shared across class)."""
        config = {
            'library': 'easyocr',
            'languages': ['en'],
            'gpu': False
        }
        return OCRReader(config)

    # =========================================================================
    # SHOULD PASS (Valid Scoreboards)
    # =========================================================================

    def test_valid_bbc_scoreboard_pipe_format(self, ocr_reader):
        """Valid: BBC LIV 0|0 FOR (standard BBC pipe format)."""
        ocr_results = [
            {'text': 'BBC'},
            {'text': 'LIV'},
            {'text': '0|0'},
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_hyphen_format(self, ocr_reader):
        """Valid: LIV 0-0 FOR (hyphen separator - lenient)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0-0'},
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_space_format(self, ocr_reader):
        """Valid: LIV 0 0 FOR (space only - lenient)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0 0'},
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_multiple_goals(self, ocr_reader):
        """Valid: BBC BRI 2|1 BRE (non-zero scores)."""
        ocr_results = [
            {'text': 'BBC'},
            {'text': 'BRI'},
            {'text': '2|1'},
            {'text': 'BRE'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_primary_codes(self, ocr_reader):
        """Valid: NFO (primary code for Nottingham Forest)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0|0'},
            {'text': 'NFO'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_alternate_codes(self, ocr_reader):
        """Valid: FOR (alternate code for Nottingham Forest)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0|0'},
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_en_dash_separator(self, ocr_reader):
        """Valid: LIV 1–0 FOR (en dash separator)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '1–0'},  # en dash
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_em_dash_separator(self, ocr_reader):
        """Valid: LIV 1—0 FOR (em dash separator)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '1—0'},  # em dash
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    def test_valid_scoreboard_case_insensitive(self, ocr_reader):
        """Valid: Codes should match case-insensitively (liv, for)."""
        ocr_results = [
            {'text': 'liv'},
            {'text': '0|0'},
            {'text': 'for'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is True

    # =========================================================================
    # SHOULD FAIL (Reject Invalid)
    # =========================================================================

    def test_invalid_intro_montage_text(self, ocr_reader):
        """Invalid: The CL UB BALL (no score pattern, no exact codes)."""
        ocr_results = [
            {'text': 'The'},
            {'text': 'CL'},
            {'text': 'UB'},
            {'text': 'BALL'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_team_name_not_code(self, ocr_reader):
        """Invalid: Brighton Club Football (full name, not 3-char code)."""
        ocr_results = [
            {'text': 'Brighton'},
            {'text': 'Club'},
            {'text': 'Football'},
            {'text': '0-0'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_score_no_codes(self, ocr_reader):
        """Invalid: 0-0 (score but no team codes)."""
        ocr_results = [
            {'text': '0-0'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_codes_no_score(self, ocr_reader):
        """Invalid: BBC LIV FOR (team codes but no score)."""
        ocr_results = [
            {'text': 'BBC'},
            {'text': 'LIV'},
            {'text': 'FOR'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_single_team_code(self, ocr_reader):
        """Invalid: LIV 0|0 (only 1 team code, need exactly 2)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0|0'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_bbc_sport_only(self, ocr_reader):
        """Invalid: BBC SPORT (no teams, no score)."""
        ocr_results = [
            {'text': 'BBC'},
            {'text': 'SPORT'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_empty_results(self, ocr_reader):
        """Invalid: Empty OCR results."""
        ocr_results = []
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_partial_code_match(self, ocr_reader):
        """Invalid: Partial code match (e.g., 'LIVERPOOL' contains 'LIV' but isn't exact)."""
        ocr_results = [
            {'text': 'LIVERPOOL'},
            {'text': '0|0'},
            {'text': 'FOREST'}
        ]
        # Full team names shouldn't match - only exact 3-char codes
        assert ocr_reader.validate_scoreboard(ocr_results) is False

    def test_invalid_duplicate_team_code(self, ocr_reader):
        """Invalid: LIV 0|0 LIV (same code twice, need 2 DISTINCT codes)."""
        ocr_results = [
            {'text': 'LIV'},
            {'text': '0|0'},
            {'text': 'LIV'}
        ]
        assert ocr_reader.validate_scoreboard(ocr_results) is False
