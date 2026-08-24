"""Tests for new Pydantic data contracts."""

import pytest
from pydantic import ValidationError

from motd.models import (
    AnalysisProvenance,
    EpisodeAnalysis,
    Fixture,
    MatchCoverage,
    Score,
    Segment,
    Transcript,
    TranscriptSegment,
)


class TestTranscriptSegment:
    def test_valid_segment(self) -> None:
        seg = TranscriptSegment(start=0.0, end=5.5, text="Hello world")
        assert seg.start == 0.0
        assert seg.end == 5.5
        assert seg.text == "Hello world"

    def test_end_must_be_after_start(self) -> None:
        with pytest.raises(ValidationError):
            TranscriptSegment(start=10.0, end=5.0, text="Bad")

    def test_text_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            TranscriptSegment(start=0.0, end=1.0, text="")

    def test_negative_start_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TranscriptSegment(start=-1.0, end=1.0, text="Nope")


class TestTranscript:
    def test_valid_transcript(self) -> None:
        t = Transcript(
            episode_id="motd_2025-26_2025-11-01",
            duration_seconds=5400.0,
            segments=[
                TranscriptSegment(start=0.0, end=5.0, text="Welcome"),
                TranscriptSegment(start=5.0, end=10.0, text="To MOTD"),
            ],
        )
        assert t.episode_id == "motd_2025-26_2025-11-01"
        assert len(t.segments) == 2

    def test_duration_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Transcript(episode_id="ep1", duration_seconds=-1.0, segments=[])


class TestFixture:
    def test_valid_fixture(self) -> None:
        f = Fixture(
            fpl_code=2645196,
            match_id="2025-11-01-BHA-LEE",
            date="2025-11-01",
            home_team="Brighton & Hove Albion",
            away_team="Leeds United",
            home_code="BHA",
            away_code="LEE",
            venue="Amex Stadium",
            score=Score(home=2, away=1),
        )
        assert f.home_team == "Brighton & Hove Albion"
        assert f.score.home == 2

    def test_fixture_without_score(self) -> None:
        f = Fixture(
            fpl_code=2645196,
            match_id="2025-11-01-BHA-LEE",
            date="2025-11-01",
            home_team="Brighton",
            away_team="Leeds",
            home_code="BHA",
            away_code="LEE",
            venue="Amex",
        )
        assert f.score is None

    def test_fixture_requires_a_stable_id(self) -> None:
        with pytest.raises(ValidationError):
            Fixture(
                match_id="2025-11-01-BHA-LEE",
                date="2025-11-01",
                home_team="Brighton",
                away_team="Leeds",
                home_code="BHA",
                away_code="LEE",
                venue="Amex",
            )


class TestScore:
    def test_valid_score(self) -> None:
        s = Score(home=2, away=1)
        assert s.home == 2
        assert s.away == 1

    def test_negative_score_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Score(home=-1, away=0)


class TestSegment:
    def test_valid_segment(self) -> None:
        s = Segment(start="12:30", end="15:45")
        assert s.start == "12:30"
        assert s.end == "15:45"

    def test_nullable_timestamps(self) -> None:
        s = Segment(start="12:30", end=None)
        assert s.end is None

    def test_both_null(self) -> None:
        s = Segment()
        assert s.start is None
        assert s.end is None


class TestMatchCoverage:
    def test_valid_match(self) -> None:
        m = MatchCoverage(
            fpl_code=2645195,
            order=1,
            segments={
                "highlights": Segment(start="12:30", end="20:00"),
            },
        )
        assert m.order == 1
        assert m.segments["highlights"].start == "12:30"

    def test_order_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            MatchCoverage(fpl_code=2645195, order=0, segments={})


class TestEpisodeAnalysis:
    def test_valid_analysis(self) -> None:
        analysis = EpisodeAnalysis(
            episode_id="motd_2025-26_2025-11-01",
            broadcast_date="2025-11-01",
            season="2025-26",
            matches=[
                MatchCoverage(
                    fpl_code=2645195,
                    order=1,
                    segments={
                        "highlights": Segment(start="05:00", end="15:00"),
                    },
                ),
            ],
        )
        assert analysis.episode_id == "motd_2025-26_2025-11-01"
        assert len(analysis.matches) == 1

    def test_duplicate_fixtures_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate fixtures"):
            EpisodeAnalysis(
                episode_id="motd_2025-26_2025-11-01",
                broadcast_date="2025-11-01",
                season="2025-26",
                matches=[
                    MatchCoverage(fpl_code=2645195, order=1),
                    MatchCoverage(fpl_code=2645195, order=2),
                ],
            )

    def test_running_order_with_a_gap_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Running order must be"):
            EpisodeAnalysis(
                episode_id="motd_2025-26_2025-11-01",
                broadcast_date="2025-11-01",
                season="2025-26",
                matches=[
                    MatchCoverage(fpl_code=2645195, order=1),
                    MatchCoverage(fpl_code=2645196, order=3),
                ],
            )

    def test_no_matches_is_valid(self) -> None:
        analysis = EpisodeAnalysis(
            episode_id="motd_2025-26_2025-11-01",
            broadcast_date="2025-11-01",
            season="2025-26",
        )
        assert analysis.matches == []

    def test_serialise_roundtrip(self) -> None:
        analysis = EpisodeAnalysis(
            episode_id="motd_2025-26_2025-11-01",
            broadcast_date="2025-11-01",
            season="2025-26",
            matches=[
                MatchCoverage(fpl_code=2645195, order=1, segments={}),
            ],
            provenance=AnalysisProvenance(
                model="claude-opus-5",
                prompt_version="2",
                analysed_at="2026-08-24T21:00:00Z",
                candidate_fpl_codes=[2645195, 2645196],
            ),
        )
        json_str = analysis.model_dump_json()
        roundtripped = EpisodeAnalysis.model_validate_json(json_str)
        assert roundtripped == analysis
