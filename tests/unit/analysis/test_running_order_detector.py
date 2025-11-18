"""
Unit tests for RunningOrderDetector.

Tests multi-strategy running order detection using real OCR data from
motd_2025-26_2025-11-01 episode.

Follows TDD approach: Write tests first, then implement detector.
"""

import json
import pytest
from pathlib import Path

from src.motd.analysis.running_order_detector import RunningOrderDetector
from src.motd.pipeline.models import RunningOrderResult, MatchBoundary


@pytest.fixture
def ocr_results():
    """Load real OCR results for integration testing."""
    ocr_path = Path('data/cache/motd_2025-26_2025-11-01/ocr_results.json')
    with open(ocr_path) as f:
        data = json.load(f)
    return data['ocr_results']


@pytest.fixture
def transcript():
    """Load real transcript for mention clustering."""
    transcript_path = Path('data/cache/motd_2025-26_2025-11-01/transcript.json')
    with open(transcript_path) as f:
        return json.load(f)


@pytest.fixture
def team_names():
    """Load Premier League team names."""
    teams_path = Path('data/teams/premier_league_2025_26.json')
    with open(teams_path) as f:
        teams_data = json.load(f)
    return [team['full'] for team in teams_data['teams']]


@pytest.fixture
def detector(ocr_results, transcript, team_names):
    """Create RunningOrderDetector with real data."""
    return RunningOrderDetector(
        ocr_results=ocr_results,
        transcript=transcript,
        team_names=team_names
    )


# Ground truth from visual_patterns.md (validated in 011c-1)
EXPECTED_RUNNING_ORDER = [
    ('Aston Villa', 'Liverpool'),           # Position 1
    ('Arsenal', 'Burnley'),                 # Position 2
    ('Manchester United', 'Nottingham Forest'),  # Position 3
    ('Fulham', 'Wolverhampton Wanderers'),  # Position 4
    ('Chelsea', 'Tottenham Hotspur'),       # Position 5
    ('Brighton & Hove Albion', 'Leeds United'),  # Position 6
    ('Brentford', 'Crystal Palace')         # Position 7
]


class TestScoreboardStrategy:
    """Test Strategy 1: Scoreboard appearance order detection."""

    def test_detects_7_matches(self, detector):
        """Should detect exactly 7 matches from scoreboard appearances."""
        result = detector.detect_from_scoreboards()
        assert len(result) == 7, "Should detect 7 matches"

    def test_correct_order(self, detector):
        """Should match ground truth running order."""
        result = detector.detect_from_scoreboards()

        for i, (detected, expected) in enumerate(zip(result, EXPECTED_RUNNING_ORDER), 1):
            assert detected == expected, f"Position {i} mismatch: got {detected}, expected {expected}"

    def test_first_match_is_liverpool_villa(self, detector):
        """First match should be Liverpool vs Aston Villa."""
        result = detector.detect_from_scoreboards()
        assert result[0] == ('Aston Villa', 'Liverpool'), "First match should be Liverpool vs Aston Villa"

    def test_abundant_detections(self, detector):
        """Each match should have multiple scoreboard detections (validation)."""
        counts = detector._count_scoreboard_detections_per_match()

        assert len(counts) == 7, "Should have counts for 7 matches"
        for teams, count in counts.items():
            assert count >= 30, f"{teams} should have >=30 scoreboard detections, got {count}"


class TestFTGraphicStrategy:
    """Test Strategy 2: FT graphic appearance order detection."""

    def test_detects_7_ft_graphics(self, detector):
        """Should detect exactly 7 FT graphics (one per match)."""
        result = detector.detect_from_ft_graphics()
        assert len(result) == 7, "Should detect 7 FT graphics after deduplication"

    def test_correct_order(self, detector):
        """Should match ground truth running order."""
        result = detector.detect_from_ft_graphics()

        for i, (detected, expected) in enumerate(zip(result, EXPECTED_RUNNING_ORDER), 1):
            assert detected == expected, f"Position {i} mismatch: got {detected}, expected {expected}"

    def test_deduplication_works(self, detector):
        """Should handle duplicate FT graphics (same match within 5s)."""
        # Known duplicate: Nottingham Forest vs Man Utd (scenes 597 & 598, 1s apart)
        raw_ft_graphics = detector._get_raw_ft_graphics()
        deduplicated = detector.detect_from_ft_graphics()

        assert len(raw_ft_graphics) >= 7, "Should find at least 7 raw FT graphics"
        assert len(deduplicated) == 7, "Should deduplicate to exactly 7"

    def test_ft_graphic_timestamps_reasonable(self, detector):
        """FT graphics should be spaced reasonably (not all at once)."""
        timestamps = detector._get_ft_graphic_timestamps()

        assert len(timestamps) == 7
        for i in range(len(timestamps) - 1):
            gap = timestamps[i+1] - timestamps[i]
            assert gap > 60, f"FT graphics {i} and {i+1} should be >60s apart, got {gap}s"


class TestCrossValidation:
    """Test cross-validation consensus logic."""

    def test_all_strategies_agree(self, detector):
        """Both strategies should produce identical running order."""
        result = detector.detect_running_order()

        # Check consensus
        assert result.consensus_confidence == 1.0, "Both strategies should agree (100% consensus)"
        assert len(result.disagreements) == 0, "Should have no disagreements"

    def test_running_order_result_structure(self, detector):
        """Result should have correct structure."""
        result = detector.detect_running_order()

        assert isinstance(result, RunningOrderResult)
        assert len(result.matches) == 7
        assert 'scoreboard' in result.strategy_results
        assert 'ft_graphic' in result.strategy_results
        assert len(result.strategy_results) == 2, "Should have exactly 2 strategies"

    def test_each_match_has_boundaries(self, detector):
        """Each match should have detected boundaries."""
        result = detector.detect_running_order()

        for i, match in enumerate(result.matches, 1):
            assert isinstance(match, MatchBoundary)
            assert match.position == i
            assert match.highlights_start is not None, f"Match {i} should have highlights_start"
            assert match.highlights_end is not None, f"Match {i} should have highlights_end"
            assert match.confidence > 0.8, f"Match {i} should have high confidence"

    def test_strategy_results_all_length_7(self, detector):
        """Each strategy should detect 7 matches."""
        result = detector.detect_running_order()

        assert len(result.strategy_results) == 2, "Should have exactly 2 strategies"
        for strategy_name, matches in result.strategy_results.items():
            assert len(matches) == 7, f"{strategy_name} should detect 7 matches, got {len(matches)}"


class TestBoundaryDetection:
    """Test boundary detection from mention clustering."""

    def test_highlights_boundaries_detected(self, detector):
        """Should detect highlights start/end for all matches."""
        result = detector.detect_running_order()

        for match in result.matches:
            assert match.highlights_start is not None
            assert match.highlights_end is not None
            assert match.highlights_end > match.highlights_start

    def test_ft_graphic_marks_highlights_end(self, detector):
        """FT graphic timestamp should match highlights_end."""
        result = detector.detect_running_order()

        for match in result.matches:
            assert match.highlights_end == match.ft_graphic_time, \
                f"{match.teams}: highlights_end should equal FT graphic time"

    def test_boundaries_sequential(self, detector):
        """Match boundaries should not overlap (sequential order)."""
        result = detector.detect_running_order()

        for i in range(len(result.matches) - 1):
            current = result.matches[i]
            next_match = result.matches[i + 1]

            if current.match_end and next_match.match_start:
                assert current.match_end <= next_match.match_start, \
                    f"Match {i+1} should end before Match {i+2} starts"

    def test_detection_sources_populated(self, detector):
        """Each match should have detection_sources list."""
        result = detector.detect_running_order()

        for match in result.matches:
            assert len(match.detection_sources) > 0
            assert 'scoreboard' in match.detection_sources or 'ft_graphic' in match.detection_sources


# Integration test: End-to-end
class TestIntegration:
    """End-to-end integration test."""

    def test_full_pipeline_produces_valid_running_order(self, detector):
        """Complete pipeline should produce valid 7-match running order."""
        result = detector.detect_running_order()

        # Structure validation
        assert isinstance(result, RunningOrderResult)
        assert len(result.matches) == 7

        # Content validation (matches ground truth)
        for i, (match, expected) in enumerate(zip(result.matches, EXPECTED_RUNNING_ORDER), 1):
            assert match.teams == expected, f"Position {i}: expected {expected}, got {match.teams}"
            assert match.position == i

        # Confidence validation
        assert result.consensus_confidence >= 0.9, "Should have high cross-validation confidence"

    def test_can_serialize_to_json(self, detector):
        """Result should be JSON-serializable (Pydantic model)."""
        result = detector.detect_running_order()

        # Should not raise
        json_str = result.model_dump_json()
        assert len(json_str) > 0

        # Should be deserializable
        reconstructed = RunningOrderResult.model_validate_json(json_str)
        assert len(reconstructed.matches) == 7
