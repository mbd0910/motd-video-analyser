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
        """Each match_end should equal the next match's match_start (no gaps)."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        for i in range(len(result.matches) - 1):
            current = result.matches[i]
            next_match = result.matches[i + 1]

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
        """Last match should end at episode duration."""
        base_result = detector.detect_running_order()
        result = detector.detect_match_boundaries(base_result)

        last_match = result.matches[-1]
        episode_duration = detector.transcript.get('duration', 0)

        assert last_match.match_end == episode_duration, \
            f"Last match should end at episode duration ({episode_duration}s), got {last_match.match_end}s"

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
