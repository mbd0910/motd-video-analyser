"""Unit tests for FT graphic validation logic."""

import pytest
from motd.ocr.reader import OCRReader


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

    def test_valid_only_one_team_tier1(self, ocr_reader):
        """Valid (Tier 1): Only 1 team detected + FT (updated from strict validation)."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': '2 - 1'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool']

        # New behavior: Tier 1 allows ≥1 team + FT (score optional)
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_valid_three_teams_tier1(self, ocr_reader):
        """Valid (Tier 1): 3 teams detected + FT (updated from strict validation)."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': 'Arsenal'},
            {'text': 'Chelsea'},
            {'text': '2 - 1'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool', 'Arsenal', 'Chelsea']

        # New behavior: Tier 1 allows ≥1 team + FT (even if 3 teams detected)
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_valid_no_score_pattern_tier1(self, ocr_reader):
        """Valid (Tier 1): Has 2 teams and FT but no score (updated from strict validation)."""
        ocr_results = [
            {'text': 'Liverpool'},
            {'text': 'Aston Villa'},
            {'text': 'FT'}
        ]
        detected_teams = ['Liverpool', 'Aston Villa']

        # New behavior: Tier 1 allows teams + FT without score pattern
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

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


class TestFTValidationTwoTier:
    """
    Test two-tier FT validation logic (prioritize teams + FT over score).

    Uses real OCR data from Episode 01 and Episode 02 to test:
    - Tier 1: Team name(s) + FT indicator (score optional)
    - Tier 2: Score pattern + FT indicator (fallback when teams not detected)
    """

    @pytest.fixture
    def ocr_reader(self):
        """Create OCRReader instance for testing."""
        config = {
            'library': 'easyocr',
            'languages': ['en'],
            'gpu': False
        }
        return OCRReader(config)

    def test_tier1_forest_manutd_draw_complete_signals(self, ocr_reader):
        """
        Tier 1: Real OCR from Episode 01 - Nottingham Forest vs Man Utd (2-2 draw).

        All signals present:
        - Both teams: 79.33%, 100% (non-bold, draw result)
        - Complete score "2 2": 100%, 100%
        - FT: 99.59%

        Expected: PASS (Tier 1: teams + FT)
        """
        ocr_results = [
            {'text': 'Nottingham Forest'},
            {'text': '2'},
            {'text': '2'},
            {'text': 'Manchester United'},
            {'text': 'FT'},
            {'text': 'Casemiro 34\', Diallo 81\''},  # Scorer names (noise)
        ]
        detected_teams = ['Nottingham Forest', 'Manchester United']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_tier1_liverpool_villa_one_team_missing(self, ocr_reader):
        """
        Tier 1: Real OCR from Episode 01 - Liverpool vs Aston Villa (2-0).

        Liverpool (bold, winner): 100% confidence
        Aston Villa (non-bold, loser): 54.11% → REJECTED (below 0.7 threshold)
        Score "2 0": 100%, 100%
        FT: 99.73%

        Expected: PASS (Tier 1: ≥1 team + FT is sufficient)
        """
        ocr_results = [
            {'text': 'Liverpool'},  # Winner (bold text)
            {'text': '2'},
            {'text': '0'},
            # Aston Villa rejected (confidence 0.5411 < 0.7)
            {'text': 'FT'},
            {'text': 'Gravenberch 58\''},  # Scorer name
        ]
        detected_teams = ['Liverpool']  # Only one team matched

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_tier1_spurs_manutd_incomplete_score_episode02(self, ocr_reader):
        """
        Tier 1: Real OCR from Episode 02 - Tottenham vs Man Utd (2-2 draw).

        **THE BUG THIS FIX ADDRESSES:**
        - Tottenham Hotspur: 99.98% (non-bold)
        - First '2': 100%
        - Second '2': 65.67% → REJECTED (below 0.7 threshold)
        - Manchester United: 77.14% (non-bold)
        - FT: 99.87%

        Score becomes "2" instead of "2 2", failing old score pattern validation.

        Expected: PASS (Tier 1: teams + FT, score optional)
        """
        ocr_results = [
            {'text': 'Tottenham Hotspur'},
            {'text': '2'},
            # Second '2' rejected (confidence 0.6567)
            {'text': 'Manchester United'},
            {'text': 'FT'},
            {'text': 'Mbeumo 32\', de Ligt 90\'+6\''},
        ]
        detected_teams = ['Tottenham Hotspur', 'Manchester United']

        # This is the key test - should PASS with new logic, FAILS with old
        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_tier2_score_plus_ft_no_teams_fallback(self, ocr_reader):
        """
        Tier 2: OCR missed team names, but score + FT detected (fallback tier).

        Scenario: Team name OCR completely failed, but numeric score is clear.

        Expected: PASS (Tier 2: score + FT fallback)
        """
        ocr_results = [
            {'text': '3'},
            {'text': '1'},
            {'text': 'FT'},
        ]
        detected_teams = []  # No teams detected

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_tier1_teams_plus_ft_no_score(self, ocr_reader):
        """
        Tier 1: Teams + FT, but score completely missing (OCR failed to read score).

        Expected: PASS (Tier 1: teams + FT, score optional)
        """
        ocr_results = [
            {'text': 'Arsenal'},
            {'text': 'Burnley'},
            {'text': 'FT'},
        ]
        detected_teams = ['Arsenal', 'Burnley']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is True

    def test_reject_no_ft_indicator_tier1_fail(self, ocr_reader):
        """
        Tier 1 rejection: Teams present but no FT indicator.

        Filters out formation graphics, studio overlays with team mentions.
        """
        ocr_results = [
            {'text': 'Chelsea'},
            {'text': '2'},
            {'text': '1'},
            {'text': 'Wolves'},
        ]
        detected_teams = ['Chelsea', 'Wolverhampton Wanderers']

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_reject_score_only_no_ft_tier2_fail(self, ocr_reader):
        """
        Tier 2 rejection: Score present but no FT indicator.

        Both tiers require FT indicator.
        """
        ocr_results = [
            {'text': '2'},
            {'text': '1'},
        ]
        detected_teams = []

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False

    def test_reject_ft_only_no_context(self, ocr_reader):
        """
        Rejection: Only FT indicator, no teams or score.

        Filters out commentary mentions of "FT" without context.
        """
        ocr_results = [
            {'text': 'FT'},
        ]
        detected_teams = []

        assert ocr_reader.validate_ft_graphic(ocr_results, detected_teams) is False
