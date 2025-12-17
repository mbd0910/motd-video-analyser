"""Tests for looks_like_ft_content() method in GraphicValidator.

This method performs a quick check to determine if OCR results from the FT region
look like genuine FT graphic content, allowing fallback to scoreboard if not.

These tests use GraphicValidator directly (no ML dependencies) enabling
fast execution without loading torch/easyocr (~2GB).
"""

import pytest
from motd.ocr.validators import GraphicValidator


@pytest.fixture
def validator(test_team_codes):
    """Create GraphicValidator with standard team codes."""
    return GraphicValidator(test_team_codes)


@pytest.mark.unit
class TestLooksLikeFTContent:
    """Tests for looks_like_ft_content() method."""

    def test_empty_results_returns_false(self, validator):
        """Empty results should not look like FT content."""
        assert validator.looks_like_ft_content([]) is False

    def test_ft_indicator_returns_true(self, validator):
        """Results with FT indicator should be accepted."""
        results = [{'text': 'Liverpool 2 FT', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_full_time_indicator_returns_true(self, validator):
        """Results with FULL TIME indicator should be accepted."""
        results = [{'text': 'FULL TIME', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_score_pattern_returns_true(self, validator):
        """Results with score pattern should be accepted."""
        results = [{'text': '2 - 1', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_score_pattern_with_pipe_returns_true(self, validator):
        """Results with BBC-style pipe score should be accepted."""
        results = [{'text': '0 | 0', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_team_code_returns_true(self, validator):
        """Results with valid team code should be accepted."""
        results = [{'text': 'LIV', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_newcastle_code_returns_true(self, validator):
        """Results with NEW team code should be accepted."""
        results = [{'text': 'NEW', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_manchester_city_mnc_code_returns_true(self, validator):
        """Results with MNC team code should be accepted (after fix)."""
        results = [{'text': 'MNC', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_garbage_text_returns_false(self, validator):
        """Random text should not look like FT content."""
        results = [{'text': 'tator: Steve Bower', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is False

    def test_commentator_credit_returns_false(self, validator):
        """Commentator credit text should not look like FT content."""
        results = [{'text': 'Commentator: John Smith', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is False

    def test_partial_word_not_matched_as_code(self, validator):
        """Words containing codes shouldn't match (e.g., 'NEW' in 'NEWCASTLE')."""
        # This tests that we match whole words only
        results = [{'text': 'NEWCASTLE', 'confidence': 0.9}]
        # 'NEWCASTLE' split gives ['NEWCASTLE'] which isn't in codes
        # But wait - we do have 'NEW' as a code...
        # Actually split() on 'NEWCASTLE' gives ['NEWCASTLE'], not ['NEW']
        # So this should return False
        assert validator.looks_like_ft_content(results) is False

    def test_multiple_results_any_match(self, validator):
        """If any result has FT content, should return True."""
        results = [
            {'text': 'Some garbage', 'confidence': 0.9},
            {'text': 'FT', 'confidence': 0.8}
        ]
        assert validator.looks_like_ft_content(results) is True

    def test_case_insensitive_ft_check(self, validator):
        """FT check should be case insensitive."""
        results = [{'text': 'ft', 'confidence': 0.9}]
        assert validator.looks_like_ft_content(results) is True

    def test_case_insensitive_team_code_check(self, validator):
        """Team code check should be case insensitive."""
        results = [{'text': 'liv', 'confidence': 0.9}]
        # Codes are stored uppercase, and we uppercase the text
        assert validator.looks_like_ft_content(results) is True
