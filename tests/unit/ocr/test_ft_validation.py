"""Unit tests for FT graphic validation logic."""

import pytest
from src.motd.ocr.reader import OCRReader


class TestFTGraphicValidation:
    """Test suite for validate_ft_graphic() method."""

    @pytest.fixture
    def ocr_reader(self):
        """Create OCRReader instance for testing."""
        # Mock config to avoid loading actual EasyOCR model
        config = {
            'library': 'easyocr',
            'languages': ['en'],
            'gpu': False
        }
        return OCRReader(config)

    def test_valid_ft_graphic_with_score_and_ft_text(self, ocr_reader):
        """Valid FT graphic: 2 teams + score + FT text."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': '2'},
            {'text': '-'},
            {'text': '1'},
            {'text': 'Aston Villa'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_valid_ft_graphic_with_full_time_text(self, ocr_reader):
        """Valid FT graphic: FULL TIME instead of FT."""
        ocr_results = [
            {'text': 'Arsenal'},
            {'text': '3 - 0'},
            {'text': 'Burnley'},
            {'text': 'FULL TIME'}
        ]
        detected_teams = ['Arsenal', 'Burnley']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_invalid_only_one_team(self, ocr_reader):
        """Invalid: Only 1 team detected (need exactly 2)."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': '2 - 1'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_invalid_three_teams(self, ocr_reader):
        """Invalid: 3 teams detected (need exactly 2)."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': 'Arsenal'},
            {'text': 'Chelsea'},
            {'text': '2 - 1'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool', 'Arsenal', 'Chelsea']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_invalid_no_score_pattern(self, ocr_reader):
        """Invalid: Has 2 teams and FT but no score."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': 'Aston Villa'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_invalid_no_ft_text(self, ocr_reader):
        """Invalid: Has 2 teams and score but no FT indicator."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': '2 - 1'},
            {'text': 'Aston Villa'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_invalid_possession_bar(self, ocr_reader):
        """Invalid: Possession bar (2 teams, no score/FT)."""
        ocr_results = [
            {'text': '54%'},
            {'text': 'Liverpool'},
            {'text': '46%'},
            {'text': 'Aston Villa'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_invalid_player_statistics(self, ocr_reader):
        """Invalid: Player statistics with team names but no FT."""
        ocr_results = [
            {'text': 'Saka'},
            {'text': '7'},
            {'text': 'Arsenal'},
            {'text': 'Shots'},
            {'text': '14'}
        ]
        detected_teams = ['Arsenal', 'Burnley']  # Even if teams detected

        # No proper score pattern (7-14 would need to be "7 - 14")
        # No FT text
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_score_pattern_variations(self, ocr_reader):
        """Valid: Different score pattern formats."""
        test_cases = [
            {'text': '2-1'},      # No spaces
            {'text': '2 - 1'},    # With spaces
            {'text': '2–1'},      # En dash
            {'text': '2—1'},      # Em dash
            {'text': '0 - 0'},    # Draw
            {'text': '2 0'},      # Space-separated (BBC FT graphics - OCR reads "2 | 0" as "2 0")
            {'text': '1  1'},     # Multiple spaces
        ]

        for score_text in test_cases:
            ocr_results = [
                {'text': 'Liverpool'},
                score_text,
                {'text': 'Aston Villa'},
                {'text': 'FT'}
            ]
            detected_teams = ['Liverpool', 'Aston Villa']

            assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True, \
                f"Failed for score pattern: {score_text['text']}"

    def test_ft_text_variations(self, ocr_reader):
        """Valid: Different FT text variations."""
        ft_variations = ['FT', 'FULL TIME', 'FULL-TIME', 'FULLTIME']

        for ft_text in ft_variations:
            ocr_results = [
                {'text': 'Liverpool'},
                {'text': '2 - 1'},
                {'text': 'Aston Villa'},
                {'text': ft_text}
            ]
            detected_teams = ['Liverpool', 'Aston Villa']

            assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True, \
                f"Failed for FT text variation: {ft_text}"

    def test_case_insensitive_matching(self, ocr_reader):
        """Valid: Case-insensitive FT text matching."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': '2 - 1'},
            {'text': 'Aston Villa'},
            {'text': 'ft'}  # Lowercase
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_empty_ocr_results(self, ocr_reader):
        """Invalid: Empty OCR results."""
        ocr_results = []
        detected_teams = []

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_real_world_false_positive_example(self, ocr_reader):
        """Invalid: Real-world false positive (possession bar from Scene 278)."""
        # This is what was incorrectly classified as FT graphic
        ocr_results = [
            {'text': '54%'},
            {'text': 'Liverpool'},
            {'text': 'Possession'},
            {'text': '46%'},
            {'text': 'Aston Villa'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        # Should FAIL validation (no score pattern, no FT text)
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False
