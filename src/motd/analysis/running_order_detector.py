"""
2-strategy running order detection with cross-validation.

Detects match running order using 2 independent strategies:
1. Scoreboard appearance order (most abundant detections)
2. FT graphic appearance order (most reliable anchor points)

Cross-validates both strategies for consensus and confidence scoring.

Note: Boundary detection via transcript/mention clustering deferred to Phase 2.
"""

from collections import defaultdict
from typing import Any

from src.motd.pipeline.models import MatchBoundary, RunningOrderResult


class RunningOrderDetector:
    """
    Multi-strategy running order detector with cross-validation.

    Uses OCR scoreboards, FT graphics, and mention clustering to detect
    the editorial running order of matches in an episode.

    Follows dependency injection pattern: Takes processed data, not file paths.
    """

    def __init__(
        self,
        ocr_results: list[dict[str, Any]],
        transcript: dict[str, Any],
        team_names: list[str]
    ):
        """
        Initialize detector with processed data.

        Args:
            ocr_results: OCR detection results (from ocr_results.json)
            transcript: Whisper transcript (from transcript.json)
            team_names: List of valid team names for matching
        """
        self.ocr_results = ocr_results
        self.transcript = transcript
        self.team_names = team_names

    def detect_running_order(self) -> RunningOrderResult:
        """
        Detect running order using 2-strategy approach with cross-validation.

        Returns:
            RunningOrderResult with ordered matches and consensus metadata
        """
        # Run 2 independent strategies
        scoreboard_order = self.detect_from_scoreboards()
        ft_order = self.detect_from_ft_graphics()

        # Cross-validate
        return self.cross_validate(scoreboard_order, ft_order)

    def detect_from_scoreboards(self) -> list[tuple[str, str]]:
        """
        Strategy 1: Detect running order from first scoreboard appearance per match.

        Returns:
            List of (team1, team2) tuples in running order (normalized/sorted)
        """
        # Filter for scoreboard detections
        scoreboard_scenes = [
            s for s in self.ocr_results
            if s.get('ocr_source') == 'scoreboard'
        ]

        # Group by team pairs, track first appearance
        match_first_appearance = {}

        for scene in scoreboard_scenes:
            teams = scene.get('validated_teams', [])
            if len(teams) >= 2:
                # Normalize team order (alphabetical)
                teams_key = tuple(sorted(teams[:2]))
                timestamp = scene['start_seconds']

                if teams_key not in match_first_appearance:
                    match_first_appearance[teams_key] = timestamp

        # Sort by first appearance time
        running_order = sorted(match_first_appearance.items(), key=lambda x: x[1])

        return [teams for teams, _ in running_order]

    def detect_from_ft_graphics(self) -> list[tuple[str, str]]:
        """
        Strategy 2: Detect running order from FT graphic appearance (with deduplication).

        Returns:
            List of (team1, team2) tuples in running order (normalized/sorted)
        """
        # Get raw FT graphics
        raw_ft_graphics = self._get_raw_ft_graphics()

        # Sort by timestamp
        raw_ft_graphics.sort(key=lambda x: x['start_seconds'])

        # Deduplicate: Keep first FT for each match (remove within 5s)
        deduplicated = []
        last_teams = None
        last_time = None

        for scene in raw_ft_graphics:
            teams = tuple(sorted(scene.get('validated_teams', [])))
            time = scene['start_seconds']

            # If different teams OR >5s gap, it's a new FT graphic
            if teams != last_teams or (last_time and time - last_time > 5):
                deduplicated.append(teams)
                last_teams = teams
                last_time = time

        return deduplicated

    def cross_validate(
        self,
        scoreboard_order: list[tuple[str, str]],
        ft_order: list[tuple[str, str]]
    ) -> RunningOrderResult:
        """
        Cross-validate both strategies and build RunningOrderResult.

        Args:
            scoreboard_order: Order from scoreboards
            ft_order: Order from FT graphics

        Returns:
            RunningOrderResult with matches and consensus metadata
        """
        # Check if both strategies agree
        consensus = (scoreboard_order == ft_order)
        consensus_confidence = 1.0 if consensus else 0.85

        # Use scoreboard order as primary (most abundant detections)
        primary_order = scoreboard_order

        # Build MatchBoundary objects with timestamps
        matches = []
        for i, teams in enumerate(primary_order, 1):
            # Get timestamps for this match
            first_scoreboard = self._get_first_scoreboard_time(teams)
            ft_graphic_time = self._get_ft_graphic_time(teams)

            match = MatchBoundary(
                teams=teams,
                position=i,
                highlights_start=first_scoreboard,
                highlights_end=ft_graphic_time,
                ft_graphic_time=ft_graphic_time,
                first_scoreboard_time=first_scoreboard,
                confidence=0.95,
                detection_sources=['scoreboard', 'ft_graphic']
            )
            matches.append(match)

        # Build result
        return RunningOrderResult(
            matches=matches,
            strategy_results={
                'scoreboard': scoreboard_order,
                'ft_graphic': ft_order
            },
            consensus_confidence=consensus_confidence,
            disagreements=[]
        )

    # Helper methods

    def _get_raw_ft_graphics(self) -> list[dict]:
        """Get raw FT graphics (before deduplication)."""
        return [
            s for s in self.ocr_results
            if s.get('ocr_source') == 'ft_score'
        ]

    def _get_ft_graphic_timestamps(self) -> list[float]:
        """Get FT graphic timestamps (after deduplication)."""
        deduplicated = self.detect_from_ft_graphics()
        timestamps = []

        for teams in deduplicated:
            time = self._get_ft_graphic_time(teams)
            if time:
                timestamps.append(time)

        return timestamps

    def _get_ft_graphic_time(self, teams: tuple[str, str]) -> float | None:
        """Get FT graphic timestamp for specific match."""
        for scene in self._get_raw_ft_graphics():
            scene_teams = tuple(sorted(scene.get('validated_teams', [])))
            if scene_teams == teams:
                return scene['start_seconds']
        return None

    def _get_first_scoreboard_time(self, teams: tuple[str, str]) -> float | None:
        """Get first scoreboard timestamp for specific match."""
        scoreboard_scenes = [
            s for s in self.ocr_results
            if s.get('ocr_source') == 'scoreboard'
        ]

        for scene in scoreboard_scenes:
            scene_teams = tuple(sorted(scene.get('validated_teams', [])))
            if scene_teams == teams:
                return scene['start_seconds']
        return None

    def _count_scoreboard_detections_per_match(self) -> dict[tuple[str, str], int]:
        """Count scoreboard detections for each match (for validation)."""
        counts = defaultdict(int)

        scoreboard_scenes = [
            s for s in self.ocr_results
            if s.get('ocr_source') == 'scoreboard'
        ]

        for scene in scoreboard_scenes:
            teams = scene.get('validated_teams', [])
            if len(teams) >= 2:
                teams_key = tuple(sorted(teams[:2]))
                counts[teams_key] += 1

        return dict(counts)

    def _get_mention_clusters(self) -> dict[tuple[str, str], dict[str, float]]:
        """
        Get mention clusters with first/last mention times.

        TODO(Task 012): Replace with proper transcript-based boundary detection.
        This is a simplified MVP implementation that approximates boundaries using
        scoreboard/FT timestamps with hardcoded offsets (-30s intro, +300s post-match).

        Proper implementation (Task 012) will:
        - Search transcript for first team mention → match_start
        - Set match_end = next match's match_start
        - No hardcoded offsets needed

        See: docs/tasks/012-classifier-integration/012-01-pipeline-integration.md
        """
        # For MVP, use scoreboard spans as proxy for clusters
        clusters = {}
        scoreboard_order = self.detect_from_scoreboards()

        for teams in scoreboard_order:
            first_scoreboard = self._get_first_scoreboard_time(teams)
            ft_time = self._get_ft_graphic_time(teams)

            if first_scoreboard and ft_time:
                clusters[teams] = {
                    'first_mention': first_scoreboard - 30,  # Approximate studio intro
                    'last_mention': ft_time + 300  # Approximate post-match end
                }

        return clusters
