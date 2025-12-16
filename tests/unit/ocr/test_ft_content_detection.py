"""Tests for _looks_like_ft_content() method in OCRReader.

This method performs a quick check to determine if OCR results from the FT region
look like genuine FT graphic content, allowing fallback to scoreboard if not.
"""

import pytest
import yaml
from pathlib import Path
from motd.ocr.reader import OCRReader


@pytest.fixture
def ocr_reader():
    """Create OCR reader with config."""
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    return OCRReader(config['ocr'])


class TestLooksLikeFTContent:
    """Tests for _looks_like_ft_content() method."""

    def test_empty_results_returns_false(self, ocr_reader):
        """Empty results should not look like FT content."""
        assert ocr_reader._looks_like_ft_content([]) is False

    def test_ft_indicator_returns_true(self, ocr_reader):
        """Results with FT indicator should be accepted."""
        results = [{'text': 'Liverpool 2 FT', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_full_time_indicator_returns_true(self, ocr_reader):
        """Results with FULL TIME indicator should be accepted."""
        results = [{'text': 'FULL TIME', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_score_pattern_returns_true(self, ocr_reader):
        """Results with score pattern should be accepted."""
        results = [{'text': '2 - 1', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_score_pattern_with_pipe_returns_true(self, ocr_reader):
        """Results with BBC-style pipe score should be accepted."""
        results = [{'text': '0 | 0', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_team_code_returns_true(self, ocr_reader):
        """Results with valid team code should be accepted."""
        results = [{'text': 'LIV', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_newcastle_code_returns_true(self, ocr_reader):
        """Results with NEW team code should be accepted."""
        results = [{'text': 'NEW', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_manchester_city_mnc_code_returns_true(self, ocr_reader):
        """Results with MNC team code should be accepted (after fix)."""
        results = [{'text': 'MNC', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_garbage_text_returns_false(self, ocr_reader):
        """Random text should not look like FT content."""
        results = [{'text': 'tator: Steve Bower', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is False

    def test_commentator_credit_returns_false(self, ocr_reader):
        """Commentator credit text should not look like FT content."""
        results = [{'text': 'Commentator: John Smith', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is False

    def test_partial_word_not_matched_as_code(self, ocr_reader):
        """Words containing codes shouldn't match (e.g., 'NEW' in 'NEWCASTLE')."""
        # This tests that we match whole words only
        results = [{'text': 'NEWCASTLE', 'confidence': 0.9}]
        # 'NEWCASTLE' split gives ['NEWCASTLE'] which isn't in codes
        # But wait - we do have 'NEW' as a code...
        # Actually split() on 'NEWCASTLE' gives ['NEWCASTLE'], not ['NEW']
        # So this should return False
        assert ocr_reader._looks_like_ft_content(results) is False

    def test_multiple_results_any_match(self, ocr_reader):
        """If any result has FT content, should return True."""
        results = [
            {'text': 'Some garbage', 'confidence': 0.9},
            {'text': 'FT', 'confidence': 0.8}
        ]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_case_insensitive_ft_check(self, ocr_reader):
        """FT check should be case insensitive."""
        results = [{'text': 'ft', 'confidence': 0.9}]
        assert ocr_reader._looks_like_ft_content(results) is True

    def test_case_insensitive_team_code_check(self, ocr_reader):
        """Team code check should be case insensitive."""
        results = [{'text': 'liv', 'confidence': 0.9}]
        # Codes are stored uppercase, and we uppercase the text
        assert ocr_reader._looks_like_ft_content(results) is True
