"""Tests for the analyser module."""

import json

import pytest

from motd.analyser import (
    AnalysisError,
    LlmBackend,
    LlmResult,
    Prompt,
    _build_prompt,
    _build_schema,
    _content_blocks,
    _resolve_matches,
    analyse,
    fixture_label,
)
from motd.models import EpisodeAnalysis, Fixture, Score, Transcript, TranscriptSegment

ARSENAL_CHELSEA = Fixture(
    fpl_code=2645195,
    match_id="2025-11-01-ARS-CHE",
    date="2025-11-01",
    home_team="Arsenal",
    away_team="Chelsea",
    home_code="ARS",
    away_code="CHE",
    venue="Emirates Stadium",
    score=Score(home=3, away=1),
    gameweek=10,
    kickoff="17:30",
    played=True,
)

BRIGHTON_LEEDS = Fixture(
    fpl_code=2645196,
    match_id="2025-11-01-BHA-LEE",
    date="2025-11-01",
    home_team="Brighton & Hove Albion",
    away_team="Leeds United",
    home_code="BHA",
    away_code="LEE",
    venue="Amex Stadium",
    score=Score(home=2, away=0),
    gameweek=10,
    kickoff="15:00",
    played=True,
)

FRIDAY_GAME = Fixture(
    fpl_code=2645194,
    match_id="2025-10-31-EVE-BUR",
    date="2025-10-31",
    home_team="Everton",
    away_team="Burnley",
    home_code="EVE",
    away_code="BUR",
    venue="Hill Dickinson Stadium",
    score=Score(home=1, away=1),
    gameweek=10,
    kickoff="20:00",
    played=True,
)

SAMPLE_CANDIDATES = [BRIGHTON_LEEDS, ARSENAL_CHELSEA]

SAMPLE_TRANSCRIPT = Transcript(
    episode_id="motd_2025-26_2025-11-01",
    duration_seconds=5400.0,
    segments=[
        TranscriptSegment(start=0.0, end=10.0, text="Welcome to Match of the Day."),
        TranscriptSegment(start=10.0, end=60.0, text="First up, Arsenal versus Chelsea."),
        TranscriptSegment(start=60.0, end=600.0, text="And it's a goal from Saka!"),
    ],
)

VALID_RESPONSE = json.dumps({
    "running_order": [
        {
            "match": fixture_label(ARSENAL_CHELSEA),
            "order": 1,
            "segments": {
                "studio_intro": {"start": "00:00", "end": "00:10"},
                "highlights": {"start": "00:10", "end": "10:00"},
                "studio_analysis": {"start": None, "end": None},
            },
            "notes": None,
        },
        {
            "match": fixture_label(BRIGHTON_LEEDS),
            "order": 2,
            "segments": {
                "studio_intro": {"start": None, "end": None},
                "highlights": {"start": "10:00", "end": "20:00"},
                "studio_analysis": {"start": None, "end": None},
            },
            "notes": None,
        },
    ]
})


def fake_backend(response: str) -> LlmBackend:
    """A backend that returns a canned response and ignores the schema."""
    def backend(prompt: Prompt, schema: dict) -> LlmResult:
        return LlmResult(text=response, model="fake-model", input_tokens=10, output_tokens=5)
    return backend


class TestFixtureLabel:
    def test_label_carries_the_date_so_a_held_over_game_is_distinguishable(self) -> None:
        assert fixture_label(ARSENAL_CHELSEA) == "2025-11-01 Arsenal v Chelsea"
        assert fixture_label(FRIDAY_GAME) == "2025-10-31 Everton v Burnley"


class TestBuildSchema:
    def test_match_is_constrained_to_the_candidate_labels(self) -> None:
        schema = _build_schema(sorted(fixture_label(f) for f in SAMPLE_CANDIDATES))
        match_field = schema["properties"]["running_order"]["items"]["properties"]["match"]
        assert match_field["enum"] == [
            "2025-11-01 Arsenal v Chelsea",
            "2025-11-01 Brighton & Hove Albion v Leeds United",
        ]

    def test_schema_is_closed(self) -> None:
        schema = _build_schema(["a", "b"])
        item = schema["properties"]["running_order"]["items"]
        assert schema["additionalProperties"] is False
        assert item["additionalProperties"] is False
        assert item["properties"]["segments"]["additionalProperties"] is False

    def test_every_property_is_required(self) -> None:
        item = _build_schema(["a"])["properties"]["running_order"]["items"]
        assert set(item["required"]) == set(item["properties"])


class TestBuildPrompt:
    def _prompt(self, candidates: list[Fixture] = SAMPLE_CANDIDATES) -> Prompt:
        return _build_prompt(
            SAMPLE_TRANSCRIPT, candidates,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )

    def test_everything_episode_specific_sits_before_the_cache_breakpoint(self) -> None:
        prompt = self._prompt()
        assert "Welcome to Match of the Day." in prompt.context
        assert "Welcome to Match of the Day." not in prompt.task
        assert "## Your task" in prompt.task
        assert "## Your task" not in prompt.context

    def test_joined_carries_both_halves_in_order(self) -> None:
        prompt = self._prompt()
        joined = prompt.joined()
        assert joined.index(prompt.context) < joined.index(prompt.task)

    def test_prompt_includes_transcript_text(self) -> None:
        context = self._prompt().context
        assert "Welcome to Match of the Day." in context
        assert "Arsenal versus Chelsea" in context

    def test_prompt_lists_candidates_by_their_exact_label(self) -> None:
        context = self._prompt().context
        assert f'"{fixture_label(ARSENAL_CHELSEA)}"' in context
        assert f'"{fixture_label(BRIGHTON_LEEDS)}"' in context
        assert "Emirates Stadium" in context

    def test_prompt_flags_a_candidate_played_on_an_earlier_date(self) -> None:
        context = self._prompt([FRIDAY_GAME, ARSENAL_CHELSEA]).context
        assert "played 2025-10-31" in context
        assert "played this day" in context

    def test_prompt_formats_timestamps_as_mmss(self) -> None:
        context = self._prompt().context
        assert "[00:00]" in context
        assert "[00:10]" in context
        assert "[01:00]" in context


class TestContentBlocks:
    def _blocks(self, ttl: str | None) -> list[dict]:
        return _content_blocks(Prompt(context="episode", task="instructions"), ttl)

    def test_the_breakpoint_lands_after_the_context_half(self) -> None:
        blocks = self._blocks("1h")
        assert [b["text"] for b in blocks] == ["episode", "instructions"]
        assert blocks[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
        assert "cache_control" not in blocks[1]

    def test_no_breakpoint_when_caching_is_off(self) -> None:
        assert all("cache_control" not in b for b in self._blocks(None))

class TestResolveMatches:
    def _by_label(self) -> dict[str, Fixture]:
        return {fixture_label(f): f for f in SAMPLE_CANDIDATES}

    def test_labels_resolve_to_fixture_ids(self) -> None:
        matches = _resolve_matches(VALID_RESPONSE, self._by_label())
        assert [m.fpl_code for m in matches] == [
            ARSENAL_CHELSEA.fpl_code, BRIGHTON_LEEDS.fpl_code,
        ]
        assert [m.order for m in matches] == [1, 2]

    def test_empty_segments_are_dropped(self) -> None:
        matches = _resolve_matches(VALID_RESPONSE, self._by_label())
        assert set(matches[0].segments) == {"studio_intro", "highlights"}
        assert set(matches[1].segments) == {"highlights"}

    def test_label_outside_the_candidate_list_raises(self) -> None:
        response = json.dumps({
            "running_order": [{
                "match": "2025-11-01 Fulham v Wolverhampton Wanderers",
                "order": 1,
                "segments": {},
                "notes": None,
            }]
        })
        with pytest.raises(AnalysisError, match="not a candidate"):
            _resolve_matches(response, self._by_label())

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(AnalysisError, match="Failed to parse"):
            _resolve_matches("not valid json at all", self._by_label())

    def test_running_order_not_a_list_raises(self) -> None:
        bad = json.dumps({"running_order": "not a list"})
        with pytest.raises(AnalysisError, match="Expected 'running_order' to be a list"):
            _resolve_matches(bad, self._by_label())

    def test_malformed_entry_raises(self) -> None:
        bad = json.dumps({
            "running_order": [{"match": fixture_label(ARSENAL_CHELSEA), "order": 0}]
        })
        with pytest.raises(AnalysisError, match="Malformed running order entry"):
            _resolve_matches(bad, self._by_label())


class TestAnalyseWithFakeBackend:
    def test_analyse_returns_valid_analysis(self) -> None:
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01",
            backend=fake_backend(VALID_RESPONSE),
        )

        assert isinstance(analysis, EpisodeAnalysis)
        assert analysis.episode_id == "motd_2025-26_2025-11-01"
        assert analysis.broadcast_date == "2025-11-01"
        assert analysis.season == "2025-26"
        assert analysis.gameweek == 10
        assert [m.fpl_code for m in analysis.matches] == [
            ARSENAL_CHELSEA.fpl_code, BRIGHTON_LEEDS.fpl_code,
        ]

    def test_provenance_records_the_candidates_the_model_actually_saw(self) -> None:
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01",
            backend=fake_backend(VALID_RESPONSE),
        )
        assert analysis.provenance is not None
        assert analysis.provenance.candidate_fpl_codes == [
            BRIGHTON_LEEDS.fpl_code, ARSENAL_CHELSEA.fpl_code,
        ]
        assert analysis.provenance.model == "fake-model"
        assert analysis.provenance.prompt_version
        assert analysis.provenance.input_tokens == 10

    def test_schema_reaches_the_backend_with_the_candidate_enum(self) -> None:
        captured: dict[str, dict] = {}

        def capturing(prompt: Prompt, schema: dict) -> LlmResult:
            captured["schema"] = schema
            return LlmResult(text=VALID_RESPONSE, model="fake-model")

        analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=capturing,
        )
        enum = captured["schema"]["properties"]["running_order"]["items"]["properties"]["match"]
        assert set(enum["enum"]) == {fixture_label(f) for f in SAMPLE_CANDIDATES}

    def test_duplicate_fixtures_in_running_order_rejected(self) -> None:
        repeated = json.dumps({
            "running_order": [
                {"match": fixture_label(ARSENAL_CHELSEA), "order": 1,
                 "segments": {}, "notes": None},
                {"match": fixture_label(ARSENAL_CHELSEA), "order": 2,
                 "segments": {}, "notes": None},
            ]
        })
        with pytest.raises(AnalysisError, match="Duplicate fixtures"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
                "motd_2025-26_2025-11-01", backend=fake_backend(repeated),
            )

    def test_running_order_with_a_gap_rejected(self) -> None:
        gapped = json.dumps({
            "running_order": [
                {"match": fixture_label(ARSENAL_CHELSEA), "order": 1,
                 "segments": {}, "notes": None},
                {"match": fixture_label(BRIGHTON_LEEDS), "order": 3,
                 "segments": {}, "notes": None},
            ]
        })
        with pytest.raises(AnalysisError, match="Running order must be"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
                "motd_2025-26_2025-11-01", backend=fake_backend(gapped),
            )

    def test_analyse_raises_on_backend_failure(self) -> None:
        def failing(prompt: Prompt, schema: dict) -> LlmResult:
            raise AnalysisError("LLM unavailable")

        with pytest.raises(AnalysisError, match="LLM unavailable"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
                "motd_2025-26_2025-11-01", backend=failing,
            )

    def test_analyse_raises_on_invalid_episode_id(self) -> None:
        with pytest.raises(AnalysisError, match="Invalid episode_id"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES, "bad_id",
                backend=fake_backend(VALID_RESPONSE),
            )

    def test_analyse_raises_without_candidates(self) -> None:
        with pytest.raises(AnalysisError, match="No candidate fixtures"):
            analyse(
                SAMPLE_TRANSCRIPT, [], "motd_2025-26_2025-11-01",
                backend=fake_backend(VALID_RESPONSE),
            )

    def test_empty_running_order_is_valid(self) -> None:
        """An episode may be an FA Cup special covering none of the candidates."""
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES, "motd_2025-26_2025-11-01",
            backend=fake_backend(json.dumps({"running_order": []})),
        )
        assert analysis.matches == []

    def test_backend_satisfies_protocol(self) -> None:
        assert isinstance(fake_backend(VALID_RESPONSE), LlmBackend)
