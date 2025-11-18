"""
2-strategy running order detection with cross-validation.

Detects match running order using 2 independent strategies:
1. Scoreboard appearance order (most abundant detections)
2. FT graphic appearance order (most reliable anchor points)

Cross-validates both strategies for consensus and confidence scoring.

Includes transcript-based boundary detection for match_start/match_end.
"""

from collections import defaultdict
from typing import Any, TypedDict
from rapidfuzz import fuzz

from motd.pipeline.models import MatchBoundary, RunningOrderResult


class TeamData(TypedDict, total=False):
    """Structure of team data from teams JSON."""

    full: str
    abbrev: str
    codes: list[str]
    alternates: list[str]


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
        teams_data: list[TeamData],
    ):
        """
        Initialize detector with processed data.

        Args:
            ocr_results: OCR detection results (from ocr_results.json)
            transcript: Whisper transcript (from transcript.json)
            teams_data: Teams data with alternates (from teams JSON)
        """
        self.ocr_results = ocr_results
        self.transcript = transcript
        self.teams_data = teams_data

        # Extract team names from teams_data
        self.team_names = [team.get("full") for team in teams_data if team.get("full")]

        # Build team alternates index for short name lookups
        self._build_alternates_index()

    def _build_alternates_index(self) -> None:
        """Build index of team alternates from teams data."""
        self.team_alternates: dict[str, list[str]] = {}

        for team in self.teams_data:
            full_name = team.get("full")
            alternates = team.get("alternates", [])

            if full_name:
                self.team_alternates[full_name] = alternates

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

    def detect_match_boundaries(self, running_order: RunningOrderResult) -> RunningOrderResult:
        """
        Detect match_start and match_end boundaries using transcript.

        For each match:
        1. match_start: Search forward from previous match's highlights_end
           to find first mention of BOTH teams (fuzzy matching)
        2. match_end: Next match's match_start (no gaps between matches)

        This avoids picking up "coming up later" mentions from earlier in the episode.

        Args:
            running_order: RunningOrderResult with highlights_start/end populated

        Returns:
            Updated RunningOrderResult with match_start/end populated
        """
        # Get transcript segments
        segments = self.transcript.get('segments', [])
        episode_duration = self.transcript.get('duration', 0)

        # Process matches to add boundaries
        updated_matches = []

        for i, match in enumerate(running_order.matches):
            # Get search window: from previous match's end to this match's highlights
            if i == 0:
                search_start = 0  # Episode start
            else:
                search_start = running_order.matches[i - 1].highlights_end  # Previous FT graphic

            # Detect match_start (intro beginning)
            match_start = self._detect_match_start(
                teams=match.teams,
                search_start=search_start,
                highlights_start=match.highlights_start,
                segments=segments,
                is_first_match=(i == 0)
            )

            # Create updated match with match_start
            updated_match = match.model_copy(update={'match_start': match_start})
            updated_matches.append(updated_match)

        # Second pass: Set match_end = next match's match_start
        for i, match in enumerate(updated_matches):
            if i < len(updated_matches) - 1:
                # match_end = next match's match_start (no gaps)
                match_end = updated_matches[i + 1].match_start
            else:
                # Last match: match_end = episode duration
                match_end = episode_duration

            # Update match with match_end
            updated_matches[i] = match.model_copy(update={'match_end': match_end})

        # Return updated result
        return running_order.model_copy(update={'matches': updated_matches})

    def _detect_match_start(
        self,
        teams: tuple[str, str],
        search_start: float,
        highlights_start: float,
        segments: list[dict],
        is_first_match: bool
    ) -> float:
        """
        Detect match_start by searching backward from highlights_start for team mentions.

        Searches backward from this match's highlights_start to find where BOTH teams
        are mentioned within 10 seconds of each other. This finds the actual studio intro
        immediately before highlights, avoiding "coming up later" mentions from earlier
        in the episode or from previous match's post-match analysis.

        Args:
            teams: Team pair (normalized/sorted)
            search_start: Start of search window (previous match's highlights_end or 0)
            highlights_start: First scoreboard timestamp (end of search window)
            segments: Transcript segments
            is_first_match: Whether this is the first match in the episode (unused - same algorithm for all)

        Returns:
            match_start timestamp (seconds)
        """
        # Find segments in the search window (between previous match and this one)
        relevant_segments = [
            s for s in segments
            if search_start <= s.get('start', 0) < highlights_start
        ]

        # Search backward from highlights_start to find where BOTH teams mentioned
        team1_mention = None
        team2_mention = None

        for segment in reversed(relevant_segments):
            text = segment.get('text', '').lower()
            timestamp = segment.get('start', 0)

            # Check if either team mentioned in this segment
            if self._fuzzy_team_match(text, teams[0]):
                team1_mention = timestamp
            if self._fuzzy_team_match(text, teams[1]):
                team2_mention = timestamp

            # If both teams found and within 10s of each other, this is the intro
            if team1_mention is not None and team2_mention is not None:
                time_gap = abs(team1_mention - team2_mention)
                if time_gap <= 10.0:
                    # Return the earlier mention (start of intro)
                    return min(team1_mention, team2_mention)

        # Fallback: No valid team mentions found, assume 60s before highlights
        return max(search_start, highlights_start - 60.0)

    def _fuzzy_team_match(self, text: str, team_name: str, threshold: float = 0.80) -> bool:
        """
        Check if team name appears in text using fuzzy matching.

        Args:
            text: Transcript text (lowercased)
            team_name: Team name to search for
            threshold: Fuzzy match threshold (default 0.80)

        Returns:
            True if team name found in text
        """
        # Normalize team name for matching
        team_lower = team_name.lower()

        # Direct substring match
        if team_lower in text:
            return True

        # Fuzzy match against words in text
        words = text.split()
        for word in words:
            # Try fuzzy matching
            score = fuzz.partial_ratio(team_lower, word) / 100.0
            if score >= threshold:
                return True

        # Handle common variations using team alternates from JSON
        # e.g., "Man United" for "Manchester United", "Villa" for "Aston Villa"
        alternates = self.team_alternates.get(team_name, [])
        for alternate in alternates:
            if alternate.lower() in text:
                return True

        return False

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
