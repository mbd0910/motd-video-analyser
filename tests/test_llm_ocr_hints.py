"""Tests for OCRHintsExtractor."""

import json
import pytest
from pathlib import Path

from motd.llm.ocr_hints import (
    OCRHintsExtractor,
    OCRHints,
    FTGraphicHint,
    ScoreboardHint,
)


class TestFTGraphicHint:
    """Tests for FTGraphicHint dataclass."""

    def test_timestamp_formatted(self):
        """Test timestamp formatting."""
        hint = FTGraphicHint(
            timestamp_seconds=666.0,
            home_team="Liverpool",
            away_team="Nottingham Forest",
        )
        assert hint.timestamp_formatted == "11:06"

    def test_timestamp_formatted_zero(self):
        """Test timestamp formatting for zero."""
        hint = FTGraphicHint(
            timestamp_seconds=0,
            home_team="Team A",
            away_team="Team B",
        )
        assert hint.timestamp_formatted == "00:00"

    def test_timestamp_formatted_large(self):
        """Test timestamp formatting for large values."""
        hint = FTGraphicHint(
            timestamp_seconds=4833.7,  # ~80 minutes
            home_team="Fulham",
            away_team="Sunderland",
        )
        assert hint.timestamp_formatted == "80:33"


class TestScoreboardHint:
    """Tests for ScoreboardHint dataclass."""

    def test_timestamp_formatted(self):
        """Test timestamp formatting."""
        hint = ScoreboardHint(
            timestamp_seconds=127.06,
            home_team="Liverpool",
            away_team="Nottingham Forest",
        )
        assert hint.timestamp_formatted == "02:07"


class TestOCRHints:
    """Tests for OCRHints dataclass."""

    def test_has_hints_with_ft_graphics(self):
        """Test has_hints with FT graphics only."""
        hints = OCRHints(
            ft_graphics=[
                FTGraphicHint(0, "Team A", "Team B"),
            ],
            first_scoreboards=[],
        )
        assert hints.has_hints is True

    def test_has_hints_with_scoreboards(self):
        """Test has_hints with scoreboards only."""
        hints = OCRHints(
            ft_graphics=[],
            first_scoreboards=[
                ScoreboardHint(0, "Team A", "Team B"),
            ],
        )
        assert hints.has_hints is True

    def test_has_hints_empty(self):
        """Test has_hints when empty."""
        hints = OCRHints()
        assert hints.has_hints is False


class TestOCRHintsExtractorFTGraphics:
    """Tests for FT graphics extraction."""

    def test_extract_ft_graphics_basic(self):
        """Test basic FT graphics extraction."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [
                {"match_id": "2025-11-22-liverpool-forest", "home_team": "Liverpool", "away_team": "Nottingham Forest"},
            ],
            "ocr_results": [
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 666.0,
                    "validated_teams": ["Liverpool", "Nottingham Forest"],
                    "matched_fixture": "2025-11-22-liverpool-forest",
                    "detected_teams": [
                        {"team": "Liverpool", "confidence": 1.0},
                        {"team": "Nottingham Forest", "confidence": 1.0},
                    ],
                },
            ],
        }

        hints = extractor.extract_ft_graphics(ocr_results)

        assert len(hints) == 1
        assert hints[0].home_team == "Liverpool"
        assert hints[0].away_team == "Nottingham Forest"
        assert hints[0].timestamp_seconds == 666.0
        assert hints[0].confidence == 1.0

    def test_extract_ft_graphics_skips_scoreboard(self):
        """Test that scoreboard sources are skipped."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [],
            "ocr_results": [
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 100.0,
                    "validated_teams": ["Team A", "Team B"],
                },
            ],
        }

        hints = extractor.extract_ft_graphics(ocr_results)

        assert len(hints) == 0

    def test_extract_ft_graphics_filters_low_confidence(self):
        """Test that low confidence results are filtered."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [],
            "ocr_results": [
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 100.0,
                    "validated_teams": ["Team A", "Team B"],
                    "detected_teams": [
                        {"team": "Team A", "confidence": 0.5},
                        {"team": "Team B", "confidence": 0.5},
                    ],
                },
            ],
        }

        hints = extractor.extract_ft_graphics(ocr_results, min_confidence=0.7)

        assert len(hints) == 0

    def test_extract_ft_graphics_sorted_by_timestamp(self):
        """Test that results are sorted by timestamp."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [],
            "ocr_results": [
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 500.0,
                    "validated_teams": ["Team C", "Team D"],
                },
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 200.0,
                    "validated_teams": ["Team A", "Team B"],
                },
            ],
        }

        hints = extractor.extract_ft_graphics(ocr_results)

        assert len(hints) == 2
        assert hints[0].timestamp_seconds == 200.0
        assert hints[1].timestamp_seconds == 500.0


class TestOCRHintsExtractorScoreboards:
    """Tests for first scoreboard extraction."""

    def test_extract_first_scoreboards_basic(self):
        """Test basic first scoreboard extraction."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [
                {"match_id": "match-1", "home_team": "Team A", "away_team": "Team B"},
            ],
            "ocr_results": [
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 100.0,
                    "validated_teams": ["Team A", "Team B"],
                    "matched_fixture": "match-1",
                },
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 150.0,
                    "validated_teams": ["Team A", "Team B"],
                    "matched_fixture": "match-1",
                },
            ],
        }

        hints = extractor.extract_first_scoreboards(ocr_results)

        # Should only get the first one (100.0s)
        assert len(hints) == 1
        assert hints[0].timestamp_seconds == 100.0

    def test_extract_first_scoreboards_multiple_matches(self):
        """Test first scoreboard per match."""
        extractor = OCRHintsExtractor("/fake/path")
        ocr_results = {
            "expected_fixtures": [
                {"match_id": "match-1", "home_team": "Team A", "away_team": "Team B"},
                {"match_id": "match-2", "home_team": "Team C", "away_team": "Team D"},
            ],
            "ocr_results": [
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 100.0,
                    "validated_teams": ["Team A", "Team B"],
                    "matched_fixture": "match-1",
                },
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 200.0,
                    "validated_teams": ["Team C", "Team D"],
                    "matched_fixture": "match-2",
                },
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 300.0,
                    "validated_teams": ["Team A", "Team B"],
                    "matched_fixture": "match-1",
                },
            ],
        }

        hints = extractor.extract_first_scoreboards(ocr_results)

        assert len(hints) == 2
        assert hints[0].timestamp_seconds == 100.0  # match-1
        assert hints[1].timestamp_seconds == 200.0  # match-2


class TestOCRHintsExtractorFormatting:
    """Tests for hint formatting."""

    def test_format_hints_section_empty(self):
        """Test formatting with no hints."""
        extractor = OCRHintsExtractor("/fake/path")
        hints = OCRHints()

        result = extractor.format_hints_section(hints)

        assert result == ""

    def test_format_hints_section_ft_only(self):
        """Test formatting with FT graphics only."""
        extractor = OCRHintsExtractor("/fake/path")
        hints = OCRHints(
            ft_graphics=[
                FTGraphicHint(666.0, "Liverpool", "Nottingham Forest"),
                FTGraphicHint(1667.8, "Newcastle United", "Manchester City"),
            ],
        )

        result = extractor.format_hints_section(hints)

        assert "## Image Analysis Hints (Advisory)" in result
        assert "Full-Time Graphics Detected" in result
        assert "11:06 - Liverpool vs Nottingham Forest" in result
        assert "27:47 - Newcastle United vs Manchester City" in result
        assert "First Scoreboard" not in result

    def test_format_hints_section_both(self):
        """Test formatting with both FT and scoreboards."""
        extractor = OCRHintsExtractor("/fake/path")
        hints = OCRHints(
            ft_graphics=[
                FTGraphicHint(666.0, "Liverpool", "Nottingham Forest"),
            ],
            first_scoreboards=[
                ScoreboardHint(127.06, "Liverpool", "Nottingham Forest"),
            ],
        )

        result = extractor.format_hints_section(hints)

        assert "Full-Time Graphics Detected" in result
        assert "First Scoreboard Appearances" in result
        assert "may contain errors" in result


class TestOCRHintsExtractorIntegration:
    """Integration tests using mock OCR data."""

    def test_extract_full_pipeline(self, tmp_path: Path):
        """Test full extraction pipeline."""
        ocr_data = {
            "expected_fixtures": [
                {"match_id": "2025-11-22-liverpool-forest", "home_team": "Liverpool", "away_team": "Nottingham Forest"},
                {"match_id": "2025-11-22-newcastle-mancity", "home_team": "Newcastle United", "away_team": "Manchester City"},
            ],
            "ocr_results": [
                # Scoreboard at 127s
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 127.0,
                    "validated_teams": ["Liverpool", "Nottingham Forest"],
                    "matched_fixture": "2025-11-22-liverpool-forest",
                },
                # FT at 666s
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 666.0,
                    "validated_teams": ["Liverpool", "Nottingham Forest"],
                    "matched_fixture": "2025-11-22-liverpool-forest",
                    "detected_teams": [
                        {"team": "Liverpool", "confidence": 1.0},
                        {"team": "Nottingham Forest", "confidence": 1.0},
                    ],
                },
                # Second match scoreboard
                {
                    "ocr_source": "scoreboard",
                    "start_seconds": 1200.0,
                    "validated_teams": ["Newcastle United", "Manchester City"],
                    "matched_fixture": "2025-11-22-newcastle-mancity",
                },
                # Second match FT
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 1667.8,
                    "validated_teams": ["Newcastle United", "Manchester City"],
                    "matched_fixture": "2025-11-22-newcastle-mancity",
                },
            ],
        }

        ocr_path = tmp_path / "ocr_results.json"
        with open(ocr_path, "w") as f:
            json.dump(ocr_data, f)

        extractor = OCRHintsExtractor(tmp_path)
        hints = extractor.extract()

        assert len(hints.ft_graphics) == 2
        assert len(hints.first_scoreboards) == 2
        assert hints.has_hints is True

        # Check FT graphics are sorted
        assert hints.ft_graphics[0].timestamp_seconds == 666.0
        assert hints.ft_graphics[1].timestamp_seconds == 1667.8

        # Check formatting works
        formatted = extractor.format_hints_section(hints)
        assert "Liverpool vs Nottingham Forest" in formatted
        assert "Newcastle United vs Manchester City" in formatted

    def test_extract_missing_ocr_results(self, tmp_path: Path):
        """Test extraction when OCR results don't exist."""
        extractor = OCRHintsExtractor(tmp_path)
        hints = extractor.extract()

        assert hints.has_hints is False
        assert len(hints.ft_graphics) == 0
        assert len(hints.first_scoreboards) == 0
