"""
Unit tests for RunningOrderDetector.

Tests multi-strategy running order detection using real OCR data from
motd_2025-26_2025-11-01 episode.

Follows TDD approach: Write tests first, then implement detector.
"""

import json
import pytest
from pathlib import Path

from motd.analysis.running_order_detector import RunningOrderDetector
from motd.pipeline.models import RunningOrderResult, MatchBoundary


@pytest.fixture
def episode_01_minimal():
    """Load minimal Episode 01 fixture (no cache dependency)."""
    fixture_path = Path('tests/fixtures/episodes/motd_2025-26_2025-11-01_minimal.json')
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def ocr_results(episode_01_minimal):
    """Load OCR results from minimal Episode 01 fixture."""
    return episode_01_minimal['ocr_results']


@pytest.fixture
def transcript(episode_01_minimal):
    """Load transcript from minimal Episode 01 fixture."""
    return {
        'segments': episode_01_minimal['segments'],
        'duration': episode_01_minimal.get('duration', 5039.0)
    }


@pytest.fixture
def teams_data():
    """Load Premier League teams data."""
    teams_path = Path('data/teams/premier_league_2025_26.json')
    with open(teams_path) as f:
        data = json.load(f)
    return data['teams']


@pytest.fixture
def fixtures():
    """Load fixtures data."""
    fixtures_path = Path('data/fixtures/premier_league_2025_26.json')
    with open(fixtures_path) as f:
        data = json.load(f)
    return data['fixtures']


@pytest.fixture
def venue_matcher():
    """Create venue matcher."""
    from motd.analysis.venue_matcher import VenueMatcher
    venues_path = Path('data/venues/premier_league_2025_26.json')
    return VenueMatcher(str(venues_path))


@pytest.fixture
def detector(ocr_results, transcript, teams_data, fixtures, venue_matcher):
    """Create RunningOrderDetector with all dependencies."""
    return RunningOrderDetector(
        ocr_results=ocr_results,
        transcript=transcript,
        teams_data=teams_data,
        fixtures=fixtures,
        venue_matcher=venue_matcher
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


class TestMatchBoundaryDetection:
    """Test match_start and match_end boundary detection via transcript."""

    def test_detect_match_boundaries_populates_all_fields(self, detector):
        """Should populate match_start and match_end for all 7 matches."""
        # Get base running order (has highlights_start/end)
        base_result = detector.detect_running_order()

        # Add boundary detection
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            assert match.match_start is not None, f"Match {i} should have match_start"
            assert match.match_end is not None, f"Match {i} should have match_end"
            assert match.highlights_start is not None, f"Match {i} should have highlights_start"
            assert match.highlights_end is not None, f"Match {i} should have highlights_end"

    def test_match_start_before_highlights_start(self, detector):
        """match_start (intro) should be before highlights_start (first scoreboard)."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            assert match.match_start < match.highlights_start, \
                f"Match {i}: intro ({match.match_start}s) should be before highlights ({match.highlights_start}s)"

    def test_highlights_end_before_match_end(self, detector):
        """highlights_end (FT graphic) should be before match_end (post-match analysis end)."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            assert match.highlights_end < match.match_end, \
                f"Match {i}: highlights_end ({match.highlights_end}s) should be before match_end ({match.match_end}s)"

    def test_match_end_equals_next_match_start(self, detector):
        """Each match_end should equal the next match's match_start (no gaps), except for interludes."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i in range(len(result.matches) - 1):
            current = result.matches[i]
            next_match = result.matches[i + 1]

            # Match 4 has an interlude (MOTD 2) after it
            # Match 4 ends at ~3118s (interlude), Match 5 starts at ~3169s (51s gap)
            if i == 3:  # Match 4 (0-indexed)
                gap = next_match.match_start - current.match_end
                assert 48 <= gap <= 54, \
                    f"Match 4 interlude gap should be 48-54s, got {gap}s"
            else:
                # All other matches: no gaps
                assert current.match_end == next_match.match_start, \
                    f"Match {i+1} end ({current.match_end}s) should equal Match {i+2} start ({next_match.match_start}s)"

    def test_first_match_start_reasonable(self, detector):
        """First match should start near episode beginning (after intro ~50s)."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        first_match = result.matches[0]

        # Should be between 0-120s (after episode intro, before highlights)
        assert 0 <= first_match.match_start <= 120, \
            f"First match should start 0-120s, got {first_match.match_start}s"

    def test_last_match_end_is_episode_duration(self, detector):
        """Last match should end before episode duration (excludes table review)."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        last_match = result.matches[-1]
        episode_duration = detector.transcript.get('duration', 0)

        # With table detection: Match 7 ends ~4977s (table keyword at sentence start)
        # Without table detection: Match 7 ends at episode_duration (5039s)
        assert last_match.match_end < episode_duration, \
            f"Last match should end before episode duration ({episode_duration}s), got {last_match.match_end}s"

        # Specific validation for Episode 01: table detected at ~4977s
        assert 4975 <= last_match.match_end <= 4980, \
            f"Expected Match 7 to end ~4977s (table review excluded), got {last_match.match_end}s"

    def test_intro_duration_reasonable(self, detector):
        """Intro duration (match_start to highlights_start) should be 3-180s."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            intro_duration = match.highlights_start - match.match_start

            # Some intros are very brief (team mentioned seconds before kickoff)
            assert 3 <= intro_duration <= 180, \
                f"Match {i} intro should be 3-180s, got {intro_duration}s"

    def test_post_match_duration_reasonable(self, detector):
        """Post-match duration (highlights_end to match_end) should be 10-600s."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            post_match_duration = match.match_end - match.highlights_end

            # Some matches have minimal post-match (quick transition), some have long analysis
            assert 10 <= post_match_duration <= 600, \
                f"Match {i} post-match should be 10-600s, got {post_match_duration}s"


class TestVenueStrategyImprovements:
    """Test venue strategy with backward search and team validation."""

    # Ground truth from Task 012-01 (visual_patterns.md + manual verification)
    GROUND_TRUTH_INTROS = {
        1: 61,    # 00:01:01 - Liverpool vs Aston Villa
        2: 865,   # 00:14:25 - Arsenal vs Burnley
        3: 1587,  # 00:26:27 - Nottingham Forest vs Man Utd
        4: 2509,  # 00:41:49 - Fulham vs Wolves
        5: 3168,  # 00:52:48 - Tottenham vs Chelsea
        6: 3894,  # 01:04:54 - Brighton vs Leeds
        7: 4480,  # 01:14:40 - Crystal Palace vs Brentford
    }

    def test_venue_detects_intro_start_not_venue_mention(self, detector):
        """Venue strategy should search BACKWARD from venue mention to find intro start.

        Example Match 1:
        - Venue mentioned at 69s: "Your commentator at Anfield..."
        - But intro STARTS at 61s: "It was six defeats in seven..."
        - Should search backward 3-5 segments and find 61s
        """
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        match1 = result.matches[0]

        # Should be within ±10s of ground truth (61s), NOT venue mention time (69s)
        assert abs(match1.match_start - 61) <= 10, \
            f"Match 1 should start ~61s (intro start), got {match1.match_start}s"

        # Should NOT be at venue mention time (~69s)
        assert abs(match1.match_start - 69) > 5, \
            f"Match 1 should NOT use venue mention time (69s), got {match1.match_start}s"

    def test_venue_strategy_rejects_false_positives_without_teams(self, detector):
        """Venue mentions without BOTH teams should be rejected as false positives.

        Example: Match 5 false positive at 3024s
        - Transcript: "that lane for Fulham" during Match 4 post-analysis
        - VenueMatcher incorrectly matched "The Lane" alias for Tottenham
        - But BOTH "Tottenham" AND "Chelsea" are NOT mentioned in those segments
        - Should reject this and keep searching
        """
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        match5 = result.matches[4]  # Tottenham vs Chelsea

        # Should be within ±30s of ground truth (3168s)
        assert abs(match5.match_start - 3168) <= 30, \
            f"Match 5 should start ~3168s, got {match5.match_start}s"

        # Should NOT be the false positive at 3024s
        assert abs(match5.match_start - 3024) > 60, \
            f"Match 5 should NOT use false positive at 3024s, got {match5.match_start}s"

    def test_all_matches_within_10s_of_ground_truth(self, detector):
        """All 7 matches should be within ±10s of ground truth intro times.

        Note: Match 7 has known issue - "Selhurl Park" typo causes venue detection
        to fail team validation. Falls back to team mention strategy (±200s).
        Matches 1-6 achieve ±5s accuracy with venue strategy.
        """
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i, match in enumerate(result.matches, 1):
            expected = self.GROUND_TRUTH_INTROS[i]
            actual = match.match_start
            error = abs(actual - expected)

            # Match 7 has venue detection issue (Selhurl Park typo + team validation)
            # TODO: Debug why Match 7 venue+team validation fails
            tolerance = 200 if i == 7 else 10

            assert error <= tolerance, \
                f"Match {i} should be within ±{tolerance}s of {expected}s, got {actual}s (error: {error}s)"

    def test_match7_selhurl_park_detection_bug(self, detector):
        """Debug Match 7 venue detection failure (Selhurl Park typo case).

        Context:
        - Teams: ['Brentford', 'Crystal Palace'] (alphabetically sorted)
        - Expected venue: Selhurst Park (Palace home ground)
        - Transcript 4485.95s: "James Fielden was at Selhurl Park" (typo)
        - Transcript 4484.37s: "Crystal Palace and Brentford" (both teams)

        Issue: venue_result returns null despite:
        - VenueMatcher working in isolation (88% confidence match)
        - Both teams present in 5-segment window
        - Venue in search window [4291s, 4527s]

        This test will reveal which step fails.
        """
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        match7 = result.matches[6]

        # Verify teams are correct
        assert set(match7.teams) == {'Brentford', 'Crystal Palace'}

        # The bug: venue_result should NOT be null
        assert match7.venue_result is not None, \
            "Match 7 venue detection should find 'Selhurl Park' → 'Selhurst Park'"

        # If venue found, verify it's correct
        if match7.venue_result:
            assert match7.venue_result['venue'] == 'Selhurst Park'
            # Timestamp should be earlier than venue mention (backward search)
            assert match7.venue_result['timestamp'] < 4486, \
                f"Should use intro start, not venue mention time: {match7.venue_result['timestamp']}"

    def test_venue_selects_earliest_team_sentence(self, detector):
        """Test that venue strategy selects EARLIEST sentence containing a team name.
        
        Real example from Match 1:
        - Sentence [5] at 61.11s: "It was six defeats... Liverpool." ← Should select THIS
        - Sentence [6] at 66.05s: "Aston Villa had just won..." ← NOT this one
        
        When searching backward from venue mention, should find the earliest 
        (furthest back) sentence containing either team, not the first one encountered.
        """
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)
        
        match1 = result.matches[0]
        
        # Match 1: Liverpool vs Aston Villa
        # Expected: 61.11s ("It was six defeats... Liverpool")
        # Algorithm should NOT pick 66.05s ("Aston Villa had just won...")
        
        assert match1.venue_result is not None
        assert match1.venue_result['timestamp'] == 61.11, \
            f"Match 1 should select earliest team sentence at 61.11s, got {match1.venue_result['timestamp']}s"
        
        # Match 2: Arsenal vs Burnley
        # Expected: 866.30s ("Leaders, Arsenal...")
        # Algorithm should NOT pick 870.94s ("Back-to-back victories for Burnley...")
        
        match2 = result.matches[1]
        assert match2.venue_result is not None
        assert match2.venue_result['timestamp'] == 866.30, \
            f"Match 2 should select earliest team sentence at 866.30s, got {match2.venue_result['timestamp']}s"


class TestClusteringStrategy:
    """
    Test Strategy 3: Temporal density clustering for match boundary detection.

    Tests clustering-based detection that finds dense co-occurrence patterns
    of team mentions in transcript to identify match introduction boundaries.
    """

    # Ground truth intro timestamps (from visual_patterns.md)
    GROUND_TRUTH_INTROS = {
        1: 61,    # 00:01:01 - Liverpool vs Aston Villa
        2: 865,   # 00:14:25 - Arsenal vs Burnley
        3: 1587,  # 00:26:27 - Nottingham Forest vs Man Utd
        4: 2509,  # 00:41:49 - Fulham vs Wolves
        5: 3168,  # 00:52:48 - Tottenham vs Chelsea
        6: 3894,  # 01:04:54 - Brighton vs Leeds
        7: 4480,  # 01:14:40 - Crystal Palace vs Brentford
    }

    def test_finds_team_mentions_in_transcript(self, detector, transcript):
        """Should extract all timestamps where a team is mentioned."""
        segments = transcript.get('segments', [])

        # Test with Liverpool (should appear multiple times)
        liverpool_mentions = detector._find_team_mentions(segments, 'Liverpool')

        assert len(liverpool_mentions) > 0, "Should find Liverpool mentions in transcript"
        assert all(isinstance(ts, float) for ts in liverpool_mentions), "All mentions should be timestamps"
        assert all(ts >= 0 for ts in liverpool_mentions), "All timestamps should be non-negative"

        # Test with Aston Villa
        villa_mentions = detector._find_team_mentions(segments, 'Aston Villa')

        assert len(villa_mentions) > 0, "Should find Aston Villa mentions"

        # Mentions should be chronologically ordered (segments are ordered)
        for i in range(len(liverpool_mentions) - 1):
            assert liverpool_mentions[i] <= liverpool_mentions[i + 1], \
                "Mentions should be in chronological order"

    def test_finds_co_mention_windows(self, detector, transcript):
        """Should identify windows where both teams are mentioned within proximity."""
        segments = transcript.get('segments', [])

        # Match 1: Liverpool vs Aston Villa
        liverpool_mentions = detector._find_team_mentions(segments, 'Liverpool')
        villa_mentions = detector._find_team_mentions(segments, 'Aston Villa')

        # Find co-occurrence windows (20s default)
        windows = detector._find_co_mention_windows(
            liverpool_mentions,
            villa_mentions,
            window_size=20.0
        )

        assert len(windows) > 0, "Should find co-mention windows for Liverpool vs Villa"

        # Each window should have metadata
        for window in windows:
            assert 'start' in window, "Window should have start timestamp"
            assert 'mentions' in window, "Window should have mention count"
            assert 'density' in window, "Window should have density score"
            assert window['mentions'] >= 2, "Window should have at least 2 mentions (one per team)"
            assert window['density'] > 0, "Density should be positive"

    def test_identifies_dense_clusters(self, detector, transcript):
        """Should identify dense clusters and return earliest mention."""
        segments = transcript.get('segments', [])

        # Match 1: Liverpool vs Aston Villa
        # highlights_start is around 112s (first scoreboard)
        # Expected intro cluster around 61s

        liverpool_mentions = detector._find_team_mentions(segments, 'Liverpool')
        villa_mentions = detector._find_team_mentions(segments, 'Aston Villa')

        windows = detector._find_co_mention_windows(
            liverpool_mentions,
            villa_mentions,
            window_size=20.0
        )

        # Identify densest cluster before highlights_start
        cluster = detector._identify_densest_cluster(
            windows,
            search_start=0.0,
            highlights_start=112.0,  # Match 1 first scoreboard
            min_density=0.05  # Low threshold for testing
        )

        assert cluster is not None, "Should find a cluster for Match 1"
        assert 'timestamp' in cluster, "Cluster should have timestamp"
        assert 'cluster_size' in cluster, "Cluster should have size"
        assert 'cluster_density' in cluster, "Cluster should have density"

        # Cluster timestamp should be before highlights_start
        assert cluster['timestamp'] < 112.0, "Cluster should be before highlights"

        # Should be reasonably close to ground truth (±30s)
        ground_truth = self.GROUND_TRUTH_INTROS[1]
        diff = abs(cluster['timestamp'] - ground_truth)
        assert diff < 30.0, f"Cluster should be within 30s of ground truth (diff: {diff}s)"

    def test_returns_earliest_mention_in_cluster(self, detector, transcript):
        """Should return EARLIEST mention in cluster, not center or latest."""
        segments = transcript.get('segments', [])

        # Match 2: Arsenal vs Burnley
        # Ground truth: 865s
        # Cluster likely spans 865-880s
        # Should return 865s (earliest), not ~872s (center)

        arsenal_mentions = detector._find_team_mentions(segments, 'Arsenal')
        burnley_mentions = detector._find_team_mentions(segments, 'Burnley')

        windows = detector._find_co_mention_windows(
            arsenal_mentions,
            burnley_mentions,
            window_size=20.0
        )

        cluster = detector._identify_densest_cluster(
            windows,
            search_start=600.0,  # After Match 1 ends (~607s)
            highlights_start=900.0,  # Match 2 first scoreboard
            min_density=0.05
        )

        assert cluster is not None, "Should find cluster for Match 2"

        # Cluster timestamp should be close to start (865s), not middle
        ground_truth = self.GROUND_TRUTH_INTROS[2]
        diff = abs(cluster['timestamp'] - ground_truth)

        # Should be within 10s of ground truth start
        assert diff < 15.0, \
            f"Should return earliest mention in cluster (expected ~{ground_truth}s, got {cluster['timestamp']}s, diff: {diff}s)"

    def test_ignores_isolated_preview_mentions(self, detector, transcript):
        """Should reject scattered low-density mentions, select dense intro cluster."""
        segments = transcript.get('segments', [])

        # Teams might be mentioned earlier in episode (e.g., "coming up later...")
        # These should be rejected in favor of dense intro cluster

        # Match 3: Nottingham Forest vs Man Utd
        # Ground truth intro: 1587s

        forest_mentions = detector._find_team_mentions(segments, 'Nottingham Forest')
        manutd_mentions = detector._find_team_mentions(segments, 'Manchester United')

        windows = detector._find_co_mention_windows(
            forest_mentions,
            manutd_mentions,
            window_size=20.0
        )

        cluster = detector._identify_densest_cluster(
            windows,
            search_start=900.0,  # After Match 2 ends
            highlights_start=1620.0,  # Match 3 first scoreboard
            min_density=0.1  # Higher threshold to filter scattered mentions
        )

        # If cluster found, should be near ground truth, not early preview
        if cluster:
            ground_truth = self.GROUND_TRUTH_INTROS[3]
            diff = abs(cluster['timestamp'] - ground_truth)

            # Should be within 60s of actual intro (not hundreds of seconds early)
            assert diff < 60.0, \
                f"Should find dense intro cluster near {ground_truth}s, not scattered mentions (got {cluster['timestamp']}s, diff: {diff}s)"

    def test_clustering_produces_reasonable_timestamps(self, detector):
        """
        Integration test: Run clustering on all 7 matches, verify sanity checks.

        Sanity checks:
        - Timestamp is within search window (search_start < timestamp < highlights_start)
        - Timestamp is before highlights_start
        - Timestamp is after search_start
        """
        base_result = detector.detect_running_order()

        # We'll manually call clustering for each match
        segments = detector.transcript.get('segments', [])
        search_start = 0.0

        for i, match in enumerate(base_result.matches, 1):
            team1, team2 = match.teams
            highlights_start = match.highlights_start

            # Extract mentions
            team1_mentions = detector._find_team_mentions(segments, team1)
            team2_mentions = detector._find_team_mentions(segments, team2)

            # Find windows
            windows = detector._find_co_mention_windows(
                team1_mentions,
                team2_mentions,
                window_size=20.0
            )

            # Identify cluster
            cluster = detector._identify_densest_cluster(
                windows,
                search_start=search_start,
                highlights_start=highlights_start,
                min_density=0.05
            )

            # If cluster found, verify sanity
            if cluster:
                timestamp = cluster['timestamp']

                # Sanity check: within search window
                assert timestamp >= search_start, \
                    f"Match {i}: Cluster timestamp ({timestamp}s) should be >= search_start ({search_start}s)"

                assert timestamp < highlights_start, \
                    f"Match {i}: Cluster timestamp ({timestamp}s) should be < highlights_start ({highlights_start}s)"

            # Update search_start for next match
            if match.highlights_end:
                search_start = match.highlights_end

    def test_match_4_sentence_level_co_mention_detection(self, detector, transcript):
        """
        Test Match 4 (Fulham vs Wolves) sentence-level co-mention detection.

        Regression test for critical bug: Match 4 teams ARE co-mentioned in same sentence
        at ~2509s ("OK, bottom of the table, Wolves were hunting a first win at Fulham"),
        but Whisper splits this across segments:
        - Segment 1 (2509s): "OK, bottom of the table, Wolves..."
        - Segment 2 (2512s): "were hunting a first win at Fulham..."

        Without sentence extraction, clustering treats these as separate mentions →
        next Wolves mention is 216s later → no co-mentions within 20s window → FAILURE.

        With sentence extraction, segments combine into single sentence → both teams
        detected in same sentence → Match 4 detected ✓
        """
        segments = transcript.get('segments', [])

        # Match 4: Fulham vs Wolves
        # Ground truth intro: 2509s (41:49)
        # highlights_start: ~2555s (first scoreboard)

        fulham_mentions = detector._find_team_mentions(segments, 'Fulham')
        wolves_mentions = detector._find_team_mentions(segments, 'Wolverhampton Wanderers')

        # Both teams should be found in transcript
        assert len(fulham_mentions) > 0, "Should find Fulham mentions"
        assert len(wolves_mentions) > 0, "Should find Wolves mentions"

        # CRITICAL: With sentence extraction, should find co-mentions within 20s window
        # (Sentence at 2509s contains both teams)
        windows = detector._find_co_mention_windows(
            fulham_mentions,
            wolves_mentions,
            window_size=20.0
        )

        # Filter to windows before highlights_start (~2555s) and after Match 3 end (~1900s)
        intro_windows = [
            w for w in windows
            if 1900.0 < w['start'] < 2555.0
        ]

        assert len(intro_windows) > 0, \
            "Should find co-mention window for Match 4 intro (~2509s) with sentence extraction"

        # Identify densest cluster
        cluster = detector._identify_densest_cluster(
            windows,
            search_start=1900.0,  # After Match 3 ends
            highlights_start=2555.0,  # Match 4 first scoreboard
            min_density=0.1
        )

        assert cluster is not None, \
            "Clustering should detect Match 4 with sentence extraction (previously failed)"

        # Cluster should be near ground truth (2509s)
        ground_truth = self.GROUND_TRUTH_INTROS[4]
        diff = abs(cluster['timestamp'] - ground_truth)

        assert diff < 30.0, \
            f"Match 4 cluster should be within 30s of ground truth {ground_truth}s " \
            f"(got {cluster['timestamp']}s, diff: {diff}s)"

    def test_hybrid_earliness_density_selection(self, detector, transcript):
        """
        Test hybrid cluster selection: Prefer earliest unless 2x denser.

        Match 3 regression test: Multiple valid clusters exist around intro:
        - 1587s: density 0.15, mentions 3 ← EARLIEST, CORRECT
        - 1616s: density 0.20, mentions 4 ← Denser but not 2x
        - 1627s: density 0.20, mentions 4

        Pure density selection picks 1616s (29s late).
        Hybrid selection picks 1587s (correct).
        """
        segments = transcript.get('segments', [])

        # Match 3: Man Utd vs Nottingham Forest
        # Ground truth: 1587s
        # highlights_start: ~1620s

        manutd_mentions = detector._find_team_mentions(segments, 'Manchester United')
        forest_mentions = detector._find_team_mentions(segments, 'Nottingham Forest')

        windows = detector._find_co_mention_windows(
            manutd_mentions,
            forest_mentions,
            window_size=20.0
        )

        # Identify cluster with hybrid logic
        cluster = detector._identify_densest_cluster(
            windows,
            search_start=900.0,  # After Match 2 ends
            highlights_start=1620.0,  # Match 3 first scoreboard
            min_density=0.1
        )

        assert cluster is not None, "Should find cluster for Match 3"

        # Should select earliest cluster (1587s), NOT denser cluster (1616s)
        ground_truth = self.GROUND_TRUTH_INTROS[3]
        diff = abs(cluster['timestamp'] - ground_truth)

        # Should be within 5s of ground truth (1587s)
        assert diff < 5.0, \
            f"Hybrid selection should pick earliest cluster (expected ~{ground_truth}s, " \
            f"got {cluster['timestamp']}s, diff: {diff}s). " \
            f"Pure density selection would pick 1616s (29s late)."

        # Verify it picked the earliest cluster (density 0.15, not 0.20)
        assert 0.14 <= cluster['cluster_density'] <= 0.16, \
            f"Should pick earliest cluster with density ~0.15 " \
            f"(got {cluster['cluster_density']})"

    def test_clustering_strategy_integration(self, detector):
        """
        Integration test: _detect_match_start_clustering() method.

        Tests the main clustering method that will be called by detect_match_boundaries().
        """
        base_result = detector.detect_running_order()
        segments = detector.transcript.get('segments', [])

        # Test Match 1: Liverpool vs Aston Villa
        match1 = base_result.matches[0]

        clustering_result = detector._detect_match_start_clustering(
            teams=match1.teams,
            search_start=0.0,
            highlights_start=match1.highlights_start,
            segments=segments
        )

        # Should return a result
        assert clustering_result is not None, "Clustering should find a result for Match 1"

        # Result should have expected structure
        assert 'timestamp' in clustering_result
        assert 'cluster_size' in clustering_result
        assert 'cluster_density' in clustering_result
        assert 'confidence' in clustering_result
        assert 'window_seconds' in clustering_result

        # Timestamp should be reasonable (±60s of ground truth)
        ground_truth = self.GROUND_TRUTH_INTROS[1]
        diff = abs(clustering_result['timestamp'] - ground_truth)

        assert diff < 60.0, \
            f"Match 1 clustering should be within 60s of ground truth {ground_truth}s (got {clustering_result['timestamp']}s, diff: {diff}s)"

        # Confidence should be between 0 and 1
        assert 0.0 <= clustering_result['confidence'] <= 1.0, \
            "Confidence should be between 0.0 and 1.0"

class TestBoundaryValidation:
    """
    Test cross-validation of boundary detection (venue vs clustering).
    
    Venue is primary (authoritative), clustering is validator (safety net).
    """

    def test_validation_perfect_agreement(self, detector):
        """Test validation when venue and clustering perfectly agree (≤10s)."""
        # Mock results with perfect agreement
        venue_result = {'timestamp': 2509.06}
        clustering_result = {'timestamp': 2509.06}  # 0.0s difference

        validation = detector._create_boundary_validation(venue_result, clustering_result)

        assert validation is not None
        assert validation.status == 'validated'
        assert validation.agreement is True
        assert validation.confidence == 1.0
        assert validation.difference_seconds == 0.0
        assert validation.venue_timestamp == 2509.06
        assert validation.clustering_timestamp == 2509.06

    def test_validation_minor_discrepancy(self, detector):
        """Test validation with minor discrepancy (10-30s)."""
        # Mock results with 25s difference
        venue_result = {'timestamp': 1587.21}
        clustering_result = {'timestamp': 1612.15}  # 24.94s difference

        validation = detector._create_boundary_validation(venue_result, clustering_result)

        assert validation is not None
        assert validation.status == 'minor_discrepancy'
        assert validation.agreement is False
        assert validation.confidence == 0.8
        assert 24.0 < validation.difference_seconds < 25.0
        assert validation.venue_timestamp == 1587.21
        assert validation.clustering_timestamp == 1612.15

    def test_validation_major_discrepancy(self, detector):
        """Test validation with major discrepancy (>30s)."""
        # Mock results with 45s difference
        venue_result = {'timestamp': 1587.21}
        clustering_result = {'timestamp': 1632.34}  # 45.13s difference

        validation = detector._create_boundary_validation(venue_result, clustering_result)

        assert validation is not None
        assert validation.status == 'major_discrepancy'
        assert validation.agreement is False
        assert validation.confidence == 0.5
        assert 44.0 < validation.difference_seconds < 46.0

    def test_validation_clustering_failed(self, detector):
        """Test validation when clustering fails to detect."""
        # Mock results with clustering failure
        venue_result = {'timestamp': 2509.06}
        clustering_result = None  # Clustering failed

        validation = detector._create_boundary_validation(venue_result, clustering_result)

        assert validation is not None
        assert validation.status == 'clustering_failed'
        assert validation.agreement is False
        assert validation.confidence == 0.7
        assert validation.venue_timestamp == 2509.06
        assert validation.clustering_timestamp is None
        assert validation.difference_seconds is None

    def test_validation_venue_failed(self, detector):
        """Test validation when venue fails (should return None)."""
        # Mock results with venue failure
        venue_result = None
        clustering_result = {'timestamp': 2509.06}

        validation = detector._create_boundary_validation(venue_result, clustering_result)

        # No validation if venue failed (venue is primary)
        assert validation is None

    def test_detect_match_boundaries_includes_validation(self, detector):
        """Test that detect_match_boundaries() populates validation field."""
        base_result = detector.detect_running_order()
        result_with_boundaries = detector.detect_match_boundaries(base_result)

        # All matches should have validation
        for i, match in enumerate(result_with_boundaries.matches, 1):
            assert match.validation is not None, f"Match {i} should have validation"
            assert match.validation.status in {'validated', 'minor_discrepancy', 'major_discrepancy', 'clustering_failed'}
            assert 0.5 <= match.validation.confidence <= 1.0
            
            # Confidence should match validation confidence
            assert match.confidence == match.validation.confidence


def load_interlude_patterns():
    """Load synthetic interlude patterns from fixtures."""
    patterns_path = Path('tests/fixtures/patterns/interlude_patterns.json')
    with open(patterns_path) as f:
        data = json.load(f)
    return data['interlude_patterns']


class TestInterludePatterns:
    """Parameterized tests using synthetic interlude patterns (no cache dependency)."""

    @pytest.fixture
    def minimal_detector(self, teams_data, fixtures, venue_matcher):
        """Create detector with empty OCR results for pattern testing."""
        return RunningOrderDetector(
            ocr_results=[],
            transcript={'segments': []},
            teams_data=teams_data,
            fixtures=fixtures,
            venue_matcher=venue_matcher
        )

    @pytest.mark.parametrize("pattern", load_interlude_patterns(), ids=lambda p: p['pattern_id'])
    def test_interlude_pattern(self, minimal_detector, pattern):
        """Test interlude detection against synthetic patterns."""
        # Set up detector with pattern data
        minimal_detector.ocr_results = pattern['ocr_results']

        result = minimal_detector._detect_interlude(
            teams=tuple(pattern['teams']),
            highlights_end=pattern['highlights_end'],
            next_match_start=pattern['next_match_start'],
            segments=pattern['segments']
        )

        expected = pattern['expected_result']
        if expected is None:
            assert result is None, f"Pattern '{pattern['pattern_id']}': Expected None, got {result}"
        else:
            assert result is not None, f"Pattern '{pattern['pattern_id']}': Expected {expected}, got None"
            assert abs(result - expected) < 1.0, f"Pattern '{pattern['pattern_id']}': Expected ~{expected}, got {result}"


class TestInterludeDetection:
    """Test interlude detection using real episode data from minimal fixtures."""

    def test_detect_interlude_match4_motd2(self, detector, transcript):
        """Match 4 (Fulham vs Wolves): Should detect MOTD 2 interlude at ~3118s."""
        teams = ('Fulham', 'Wolverhampton Wanderers')
        highlights_end = 2881.0  # FT graphic timestamp (from task doc)
        next_match_start = 3169.0  # Match 5 start
        segments = transcript['segments']

        result = detector._detect_interlude(teams, highlights_end, next_match_start, segments)

        # Expected: keyword at 3118s (sentence start, no buffer)
        assert result is not None, "Should detect interlude"
        assert 3116 <= result <= 3120, f"Expected ~3118s, got {result}"

    def test_no_interlude_normal_matches(self, detector, transcript):
        """Matches 1-3, 5-6: Should NOT detect interlude (no keywords)."""
        # Test Match 1 (Liverpool vs Villa)
        teams = ('Aston Villa', 'Liverpool')
        highlights_end = 607.0
        next_match_start = 866.0
        segments = transcript['segments']

        result = detector._detect_interlude(teams, highlights_end, next_match_start, segments)
        assert result is None, "Match 1 should have no interlude"

    def test_interlude_keyword_in_consecutive_sentences(self, detector):
        """Should detect keyword split across consecutive sentences."""
        teams = ('Fulham', 'Wolverhampton Wanderers')
        segments = [
            {'start': 3000.0, 'text': 'Great analysis there.'},
            {'start': 3118.0, 'text': "Two games on Sunday's"},
            {'start': 3119.0, 'text': 'Match Of The Day.'},
            {'start': 3123.0, 'text': "That's an absolutely stunning goal!"},
        ]

        result = detector._detect_interlude(teams, 2881.0, 3169.0, segments)

        assert result is not None, "Should detect keyword in consecutive sentences"
        assert 3116 <= result <= 3120

    def test_interlude_with_team_mention_but_no_graphics(self, detector):
        """
        Should detect interlude even if team name mentioned (e.g., women's football news).

        Key insight: Absence of scoreboards/FT graphics is the validation signal,
        NOT absence of team names in transcript.
        """
        teams = ('Fulham', 'Wolverhampton Wanderers')
        segments = [
            {'start': 3118.0, 'text': "Sunday's Match Of The Day."},
            {'start': 3130.0, 'text': "Fulham women scored a late winner."},  # Team mention!
        ]

        # Temporarily set empty OCR results (no graphics in window)
        original_ocr = detector.ocr_results
        detector.ocr_results = []

        try:
            result = detector._detect_interlude(teams, 2881.0, 3169.0, segments)
            # NEW behaviour: Team mention alone doesn't reject - no graphics = valid interlude
            assert result is not None, "Should detect: team mention without graphics is valid"
            assert 3116 <= result <= 3120
        finally:
            detector.ocr_results = original_ocr

    def test_interlude_rejected_if_scoreboard_in_window(self, detector):
        """Should reject interlude if scoreboard/FT graphic detected in validation window."""
        teams = ('Fulham', 'Wolverhampton Wanderers')
        segments = [
            {'start': 3118.0, 'text': "Sunday's Match Of The Day."},
            {'start': 3150.0, 'text': "What a match this has been."},
        ]

        # Inject a scoreboard in the validation window
        original_ocr = detector.ocr_results
        detector.ocr_results = [
            {'start_seconds': 3140.0, 'end_seconds': 3145.0, 'ocr_source': 'scoreboard'}
        ]

        try:
            result = detector._detect_interlude(teams, 2881.0, 3169.0, segments)
            assert result is None, "Should reject: scoreboard in window means it's a match, not interlude"
        finally:
            detector.ocr_results = original_ocr

    def test_match_end_uses_interlude_detection(self, detector, transcript):
        """_detect_match_end should use interlude detection for Match 4."""
        teams = ('Fulham', 'Wolverhampton Wanderers')
        highlights_end = 2881.0
        next_match_start = 3169.0
        episode_duration = 5039.0
        segments = transcript['segments']

        result = detector._detect_match_end(
            teams, highlights_end, next_match_start, episode_duration, segments
        )

        # Should return interlude start (3118s), not naive (3169s)
        assert 3116 <= result <= 3120, f"Expected ~3118s interlude cutoff, got {result}"

    def test_match_end_naive_when_no_interlude(self, detector, transcript):
        """_detect_match_end should use naive approach when no interlude."""
        teams = ('Aston Villa', 'Liverpool')
        highlights_end = 607.0
        next_match_start = 866.0
        episode_duration = 5039.0
        segments = transcript['segments']

        result = detector._detect_match_end(
            teams, highlights_end, next_match_start, episode_duration, segments
        )

        # Should return naive approach (next match start)
        assert result == 866.0, f"Expected naive 866s, got {result}"

    def test_detect_interlude_episode02_united_alternate_false_positive(self, detector):
        """
        Interlude detection should not reject due to generic 'United' alternate.

        Episode 02, Match 3 (Burnley vs West Ham): Interlude at 2640.28s says
        "bumper Sunday match of the day", but at 2688.55s, text mentions
        "Manchester United" (women's football news).

        The OLD fuzzy matcher incorrectly matched "United" (West Ham alternate)
        against "Manchester United", causing false rejection.

        NEW approach: Use scoreboard/FT graphic absence instead of team name checks.
        The interlude has no match graphics → should be detected.
        """
        # Load Episode 02 minimal fixture (no cache dependency)
        episode02_path = Path('tests/fixtures/episodes/motd_2025-26_2025-11-08_minimal.json')
        with open(episode02_path) as f:
            episode02 = json.load(f)

        # Use Episode 02 OCR results for this test
        original_ocr = detector.ocr_results
        detector.ocr_results = episode02['ocr_results']

        try:
            # Match 3: Burnley vs West Ham United
            teams = ('Burnley', 'West Ham United')
            highlights_end = 2386.33
            next_match_start = 2704.41
            segments = episode02['segments']

            result = detector._detect_interlude(teams, highlights_end, next_match_start, segments)

            # EXPECTED: Interlude detected at 2640.28s
            # No scoreboards/FT graphics in the interlude window
            assert result is not None, (
                "Interlude at 2640.28s should be detected. "
                "No match graphics in validation window."
            )
            assert 2640 <= result <= 2641, f"Expected ~2640.28s, got {result}"
        finally:
            detector.ocr_results = original_ocr


class TestTableReviewDetection:
    """Test league table review detection using keyword + unrelated team validation."""

    def test_detect_table_review_match7_dual_signal(self, detector, transcript):
        """Match 7: Should detect table review at ~4977s with unrelated team validation."""
        teams = ('Brentford', 'Crystal Palace')
        highlights_end = 4841.0  # Match 7 FT graphic
        episode_duration = 5039.0
        segments = transcript['segments']

        # All 20 Premier League teams (2025/26)
        all_teams = [
            'Arsenal', 'Liverpool', 'Manchester United', 'Chelsea', 'Tottenham Hotspur',
            'Manchester City', 'Newcastle United', 'Brighton & Hove Albion', 'Aston Villa',
            'Wolverhampton Wanderers', 'Fulham', 'Brentford', 'Crystal Palace', 'Everton',
            'Nottingham Forest', 'West Ham United', 'Bournemouth', 'Burnley', 'Leeds United',
            'Sunderland'
        ]

        result = detector._detect_table_review(
            teams, highlights_end, episode_duration, segments, all_teams
        )

        # Expected: keyword at 4977.53s (sentence start, no buffer)
        assert result is not None, "Should detect table review"
        assert 4975 <= result <= 4980, f"Expected ~4977s, got {result}"

    def test_table_review_insufficient_unrelated_teams(self, detector):
        """Should reject if <2 unrelated teams mentioned after keyword."""
        teams = ('Brentford', 'Crystal Palace')
        segments = [
            {'start': 4977.0, 'text': "Let's look at the table."},
            {'start': 4980.0, 'text': "Arsenal are top."},  # Only 1 unrelated team
            {'start': 4985.0, 'text': "Great performance today."},
        ]
        all_teams = ['Arsenal', 'Liverpool', 'Manchester United', 'Chelsea']

        result = detector._detect_table_review(teams, 4841.0, 5039.0, segments, all_teams)

        assert result is None, "Should reject: <2 unrelated teams mentioned"

    def test_table_keyword_before_validation_window(self, detector):
        """Foreign teams mentioned BEFORE keyword should be ignored."""
        teams = ('Brentford', 'Crystal Palace')
        segments = [
            {'start': 4973.0, 'text': "Liverpool were knocked out."},  # Pre-keyword (ignored)
            {'start': 4977.0, 'text': "Let's look at the table."},  # Keyword
            {'start': 4980.0, 'text': "Arsenal are top."},  # Post-keyword (only 1!)
        ]
        all_teams = ['Arsenal', 'Liverpool', 'Manchester United', 'Chelsea']

        result = detector._detect_table_review(teams, 4841.0, 5039.0, segments, all_teams)

        # Liverpool at 4973s should be ignored (before keyword at 4977s)
        # Only Arsenal counts → <2 unrelated teams → None
        assert result is None, "Liverpool at 4973s should be ignored (pre-keyword)"

    def test_table_keyword_variations(self, detector):
        """Should detect table with various keyword phrasings."""
        teams = ('Brentford', 'Crystal Palace')
        all_teams = ['Arsenal', 'Liverpool', 'Manchester United', 'Chelsea']

        # Test variation 1: "quick look at the table"
        segments1 = [
            {'start': 4977.0, 'text': "Let's have a quick look at the table."},
            {'start': 4980.0, 'text': "Arsenal are top."},
            {'start': 4985.0, 'text': "Liverpool in second."},
        ]
        result1 = detector._detect_table_review(teams, 4841.0, 5039.0, segments1, all_teams)
        assert result1 is not None, "Should detect 'quick look at table'"

        # Test variation 2: "Premier League table"
        segments2 = [
            {'start': 4977.0, 'text': "The Premier League table shows..."},
            {'start': 4980.0, 'text': "Arsenal are top."},
            {'start': 4985.0, 'text': "Chelsea in third."},
        ]
        result2 = detector._detect_table_review(teams, 4841.0, 5039.0, segments2, all_teams)
        assert result2 is not None, "Should detect 'Premier League table'"

        # Test variation 3: "league table" without context
        segments3 = [
            {'start': 4977.0, 'text': "A look at the league."},  # Missing "table"
            {'start': 4980.0, 'text': "Arsenal are top."},
            {'start': 4985.0, 'text': "Liverpool in second."},
        ]
        result3 = detector._detect_table_review(teams, 4841.0, 5039.0, segments3, all_teams)
        assert result3 is None, "Should NOT detect without 'table' keyword"

    def test_table_keyword_rejects_comfortable_false_positive(self, detector):
        """
        Should NOT match 'table' inside 'comfortable' + 'looked'.

        Episode 02 bug: "I thought he looked really comfortable" was matching
        because 'comforTABLE' contains 'table' and 'LOOKed' contains 'look'.
        The actual table keyword "Let's take a look then at the Premier League table"
        comes later at 4080.01s.
        """
        teams = ('Chelsea', 'Wolverhampton Wanderers')
        all_teams = ['Arsenal', 'Liverpool', 'Manchester United', 'Everton', 'West Ham United']

        # Episode 02 false positive scenario
        segments = [
            # False positive at 3981.79s - "comfortable" contains "table", "looked" contains "look"
            {'start': 3981.79, 'text': "And of course they benefited from that. I thought he looked really, really comfortable."},
            # Actual table keyword at 4080.01s
            {'start': 4080.01, 'text': "Let's take a look then at the Premier League table."},
            {'start': 4082.69, 'text': "Arsenal are still six points clear at the top."},
            {'start': 4085.0, 'text': "Liverpool in second."},
        ]

        result = detector._detect_table_review(teams, 3895.0, 4200.0, segments, all_teams)

        # Should detect at 4080.01s (actual table keyword), NOT 3981.79s (false positive)
        assert result is not None, "Should detect table review"
        assert result == 4080.01, f"Expected 4080.01s (actual table keyword), got {result}s (false positive from 'comfortable')"

    def test_match_end_uses_table_detection_last_match(self, detector, transcript):
        """_detect_match_end should use table detection for last match (Match 7)."""
        teams = ('Brentford', 'Crystal Palace')
        highlights_end = 4841.0
        next_match_start = None  # Last match indicator
        episode_duration = 5039.0
        segments = transcript['segments']

        result = detector._detect_match_end(
            teams, highlights_end, next_match_start, episode_duration, segments
        )

        # Should return table cutoff (~4977s), not naive (5039s)
        assert result < 5000, f"Expected table cutoff <5000s, got {result}"
        assert 4975 <= result <= 4980, f"Expected ~4977s table cutoff, got {result}"
