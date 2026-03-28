"""Tests for the analyser module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from motd.analyser import AnalysisError, _build_prompt, _parse_response, analyse
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

    def test_prompt_includes_timestamps(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "00:00" in prompt or "0.0" in prompt

    def test_prompt_requests_json_output(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "JSON" in prompt or "json" in prompt


class TestParseResponse:
    """Test parsing Claude's JSON response into EpisodeAnalysis."""

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
        """Claude sometimes wraps JSON in markdown fences."""
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


class TestAnalyseIntegration:
    """Integration test: mock Claude subprocess, verify full flow."""

    @patch("motd.analyser.subprocess.run")
    def test_analyse_returns_valid_analysis(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=VALID_ANALYSIS_JSON,
            stderr="",
        )

        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )

        assert isinstance(analysis, EpisodeAnalysis)
        assert len(analysis.matches) == 2
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "claude" in cmd

    @patch("motd.analyser.subprocess.run")
    def test_analyse_raises_on_claude_failure(
        self, mock_run: MagicMock
    ) -> None:
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "claude", stderr="Claude error"
        )

        with pytest.raises(AnalysisError, match="Claude"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_FIXTURES,
                "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
            )
