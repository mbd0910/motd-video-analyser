"""Tests for the analyser module."""

import json

import pytest

from motd.analyser import AnalysisError, LlmBackend, _build_prompt, _parse_response, analyse
from motd.models import (
    EpisodeAnalysis,
    Fixture,
    Score,
    Transcript,
    TranscriptSegment,
)

SAMPLE_FIXTURES = [
    Fixture(
        match_id="2025-11-01-arsenal-chelsea",
        date="2025-11-01",
        home_team="Arsenal",
        away_team="Chelsea",
        venue="Emirates Stadium",
        score=Score(home=3, away=1),
    ),
    Fixture(
        match_id="2025-11-01-brighton-leeds",
        date="2025-11-01",
        home_team="Brighton & Hove Albion",
        away_team="Leeds United",
        venue="Amex Stadium",
        score=Score(home=2, away=0),
    ),
]

SAMPLE_TRANSCRIPT = Transcript(
    episode_id="motd_2025-26_2025-11-01",
    duration_seconds=5400.0,
    segments=[
        TranscriptSegment(start=0.0, end=10.0, text="Welcome to Match of the Day."),
        TranscriptSegment(start=10.0, end=60.0, text="First up, Arsenal versus Chelsea."),
        TranscriptSegment(start=60.0, end=600.0, text="And it's a goal from Saka!"),
    ],
)

VALID_ANALYSIS_JSON = json.dumps({
    "matches": [
        {
            "order": 1,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "venue": "Emirates Stadium",
            "score": {"home": 3, "away": 1},
            "segments": {
                "studio_intro": {"start": "00:00", "end": "00:10"},
                "highlights": {"start": "00:10", "end": "10:00"},
            },
            "notes": None,
        },
        {
            "order": 2,
            "home_team": "Brighton & Hove Albion",
            "away_team": "Leeds United",
            "venue": "Amex Stadium",
            "score": {"home": 2, "away": 0},
            "segments": {
                "highlights": {"start": "10:00", "end": "20:00"},
            },
            "notes": None,
        },
    ]
})


class TestBuildPrompt:
    """Test prompt construction from transcript and fixtures."""

    def test_prompt_includes_transcript_text(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "Welcome to Match of the Day." in prompt
        assert "Arsenal versus Chelsea" in prompt

    def test_prompt_includes_fixture_data(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "Arsenal" in prompt
        assert "Chelsea" in prompt
        assert "Emirates Stadium" in prompt
        assert "Brighton" in prompt

    def test_prompt_formats_timestamps_as_mmss(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "[00:00]" in prompt
        assert "[00:10]" in prompt
        assert "[01:00]" in prompt

    def test_prompt_requests_json_output(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "JSON" in prompt or "json" in prompt


class TestParseResponse:
    """Test parsing LLM JSON response into EpisodeAnalysis."""

    def test_valid_response_parsed(self) -> None:
        analysis = _parse_response(
            VALID_ANALYSIS_JSON,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert isinstance(analysis, EpisodeAnalysis)
        assert analysis.episode_id == "motd_2025-26_2025-11-01"
        assert analysis.broadcast_date == "2025-11-01"
        assert analysis.season == "2025-26"
        assert len(analysis.matches) == 2
        assert analysis.matches[0].order == 1
        assert analysis.matches[0].home_team == "Arsenal"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(AnalysisError, match="Failed to parse"):
            _parse_response(
                "not valid json at all",
                "ep1", "2025-11-01", "2025-26",
            )

    def test_missing_required_fields_raises(self) -> None:
        bad_json = json.dumps({"matches": [{"order": 1}]})
        with pytest.raises(AnalysisError, match="doesn't match expected schema"):
            _parse_response(bad_json, "ep1", "2025-11-01", "2025-26")

    def test_matches_not_a_list_raises(self) -> None:
        bad_json = json.dumps({"matches": "not a list"})
        with pytest.raises(AnalysisError, match="Expected 'matches' to be a list"):
            _parse_response(bad_json, "ep1", "2025-11-01", "2025-26")

    def test_response_with_json_fence_parsed(self) -> None:
        """LLMs sometimes wrap JSON in markdown fences."""
        fenced = f"```json\n{VALID_ANALYSIS_JSON}\n```"
        analysis = _parse_response(
            fenced,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert len(analysis.matches) == 2

    def test_running_order_sequential(self) -> None:
        analysis = _parse_response(
            VALID_ANALYSIS_JSON,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        orders = [m.order for m in analysis.matches]
        assert orders == sorted(orders)
        assert orders == list(range(1, len(orders) + 1))


class TestAnalyseWithFakeBackend:
    """Test analyse() with injected fake LLM backend — no subprocess mocking."""

    def test_analyse_returns_valid_analysis(self) -> None:
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01",
            backend=lambda prompt: VALID_ANALYSIS_JSON,
        )

        assert isinstance(analysis, EpisodeAnalysis)
        assert analysis.episode_id == "motd_2025-26_2025-11-01"
        assert analysis.broadcast_date == "2025-11-01"
        assert analysis.season == "2025-26"
        assert len(analysis.matches) == 2
        assert analysis.matches[0].order == 1
        assert analysis.matches[0].home_team == "Arsenal"
        assert analysis.matches[0].away_team == "Chelsea"
        assert analysis.matches[1].order == 2
        assert analysis.matches[1].home_team == "Brighton & Hove Albion"

    def test_analyse_raises_on_backend_failure(self) -> None:
        def failing_backend(prompt: str) -> str:
            raise AnalysisError("LLM unavailable")

        with pytest.raises(AnalysisError, match="LLM unavailable"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
                "motd_2025-26_2025-11-01",
                backend=failing_backend,
            )

    def test_analyse_raises_on_malformed_response(self) -> None:
        with pytest.raises(AnalysisError, match="Failed to parse"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
                "motd_2025-26_2025-11-01",
                backend=lambda prompt: "not json at all",
            )

    def test_analyse_raises_on_invalid_episode_id(self) -> None:
        with pytest.raises(AnalysisError, match="Invalid episode_id"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
                "bad_id",
                backend=lambda prompt: VALID_ANALYSIS_JSON,
            )

    def test_prompt_includes_fixtures(self) -> None:
        """Verify the prompt sent to the backend includes fixture data."""
        captured: dict[str, str] = {}

        def capturing_backend(prompt: str) -> str:
            captured["prompt"] = prompt
            return VALID_ANALYSIS_JSON

        analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01",
            backend=capturing_backend,
        )

        assert "Arsenal" in captured["prompt"]
        assert "Emirates Stadium" in captured["prompt"]
        assert "Brighton" in captured["prompt"]

    def test_backend_satisfies_protocol(self) -> None:
        """A lambda satisfies LlmBackend protocol."""
        backend = lambda prompt: VALID_ANALYSIS_JSON  # noqa: E731
        assert isinstance(backend, LlmBackend)
