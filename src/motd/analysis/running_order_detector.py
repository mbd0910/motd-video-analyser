"""
2-strategy running order detection with cross-validation.

Detects match running order using 2 independent strategies:
1. Scoreboard appearance order (most abundant detections)
2. FT graphic appearance order (most reliable anchor points)

Cross-validates both strategies for consensus and confidence scoring.

Includes transcript-based boundary detection for match_start/match_end.
"""

from collections import defaultdict
from typing import Any, TypedDict, Optional
from rapidfuzz import fuzz
from pathlib import Path
import json

from motd.pipeline.models import MatchBoundary, RunningOrderResult
from motd.analysis.venue_matcher import VenueMatcher


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

    # Venue strategy constants
    MAX_VENUE_LOOKBACK_SECONDS = 20.0  # Maximum time before venue mention to search for team mentions

    # Fuzzy matching constants
    MIN_WORD_LENGTH_FOR_FUZZY_MATCH = 4  # Prevent single-letter false positives (e.g., "a" matching "Aston")
    FUZZY_MATCH_THRESHOLD = 0.80  # Minimum confidence for fuzzy team name matching

    # Transition phrases to skip when searching for team mentions
    TRANSITION_PHRASES = {'ok.', 'thank you.', 'thank you very much.'}

    # Clustering strategy constants
    CLUSTERING_WINDOW_SECONDS = 20.0  # Both teams must be mentioned within this window
    CLUSTERING_MIN_DENSITY = 0.1      # Minimum mentions per second to qualify as cluster
    CLUSTERING_MIN_SIZE = 3            # Minimum co-mentions to qualify as cluster

    def __init__(
        self,
        ocr_results: list[dict[str, Any]],
        transcript: dict[str, Any],
        teams_data: list[TeamData],
        fixtures: list[dict[str, Any]],
        venue_matcher: VenueMatcher,
    ):
        """
        Initialize detector with processed data and dependencies.

        Args:
            ocr_results: OCR detection results (from ocr_results.json)
            transcript: Whisper transcript (from transcript.json)
            teams_data: Teams data with alternates (from teams JSON)
            fixtures: List of fixtures (from fixtures JSON) - injected dependency
            venue_matcher: Venue matcher instance - injected dependency
        """
        self.ocr_results = ocr_results
        self.transcript = transcript
        self.teams_data = teams_data
        self.fixtures = fixtures
        self.venue_matcher = venue_matcher

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

    def detect_match_boundaries(
        self,
        running_order: RunningOrderResult,
        include_clustering_diagnostics: bool = False
    ) -> RunningOrderResult:
        """
        Detect match_start and match_end using 3 independent strategies.

        Strategy 1: Team Mention Detection (both teams within 10s) - fallback
        Strategy 2: Venue Detection (venue mentioned in transcript) - PRIMARY
        Strategy 3: Clustering (temporal density of team co-mentions) - OBSERVATION

        All three results are recorded for analysis/comparison.
        match_start uses venue (preferred) or team mention (fallback).
        Clustering stored for side-by-side comparison only.

        Args:
            running_order: RunningOrderResult with highlights_start/end populated
            include_clustering_diagnostics: If True, include detailed diagnostic data in clustering results

        Returns:
            Updated RunningOrderResult with boundaries and all three strategy results
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

            # Run BOTH strategies
            # Strategy 1: Team Mention (existing)
            team_mention_timestamp = self._detect_match_start(
                teams=match.teams,
                search_start=search_start,
                highlights_start=match.highlights_start,
                segments=segments,
                is_first_match=(i == 0)
            )

            # Build team mention result
            team_mention_result = {
                'timestamp': team_mention_timestamp,
                'strategy': 'team_mention'
            } if team_mention_timestamp else None

            # Strategy 2: Venue Detection
            venue_result = self._detect_match_start_venue(
                teams=match.teams,
                search_start=search_start,
                highlights_start=match.highlights_start,
                segments=segments
            )

            # Strategy 3: Clustering (OBSERVATION ONLY)
            clustering_result = self._detect_match_start_clustering(
                teams=match.teams,
                search_start=search_start,
                highlights_start=match.highlights_start,
                segments=segments,
                include_diagnostics=include_clustering_diagnostics
            )

            # Choose best strategy result:
            # - Prefer venue (most accurate, ±5s)
            # - Fallback to team mention if venue not found
            # - Clustering stored for observation/comparison only
            if venue_result and venue_result.get('timestamp'):
                match_start = venue_result['timestamp']
            else:
                match_start = team_mention_timestamp

            # Create updated match with ALL THREE strategy results
            updated_match = match.model_copy(update={
                'match_start': match_start,
                'team_mention_result': team_mention_result,
                'venue_result': venue_result,
                'clustering_result': clustering_result  # NEW: Store for observation
            })
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

        # Find ALL team mentions in the search window
        team1_mentions = []
        team2_mentions = []

        for segment in relevant_segments:
            text = segment.get('text', '').lower()
            timestamp = segment.get('start', 0)

            if self._fuzzy_team_match(text, teams[0]):
                team1_mentions.append(timestamp)
            if self._fuzzy_team_match(text, teams[1]):
                team2_mentions.append(timestamp)

        # Find all valid pairs (both teams mentioned within 10s)
        valid_pairs = []
        for t1 in team1_mentions:
            for t2 in team2_mentions:
                time_gap = abs(t1 - t2)
                if time_gap <= 10.0:
                    intro_start = min(t1, t2)
                    valid_pairs.append({
                        'intro_start': intro_start,
                        'team1_time': t1,
                        'team2_time': t2,
                        'gap': time_gap,
                        'distance_from_highlights': highlights_start - intro_start
                    })

        if valid_pairs:
            # Choose the EARLIEST pair (furthest from highlights_start)
            # This finds the actual intro, not commentary right before highlights
            # The search window (previous match's end to highlights start) prevents going too far back
            best_pair = max(valid_pairs, key=lambda p: p['distance_from_highlights'])
            return best_pair['intro_start']

        # Fallback: No valid team mentions found, assume 60s before highlights
        return max(search_start, highlights_start - 60.0)

    def _extract_sentences_from_segments(
        self, segments: list[dict]
    ) -> list[dict[str, Any]]:
        """
        Extract sentences from transcript segments by combining segments
        until we hit one ending with sentence-ending punctuation.

        Args:
            segments: List of transcript segments (ordered by timestamp)

        Returns:
            List of sentences with start timestamp and text
            Each sentence dict contains:
            - 'start': timestamp of first segment in sentence
            - 'text': complete sentence text
        """
        if not segments:
            return []

        sentences = []
        current_parts = []
        current_start = None

        for segment in segments:
            text = segment.get('text', '').strip()
            if not text:
                continue

            # Start new sentence if needed
            if current_start is None:
                current_start = segment.get('start', 0)

            current_parts.append(text)

            # Check if this segment ends with sentence-ending punctuation
            if text.endswith('.') or text.endswith('!') or text.endswith('?'):
                # Complete sentence
                sentence_text = ' '.join(current_parts)
                sentences.append({'start': current_start, 'text': sentence_text})
                # Reset
                current_parts = []
                current_start = None

        # Handle incomplete sentence at end
        if current_parts:
            sentence_text = ' '.join(current_parts)
            sentences.append({'start': current_start, 'text': sentence_text})

        return sentences

    def _detect_match_start_venue(
        self,
        teams: tuple[str, str],
        search_start: float,
        highlights_start: float,
        segments: list[dict],
    ) -> Optional[dict[str, Any]]:
        """
        Strategy 2: Detect match_start via venue mention in transcript.

        Searches backward from highlights_start for venue mentions and fuzzy matches
        against the expected venue for this match.

        Args:
            teams: Team pair (normalized/sorted)
            search_start: Start of search window
            highlights_start: First scoreboard timestamp
            segments: Transcript segments

        Returns:
            Dict with timestamp and venue details, or None if not found
        """
        # Find fixture for these teams to get expected venue
        fixture = self._find_fixture_for_teams(teams)
        if not fixture or not fixture.get('venue'):
            return None

        expected_venue = fixture['venue']

        # Search backward through segments in search window
        relevant_segments = [
            s for s in segments
            if search_start <= s.get('start', 0) < highlights_start
        ]

        venue_mentions = []
        for segment in relevant_segments:
            text = segment.get('text', '')
            match = self.venue_matcher.match_venue(text)

            # Check if matched venue is the expected one for this match
            if match and match.venue == expected_venue:
                venue_mentions.append({
                    'timestamp': segment.get('start', 0),
                    'confidence': match.confidence,
                    'venue': match.venue,
                    'matched_text': match.matched_text,
                    'source': match.source
                })

        if venue_mentions:
            # For each venue mention, search backward through SENTENCES for team mentions
            for venue_mention in sorted(venue_mentions, key=lambda m: m['timestamp']):
                venue_timestamp = venue_mention['timestamp']

                # Get segments before and including venue mention (8-10 segments for safety)
                intro_segments = [
                    s for s in relevant_segments
                    if s.get('start', 0) <= venue_timestamp
                ]
                search_window = intro_segments[-10:] if len(intro_segments) >= 10 else intro_segments

                # Extract sentences from these segments
                sentences = self._extract_sentences_from_segments(search_window)

                # Search backward through sentences to find ALL sentences containing team names
                # within reasonable proximity of the venue mention
                # Then return the EARLIEST one (minimum timestamp)
                team_sentences = []

                for sentence in reversed(sentences):
                    text = sentence['text'].lower()
                    sentence_time = sentence['start']

                    # Only consider sentences within lookback window before venue mention
                    if venue_timestamp - sentence_time > self.MAX_VENUE_LOOKBACK_SECONDS:
                        continue

                    # Skip pure transition sentences
                    if text.strip().lower() in self.TRANSITION_PHRASES:
                        continue

                    # Check if sentence contains at least one team name
                    has_team = (
                        self._fuzzy_team_match(text, teams[0]) or
                        self._fuzzy_team_match(text, teams[1])
                    )

                    if has_team:
                        team_sentences.append(sentence)

                # Return the earliest sentence containing a team name
                if team_sentences:
                    earliest = min(team_sentences, key=lambda s: s['start'])
                    return {
                        'timestamp': earliest['start'],
                        'venue': venue_mention['venue'],
                        'confidence': venue_mention['confidence'],
                        'matched_text': venue_mention['matched_text'],
                        'source': venue_mention['source']
                    }

        # No valid venue mention found (either no venue or no team validation)
        return None

    def _find_fixture_for_teams(self, teams: tuple[str, str]) -> Optional[dict]:
        """
        Find fixture that matches the given team pair.

        Args:
            teams: Team pair (order doesn't matter)

        Returns:
            Fixture dict or None if not found
        """
        for fixture in self.fixtures:
            home = fixture.get('home_team', '')
            away = fixture.get('away_team', '')

            # Check if teams match (order doesn't matter)
            if set([home, away]) == set(teams):
                return fixture

        return None

    def _fuzzy_team_match(self, text: str, team_name: str) -> bool:
        """
        Check if team name appears in text using fuzzy matching.

        Uses class constant FUZZY_MATCH_THRESHOLD (0.80) for consistency.

        Args:
            text: Transcript text (lowercased)
            team_name: Team name to search for

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
            # Skip very short words to avoid false positives (e.g., "a" matching "Aston")
            if len(word) < self.MIN_WORD_LENGTH_FOR_FUZZY_MATCH:
                continue

            # Try fuzzy matching
            score = fuzz.partial_ratio(team_lower, word) / 100.0
            if score >= self.FUZZY_MATCH_THRESHOLD:
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

    # ========================================================================
    # Clustering Strategy Methods (Phase 2b-1a)
    # ========================================================================

    def _find_team_mentions(self, segments: list[dict], team_name: str) -> list[float]:
        """
        Extract all timestamps where a team is mentioned in transcript.

        Uses existing fuzzy matching logic to identify team mentions across
        segments. Returns chronologically ordered list of mention timestamps.

        Args:
            segments: Transcript segments (from transcript.json)
            team_name: Full team name to search for

        Returns:
            List of timestamps (floats) where team is mentioned, in chronological order
        """
        mentions = []

        for segment in segments:
            text = segment.get('text', '')
            timestamp = segment.get('start', 0)

            if self._fuzzy_team_match(text, team_name):
                mentions.append(timestamp)

        return mentions

    def _find_co_mention_windows(
        self,
        team1_mentions: list[float],
        team2_mentions: list[float],
        window_size: float = None
    ) -> list[dict[str, Any]]:
        """
        Find temporal windows where both teams are co-mentioned within proximity.

        Sliding window approach: For each mention of team1, count how many times
        both teams appear in the next `window_size` seconds.

        Args:
            team1_mentions: Timestamps where team1 mentioned
            team2_mentions: Timestamps where team2 mentioned
            window_size: Maximum time between mentions (default: CLUSTERING_WINDOW_SECONDS)

        Returns:
            List of windows, each with:
            - 'start': Earliest mention in window
            - 'mentions': Total co-mentions in window
            - 'density': Mentions per second
            - 'team1_count': Mentions of team1
            - 'team2_count': Mentions of team2
        """
        if window_size is None:
            window_size = self.CLUSTERING_WINDOW_SECONDS

        windows = []
        all_mentions = sorted(
            [(ts, 1) for ts in team1_mentions] + [(ts, 2) for ts in team2_mentions]
        )

        # Sliding window approach
        for i, (start_ts, _) in enumerate(all_mentions):
            window_end = start_ts + window_size

            # Count mentions within window
            team1_count = 0
            team2_count = 0

            for ts, team_id in all_mentions[i:]:
                if ts > window_end:
                    break

                if team_id == 1:
                    team1_count += 1
                else:
                    team2_count += 1

            # Only create window if both teams mentioned
            if team1_count > 0 and team2_count > 0:
                total_mentions = team1_count + team2_count
                density = total_mentions / window_size

                windows.append({
                    'start': start_ts,
                    'mentions': total_mentions,
                    'density': density,
                    'team1_count': team1_count,
                    'team2_count': team2_count
                })

        return windows

    def _identify_densest_cluster(
        self,
        windows: list[dict[str, Any]],
        search_start: float,
        highlights_start: float,
        min_density: float = None
    ) -> Optional[dict[str, Any]]:
        """
        Identify the densest cluster of co-mentions before highlights_start.

        Finds the temporal window with highest mention density (mentions/second)
        within the search window, then returns the EARLIEST mention in that cluster
        (not the center or latest).

        Args:
            windows: List of co-mention windows from _find_co_mention_windows()
            search_start: Start of search window (previous match end or 0)
            highlights_start: First scoreboard timestamp (end of search window)
            min_density: Minimum density threshold (default: CLUSTERING_MIN_DENSITY)

        Returns:
            Cluster metadata dict with:
            - 'timestamp': Earliest mention in cluster (match_start candidate)
            - 'cluster_size': Number of co-mentions
            - 'cluster_density': Mentions per second
            Or None if no qualifying cluster found
        """
        if min_density is None:
            min_density = self.CLUSTERING_MIN_DENSITY

        # Filter to search window
        valid_windows = [
            w for w in windows
            if search_start <= w['start'] < highlights_start
            and w['density'] >= min_density
            and w['mentions'] >= self.CLUSTERING_MIN_SIZE
        ]

        if not valid_windows:
            return None

        # Find densest window (highest density)
        densest = max(valid_windows, key=lambda w: w['density'])

        return {
            'timestamp': densest['start'],  # Earliest mention in cluster
            'cluster_size': densest['mentions'],
            'cluster_density': densest['density']
        }

    def _detect_match_start_clustering(
        self,
        teams: tuple[str, str],
        search_start: float,
        highlights_start: float,
        segments: list[dict],
        include_diagnostics: bool = False
    ) -> Optional[dict[str, Any]]:
        """
        Strategy 3: Detect match_start via temporal density clustering.

        Finds dense clusters where both teams are co-mentioned in close temporal
        proximity (within CLUSTERING_WINDOW_SECONDS). Returns the earliest mention
        in the densest cluster as the match_start candidate.

        This provides independent validation of venue strategy using statistical
        density rather than linguistic patterns.

        Args:
            teams: Team pair (normalized/sorted)
            search_start: Start of search window (previous match end or 0)
            highlights_start: First scoreboard timestamp (end of search window)
            segments: Transcript segments
            include_diagnostics: If True, include detailed diagnostic data

        Returns:
            Dict with:
            - 'timestamp': earliest mention in densest cluster
            - 'cluster_size': number of co-mentions in cluster
            - 'cluster_density': mentions per second
            - 'confidence': 0.0-1.0 based on cluster density
            - 'window_seconds': window size used
            - 'diagnostics': (if include_diagnostics=True) detailed analysis
            Or None if no significant cluster found
        """
        team1, team2 = teams

        # Extract all team mentions
        team1_mentions = self._find_team_mentions(segments, team1)
        team2_mentions = self._find_team_mentions(segments, team2)

        # Build diagnostics structure if requested
        diagnostics = None
        if include_diagnostics:
            diagnostics = {
                'team1_mentions': team1_mentions,
                'team2_mentions': team2_mentions,
                'team1': team1,
                'team2': team2,
                'search_window': {
                    'start': search_start,
                    'end': highlights_start,
                    'duration': highlights_start - search_start
                }
            }

        if not team1_mentions or not team2_mentions:
            if include_diagnostics:
                diagnostics['failure_reason'] = 'no_mentions'
                diagnostics['failure_details'] = (
                    f"Team1 ({team1}): {len(team1_mentions)} mentions, "
                    f"Team2 ({team2}): {len(team2_mentions)} mentions"
                )
                return {'diagnostics': diagnostics}
            return None

        # Find co-mention windows
        windows = self._find_co_mention_windows(
            team1_mentions,
            team2_mentions,
            window_size=self.CLUSTERING_WINDOW_SECONDS
        )

        if include_diagnostics:
            diagnostics['all_windows'] = windows
            diagnostics['total_windows'] = len(windows)

        if not windows:
            if include_diagnostics:
                diagnostics['failure_reason'] = 'no_windows'
                diagnostics['failure_details'] = (
                    f"No windows found where both teams mentioned within {self.CLUSTERING_WINDOW_SECONDS}s"
                )
                return {'diagnostics': diagnostics}
            return None

        # Identify densest cluster
        cluster = self._identify_densest_cluster(
            windows,
            search_start=search_start,
            highlights_start=highlights_start,
            min_density=self.CLUSTERING_MIN_DENSITY
        )

        # Filter windows to valid ones (for diagnostics)
        if include_diagnostics:
            valid_windows = [
                w for w in windows
                if search_start <= w['start'] < highlights_start
                and w['density'] >= self.CLUSTERING_MIN_DENSITY
                and w['mentions'] >= self.CLUSTERING_MIN_SIZE
            ]
            diagnostics['valid_windows'] = valid_windows
            diagnostics['invalid_windows_count'] = len(windows) - len(valid_windows)

        if not cluster:
            if include_diagnostics:
                diagnostics['failure_reason'] = 'no_valid_cluster'
                diagnostics['failure_details'] = (
                    f"No windows passed thresholds: "
                    f"min_density={self.CLUSTERING_MIN_DENSITY}, "
                    f"min_size={self.CLUSTERING_MIN_SIZE}"
                )
                # Add rejection reasons for each window
                diagnostics['window_rejections'] = []
                for w in windows:
                    rejection = {'window': w, 'reasons': []}
                    if w['start'] < search_start or w['start'] >= highlights_start:
                        rejection['reasons'].append('outside_search_window')
                    if w['density'] < self.CLUSTERING_MIN_DENSITY:
                        rejection['reasons'].append(f'density_too_low ({w["density"]:.2f} < {self.CLUSTERING_MIN_DENSITY})')
                    if w['mentions'] < self.CLUSTERING_MIN_SIZE:
                        rejection['reasons'].append(f'cluster_too_small ({w["mentions"]} < {self.CLUSTERING_MIN_SIZE})')
                    if rejection['reasons']:
                        diagnostics['window_rejections'].append(rejection)

                return {'diagnostics': diagnostics}
            return None

        # Calculate confidence based on density
        density = cluster['cluster_density']
        if density >= 2.0:
            confidence = 0.95
        elif density >= 1.0:
            confidence = 0.90
        elif density >= 0.5:
            confidence = 0.80
        elif density >= 0.2:
            confidence = 0.70
        else:
            confidence = 0.60

        result = {
            'timestamp': cluster['timestamp'],
            'cluster_size': cluster['cluster_size'],
            'cluster_density': cluster['cluster_density'],
            'confidence': confidence,
            'window_seconds': self.CLUSTERING_WINDOW_SECONDS
        }

        # Add diagnostics if requested
        if include_diagnostics:
            diagnostics['selected_cluster'] = cluster
            diagnostics['selection_reason'] = 'highest_density'

            # Find alternative clusters (other valid windows)
            valid_windows_for_alternatives = [
                w for w in windows
                if search_start <= w['start'] < highlights_start
                and w['density'] >= self.CLUSTERING_MIN_DENSITY
                and w['mentions'] >= self.CLUSTERING_MIN_SIZE
                and w['start'] != cluster['timestamp']  # Exclude selected
            ]

            # Sort by density (descending) and take top 3
            alternative_clusters = sorted(
                valid_windows_for_alternatives,
                key=lambda w: w['density'],
                reverse=True
            )[:3]

            diagnostics['alternative_clusters'] = alternative_clusters
            result['diagnostics'] = diagnostics

        return result
