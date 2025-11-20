"""
Tests for running order output display logic.

Covers 3 bugs discovered during Episode 02 analysis (Task 012-03):
1. Ground truth showing Episode 01 data for all episodes
2. Contradictory boundary strategy labels ("venue not detected" → "using venue")
3. Missing detection event details (FT graphics, scoreboards)
"""

import pytest
from click.testing import CliRunner
from io import StringIO
import sys

from motd.cli.running_order_output import (
    display_running_order_results,
    _get_boundary_strategy_label,
    _display_detection_events
)
from motd.pipeline.models import (
    MatchBoundary,
    BoundaryValidation,
    RunningOrderResult
)


# ============================================================
# Test Class 1: Ground Truth Display Logic
# ============================================================

class TestGroundTruthDisplay:
    """Test that ground truth only displays when data exists for the episode."""

    def test_ground_truth_none_hides_section(self, capsys):
        """When ground_truth is None, don't show 'Ground Truth:' section."""
        result = RunningOrderResult(
            matches=[
                MatchBoundary(
                    teams=("Tottenham Hotspur", "Manchester United"),
                    position=1,
                    match_start=60.0,
                    highlights_start=90.0,
                    highlights_end=600.0,
                    match_end=700.0,
                    confidence=0.9,
                    venue_result={'timestamp': 60.0}
                )
            ],
            strategy_results={},
            consensus_confidence=1.0
        )

        display_running_order_results(result, ground_truth=None, fixtures=[])

        captured = capsys.readouterr()
        assert "Ground Truth:" not in captured.out

    def test_ground_truth_empty_dict_hides_section(self, capsys):
        """When ground_truth is {}, don't show 'Ground Truth:' section."""
        result = RunningOrderResult(
            matches=[
                MatchBoundary(
                    teams=("Tottenham Hotspur", "Manchester United"),
                    position=1,
                    match_start=60.0,
                    highlights_start=90.0,
                    highlights_end=600.0,
                    match_end=700.0,
                    confidence=0.9,
                    venue_result={'timestamp': 60.0}
                )
            ],
            strategy_results={},
            consensus_confidence=1.0
        )

        display_running_order_results(result, ground_truth={}, fixtures=[])

        captured = capsys.readouterr()
        assert "Ground Truth:" not in captured.out

    def test_ground_truth_episode01_shows_section(self, capsys):
        """When ground_truth has data, show 'Ground Truth:' section."""
        result = RunningOrderResult(
            matches=[
                MatchBoundary(
                    teams=("Liverpool", "Aston Villa"),
                    position=1,
                    match_start=61.0,
                    highlights_start=180.0,
                    highlights_end=607.3,
                    match_end=866.0,
                    confidence=0.9,
                    venue_result={'timestamp': 61.0}
                )
            ],
            strategy_results={},
            consensus_confidence=1.0
        )
        ground_truth = {1: 61}  # Episode 01 match 1: 00:01:01

        display_running_order_results(result, ground_truth, fixtures=[])

        captured = capsys.readouterr()
        assert "Ground Truth:        01:01" in captured.out


# ============================================================
# Test Class 2: Boundary Strategy Label Generation
# ============================================================

class TestBoundaryStrategyLabel:
    """Test that boundary strategy label reflects actual detection."""

    def test_venue_detected_shows_venue_label(self):
        """When venue detected, show 'using venue'."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            venue_result={'timestamp': 60.0, 'venue': 'Tottenham Hotspur Stadium'}
        )

        label = _get_boundary_strategy_label(match)
        assert label == "Boundaries (using venue)"

    def test_venue_validated_by_clustering_shows_full_label(self):
        """When venue validated by clustering, show full label."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            venue_result={'timestamp': 60.0},
            clustering_result={'timestamp': 62.0},
            validation=BoundaryValidation(
                status='validated',
                venue_timestamp=60.0,
                clustering_timestamp=62.0,
                difference_seconds=2.0,
                agreement=True,
                confidence=1.0
            )
        )

        label = _get_boundary_strategy_label(match)
        assert label == "Boundaries (using venue, validated by clustering)"

    def test_venue_failed_clustering_used_shows_fallback_label(self):
        """When venue failed and clustering used, show fallback label."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.7,
            venue_result=None,
            clustering_result={'timestamp': 62.0}
        )

        label = _get_boundary_strategy_label(match)
        assert label == "Boundaries (using clustering - venue failed)"

    def test_both_failed_team_mention_used_shows_final_fallback(self):
        """When both strategies failed, show team mention fallback."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.5,
            venue_result=None,
            clustering_result=None,
            team_mention_result={'timestamp': 60.0}
        )

        label = _get_boundary_strategy_label(match)
        assert label == "Boundaries (using team mention - venue & clustering failed)"

    def test_venue_none_timestamp_treated_as_not_detected(self):
        """When venue_result exists but timestamp is None, treat as not detected."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.7,
            venue_result={'timestamp': None},  # Exists but no timestamp
            clustering_result={'timestamp': 62.0}
        )

        label = _get_boundary_strategy_label(match)
        assert label == "Boundaries (using clustering - venue failed)"


# ============================================================
# Test Class 3: Detection Events Display
# ============================================================

class TestDetectionEventsDisplay:
    """Test detection event details for debugging."""

    def test_ft_graphic_shows_timestamp(self, capsys):
        """When FT graphic detected, show timestamp."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            ft_graphic_time=600.0
        )

        _display_detection_events(match, 1, [match])

        captured = capsys.readouterr()
        assert "Detection Events:" in captured.out
        assert "FT Graphic:      10:00 (600.0s)" in captured.out

    def test_first_scoreboard_shows_timestamp(self, capsys):
        """When first scoreboard detected, show timestamp."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            first_scoreboard_time=185.0
        )

        _display_detection_events(match, 1, [match])

        captured = capsys.readouterr()
        assert "Detection Events:" in captured.out
        assert "First Scoreboard: 03:05 (185.0s)" in captured.out

    def test_both_events_show_in_order(self, capsys):
        """When both FT graphic and scoreboard detected, show both."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            ft_graphic_time=600.0,
            first_scoreboard_time=185.0
        )

        _display_detection_events(match, 1, [match])

        captured = capsys.readouterr()
        output = captured.out
        assert "Detection Events:" in output
        # FT graphic should appear before scoreboard in display order
        ft_pos = output.index("FT Graphic:")
        sb_pos = output.index("First Scoreboard:")
        assert ft_pos < sb_pos

    def test_no_events_hides_section(self, capsys):
        """When no detection events, don't show section."""
        match = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=600.0,
            match_end=700.0,
            confidence=0.9,
            ft_graphic_time=None,
            first_scoreboard_time=None
        )

        _display_detection_events(match, 1, [match])

        captured = capsys.readouterr()
        assert "Detection Events:" not in captured.out

    def test_timestamp_formatting_minutes_seconds(self, capsys):
        """Test timestamp formatting for various durations."""
        # 11:33 (693 seconds)
        match1 = MatchBoundary(
            teams=("Arsenal", "Sunderland"),
            position=1,
            match_start=60.0,
            highlights_start=90.0,
            highlights_end=693.0,
            match_end=700.0,
            confidence=0.9,
            ft_graphic_time=693.0
        )

        _display_detection_events(match1, 1, [match1])

        captured = capsys.readouterr()
        assert "11:33 (693.0s)" in captured.out


# ============================================================
# Integration Tests
# ============================================================

class TestRunningOrderOutputIntegration:
    """Integration tests for full display_running_order_results() flow."""

    def test_episode02_no_ground_truth_shows_correct_labels(self, capsys):
        """
        Episode 02 integration test:
        - No ground truth section
        - Correct strategy labels (clustering used for most matches)
        - Detection events visible
        """
        # Match 1: Arsenal vs Sunderland (venue detected, validated)
        match1 = MatchBoundary(
            teams=("Arsenal", "Sunderland"),
            position=1,
            match_start=126.0,
            highlights_start=180.0,
            highlights_end=693.0,
            match_end=1078.0,
            confidence=0.9,
            venue_result={'timestamp': 126.0},
            clustering_result={'timestamp': 126.0},
            validation=BoundaryValidation(
                status='validated',
                venue_timestamp=126.0,
                clustering_timestamp=126.0,
                difference_seconds=0.0,
                agreement=True,
                confidence=1.0
            ),
            ft_graphic_time=693.0,
            first_scoreboard_time=185.0
        )

        # Match 2: Spurs vs Man Utd (venue failed, clustering used)
        match2 = MatchBoundary(
            teams=("Tottenham Hotspur", "Manchester United"),
            position=2,
            match_start=1078.0,
            highlights_start=1122.0,
            highlights_end=1579.0,
            match_end=1892.0,
            confidence=0.7,
            venue_result=None,
            clustering_result={'timestamp': 1078.0},
            ft_graphic_time=None,  # Missing (Episode 02 had 4/5 detected)
            first_scoreboard_time=1122.0
        )

        result = RunningOrderResult(
            matches=[match1, match2],
            strategy_results={},
            consensus_confidence=1.0
        )

        display_running_order_results(result, ground_truth=None, fixtures=[])

        captured = capsys.readouterr()
        output = captured.out

        # Verify no ground truth
        assert "Ground Truth:" not in output

        # Verify strategy labels
        assert "Boundaries (using venue, validated by clustering)" in output
        assert "Boundaries (using clustering - venue failed)" in output

        # Verify detection events for match 1
        assert "FT Graphic:      11:33 (693.0s)" in output
        assert "First Scoreboard: 03:05 (185.0s)" in output
