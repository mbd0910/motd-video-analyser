"""Tests for the analyser module."""

import json

import pytest

from motd.analyser import (
    SEGMENT_KEYS,
    AnalysisError,
    LlmBackend,
    LlmResult,
    Prompt,
    _assert_highlights_do_not_overlap,
    _build_prompt,
    _build_schema,
    _content_blocks,
    _normalise,
    _parse_response,
    _resolve_location,
    _timeline_share,
    analyse,
    fixture_label,
)
from motd.models import (
    EpisodeAnalysis,
    Fixture,
    MatchCoverage,
    Score,
    Transcript,
    TranscriptSegment,
)

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

# The handover lines are checked against this text, so the canned replies quote it.
SAMPLE_TRANSCRIPT = Transcript(
    episode_id="motd_2025-26_2025-11-01",
    duration_seconds=5400.0,
    segments=[
        TranscriptSegment(start=0.0, end=10.0, text="Welcome to Match of the Day."),
        TranscriptSegment(start=10.0, end=60.0, text="Guy Mowbray was at the Emirates Stadium."),
        TranscriptSegment(start=60.0, end=600.0, text="And it's a goal from Saka!"),
        TranscriptSegment(start=2700.0, end=2760.0, text="Steve Wilson was at the Amex Stadium."),
    ],
)

HAYSTACK = _normalise(" ".join(seg.text for seg in SAMPLE_TRANSCRIPT.segments))


def located(handover: str, **spans: tuple[str, str]) -> dict:
    """One match's reply — absence is an empty string, as the schema has no nulls."""
    blank = {"start": "", "end": ""}
    return {
        "handover": handover,
        **{key: blank for key in SEGMENT_KEYS},
        **{key: {"start": start, "end": end} for key, (start, end) in spans.items()},
        "notes": "",
    }


ARSENAL_REPLY = located(
    "Guy Mowbray was at the Emirates Stadium.",
    studio_intro=("00:00", "00:10"),
    highlights=("00:10", "45:00"),
)
BRIGHTON_REPLY = located(
    "Steve Wilson was at the Amex Stadium.",
    highlights=("45:00", "88:00"),
)
# The candidate order is chronological by kickoff, so Brighton is asked about first
# and Arsenal second — the reverse of the order they aired in.
REPLIES_BY_LABEL = {
    fixture_label(BRIGHTON_LEEDS): BRIGHTON_REPLY,
    fixture_label(ARSENAL_CHELSEA): ARSENAL_REPLY,
}


def fake_backend(*replies: dict) -> LlmBackend:
    """A backend that answers each call in turn, ignoring the schema."""
    queued = list(replies)

    def backend(prompt: Prompt, schema: dict) -> LlmResult:
        reply = queued.pop(0) if len(queued) > 1 else queued[0]
        return LlmResult(
            text=json.dumps(reply), model="fake-model", input_tokens=10, output_tokens=5
        )

    return backend


def replying_by_match() -> LlmBackend:
    """A backend that answers whichever match the task half names."""

    def backend(prompt: Prompt, schema: dict) -> LlmResult:
        reply = next(r for label, r in REPLIES_BY_LABEL.items() if label in prompt.task)
        return LlmResult(
            text=json.dumps(reply), model="fake-model", input_tokens=10, output_tokens=5
        )

    return backend


class TestFixtureLabel:
    def test_label_carries_the_date_so_a_held_over_game_is_distinguishable(self) -> None:
        assert fixture_label(ARSENAL_CHELSEA) == "2025-11-01 Arsenal v Chelsea"
        assert fixture_label(FRIDAY_GAME) == "2025-10-31 Everton v Burnley"


class TestBuildSchema:
    def test_the_schema_does_not_depend_on_the_episode(self) -> None:
        # One match's shape, so it compiles once and is cached across every episode,
        # rather than being rebuilt from that gameweek's candidate labels.
        assert _build_schema() == _build_schema()

    def test_the_quote_is_generated_before_the_timings_it_anchors(self) -> None:
        assert list(_build_schema()["properties"])[0] == "handover"

    def test_no_position_is_asked_for(self) -> None:
        # Order is derived from the timestamps, so the model cannot get it wrong.
        assert "order" not in _build_schema()["properties"]

    def test_no_parameter_is_union_typed(self) -> None:
        # Structured outputs cap a schema at 16 union-typed parameters.
        def unions(node: object) -> int:
            if not isinstance(node, dict):
                return 0
            here = int(isinstance(node.get("type"), list) or "anyOf" in node)
            return here + sum(unions(child) for child in node.get("properties", {}).values())

        assert unions(_build_schema()) == 0

    def test_schema_is_closed(self) -> None:
        schema = _build_schema()
        assert schema["additionalProperties"] is False
        assert schema["properties"]["highlights"]["additionalProperties"] is False

    def test_every_property_is_required(self) -> None:
        schema = _build_schema()
        assert set(schema["required"]) == set(schema["properties"])


class TestBuildPrompt:
    def _prompt(self, fixture: Fixture = ARSENAL_CHELSEA) -> Prompt:
        return _build_prompt(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES, fixture,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )

    def test_the_context_half_is_the_same_for_every_match(self) -> None:
        # This is what makes it the cached half: one write per episode, not per match.
        assert self._prompt(ARSENAL_CHELSEA).context == self._prompt(BRIGHTON_LEEDS).context

    def test_the_task_half_names_the_one_match_to_locate(self) -> None:
        task = self._prompt(ARSENAL_CHELSEA).task
        assert fixture_label(ARSENAL_CHELSEA) in task
        assert fixture_label(BRIGHTON_LEEDS) not in task

    def test_joined_carries_both_halves_in_order(self) -> None:
        prompt = self._prompt()
        assert prompt.joined() == f"{prompt.context}\n\n{prompt.task}"

    def test_context_includes_transcript_text(self) -> None:
        assert "And it's a goal from Saka!" in self._prompt().context

    def test_context_lists_every_match_in_the_episode(self) -> None:
        context = self._prompt().context
        for fixture in SAMPLE_CANDIDATES:
            assert fixture_label(fixture) in context

    def test_context_flags_a_match_played_on_an_earlier_date(self) -> None:
        prompt = _build_prompt(
            SAMPLE_TRANSCRIPT, [FRIDAY_GAME], FRIDAY_GAME,
            "motd_2025-26_2025-11-01", "2025-11-01", "2025-26",
        )
        assert "played 2025-10-31" in prompt.context

    def test_context_formats_timestamps_as_mmss(self) -> None:
        assert "[00:10] Guy Mowbray" in self._prompt().context


class TestContentBlocks:
    def test_the_breakpoint_lands_after_the_context_half(self) -> None:
        blocks = _content_blocks(Prompt(context="ctx", task="task"), "5m")
        assert blocks[0]["cache_control"] == {"type": "ephemeral", "ttl": "5m"}
        assert "cache_control" not in blocks[1]

    def test_no_breakpoint_when_caching_is_off(self) -> None:
        blocks = _content_blocks(Prompt(context="ctx", task="task"), None)
        assert all("cache_control" not in block for block in blocks)


class TestResolveLocation:
    def test_timings_and_the_second_the_match_starts(self) -> None:
        coverage, start = _resolve_location(ARSENAL_REPLY, ARSENAL_CHELSEA, HAYSTACK)
        assert coverage.fpl_code == ARSENAL_CHELSEA.fpl_code
        assert set(coverage.segments) == {"studio_intro", "highlights"}
        assert start == 0.0

    def test_the_verified_quote_is_kept_as_evidence(self) -> None:
        coverage, _ = _resolve_location(ARSENAL_REPLY, ARSENAL_CHELSEA, HAYSTACK)
        assert coverage.handover == "Guy Mowbray was at the Emirates Stadium."

    def test_the_empty_string_sentinel_does_not_reach_the_stored_analysis(self) -> None:
        reply = located("Guy Mowbray was at the Emirates Stadium.", highlights=("00:10", ""))
        coverage, _ = _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)
        assert coverage.segments["highlights"].end is None
        assert coverage.notes is None

    def test_a_match_with_no_timings_is_a_failed_run_not_an_absence(self) -> None:
        with pytest.raises(AnalysisError, match="failed run"):
            _resolve_location(located(""), ARSENAL_CHELSEA, HAYSTACK)

    def test_a_quote_that_is_not_in_the_transcript_raises(self) -> None:
        reply = located("Jon Champion was at Old Trafford.", highlights=("00:10", "45:00"))
        with pytest.raises(AnalysisError, match="not in the transcript"):
            _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)

    def test_a_quote_too_short_to_mean_anything_raises(self) -> None:
        reply = located("the", highlights=("00:10", "45:00"))
        with pytest.raises(AnalysisError, match="too short to verify"):
            _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)

    def test_punctuation_and_case_drift_do_not_break_verification(self) -> None:
        reply = located("guy mowbray was at the EMIRATES stadium", highlights=("00:10", "45:00"))
        coverage, _ = _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)
        assert coverage.fpl_code == ARSENAL_CHELSEA.fpl_code

    def test_a_quote_spanning_two_subtitle_lines_still_verifies(self) -> None:
        # Subtitles break mid-sentence, so the transcript is joined with spaces —
        # without them the words either side of a break fuse and a real quote fails.
        reply = located("Emirates Stadium. And it's a goal", highlights=("00:10", "45:00"))
        coverage, _ = _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)
        assert coverage.fpl_code == ARSENAL_CHELSEA.fpl_code

    def test_a_malformed_span_raises(self) -> None:
        reply = located("Guy Mowbray was at the Emirates Stadium.")
        reply["highlights"] = "not an object"
        with pytest.raises(AnalysisError, match="malformed highlights"):
            _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)

    def test_a_match_timed_only_by_its_end_raises(self) -> None:
        reply = located("Guy Mowbray was at the Emirates Stadium.", highlights=("", "45:00"))
        with pytest.raises(AnalysisError, match="no usable start time"):
            _resolve_location(reply, ARSENAL_CHELSEA, HAYSTACK)


class TestParseResponse:
    def test_invalid_json_raises(self) -> None:
        with pytest.raises(AnalysisError, match="Failed to parse"):
            _parse_response("not valid json at all")

    def test_a_non_object_reply_raises(self) -> None:
        with pytest.raises(AnalysisError, match="Expected a JSON object"):
            _parse_response("[1, 2, 3]")


class TestOverlapCheck:
    def _match(self, fpl_code: int, order: int, start: str, end: str) -> MatchCoverage:
        return MatchCoverage(
            fpl_code=fpl_code, order=order,
            segments={"highlights": {"start": start, "end": end}},
        )

    def test_abutting_packages_are_normal(self) -> None:
        _assert_highlights_do_not_overlap(
            [self._match(1, 1, "00:00", "20:00"), self._match(2, 2, "20:00", "40:00")], []
        )

    def test_packages_out_of_running_order_are_not_a_false_overlap(self) -> None:
        # A match takes its place in the order from its earliest segment of any kind,
        # so the list can reach the check with its highlights spans out of sequence.
        _assert_highlights_do_not_overlap(
            [self._match(1, 1, "63:06", "63:33"), self._match(2, 2, "62:05", "62:37")], []
        )

    def test_two_matches_claiming_the_same_screen_time_raises(self) -> None:
        # Each match is located by its own call, so nothing else catches this.
        with pytest.raises(AnalysisError, match="overlapping highlights"):
            _assert_highlights_do_not_overlap(
                [self._match(1, 1, "00:00", "20:00"), self._match(2, 2, "15:00", "40:00")], []
            )


class TestTimelineShare:
    def _match(self, order: int, *spans: tuple[str, str]) -> MatchCoverage:
        return MatchCoverage(
            fpl_code=order, order=order,
            segments={
                key: {"start": start, "end": end}
                for key, (start, end) in zip(SEGMENT_KEYS, spans, strict=False)
            },
        )

    def test_abutting_segments_of_one_match_are_not_double_counted(self) -> None:
        match = self._match(1, ("00:00", "10:00"), ("10:00", "20:00"))
        assert _timeline_share([match], 2400) == pytest.approx(0.5)

    def test_a_round_up_inside_a_fuller_package_is_counted_once(self) -> None:
        first = self._match(1, ("00:00", "20:00"))
        second = self._match(2, ("10:00", "30:00"))
        assert _timeline_share([first, second], 3600) == pytest.approx(0.5)

    def test_a_gap_between_matches_is_not_counted(self) -> None:
        first = self._match(1, ("00:00", "10:00"))
        second = self._match(2, ("50:00", "60:00"))
        assert _timeline_share([first, second], 3600) == pytest.approx(1 / 3)

    def test_untimed_matches_give_no_answer_rather_than_zero(self) -> None:
        assert _timeline_share([self._match(1)], 3600) is None

    def test_a_transcript_of_unknown_length_gives_no_answer(self) -> None:
        assert _timeline_share([self._match(1, ("00:00", "10:00"))], 0) is None

    def test_a_reversed_span_is_ignored_rather_than_counted_negative(self) -> None:
        assert _timeline_share([self._match(1, ("20:00", "10:00"))], 3600) is None


class TestAnalyseWithFakeBackend:
    def test_analyse_returns_valid_analysis(self) -> None:
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=replying_by_match(),
        )
        assert isinstance(analysis, EpisodeAnalysis)
        assert analysis.episode_id == "motd_2025-26_2025-11-01"
        assert analysis.broadcast_date == "2025-11-01"
        assert analysis.season == "2025-26"
        assert analysis.gameweek == 10

    def test_the_running_order_comes_from_the_timestamps(self) -> None:
        # Brighton is asked about first and answers 45:00; Arsenal answers 00:00. The
        # order follows the clock, not the order the matches were asked about.
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=replying_by_match(),
        )
        assert [m.fpl_code for m in analysis.matches] == [
            ARSENAL_CHELSEA.fpl_code, BRIGHTON_LEEDS.fpl_code,
        ]
        assert [m.order for m in analysis.matches] == [1, 2]

    def test_one_call_is_made_for_each_match(self) -> None:
        tasks = []

        def counting(prompt: Prompt, schema: dict) -> LlmResult:
            tasks.append(prompt.task)
            reply = next(r for label, r in REPLIES_BY_LABEL.items() if label in prompt.task)
            return LlmResult(text=json.dumps(reply), model="fake-model")

        analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=counting,
        )
        assert len(tasks) == len(SAMPLE_CANDIDATES)

    def test_provenance_records_the_candidates_and_sums_the_calls(self) -> None:
        analysis = analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=replying_by_match(),
        )
        assert analysis.provenance is not None
        assert analysis.provenance.candidate_fpl_codes == [
            BRIGHTON_LEEDS.fpl_code, ARSENAL_CHELSEA.fpl_code,
        ]
        assert analysis.provenance.model == "fake-model"
        assert analysis.provenance.prompt_version == "4"
        assert analysis.provenance.walkthrough is None

    def test_a_match_the_model_cannot_place_fails_the_whole_run(self) -> None:
        """Every match in the window was shown, so a missing one is a broken run."""
        with pytest.raises(AnalysisError, match="failed run"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
                "motd_2025-26_2025-11-01", backend=fake_backend(located("")),
            )

    def test_timings_that_leave_the_episode_unexplained_are_rejected(self) -> None:
        """One ten-minute package out of ninety minutes is not a whole show."""
        thin = located(
            "Guy Mowbray was at the Emirates Stadium.", highlights=("02:05", "12:26")
        )
        with pytest.raises(AnalysisError, match="account for only"):
            analyse(
                SAMPLE_TRANSCRIPT, [ARSENAL_CHELSEA],
                "motd_2025-26_2025-11-01", backend=fake_backend(thin),
            )

    def test_two_matches_landing_on_one_package_are_rejected(self) -> None:
        both = located(
            "Guy Mowbray was at the Emirates Stadium.", highlights=("00:10", "88:00")
        )
        with pytest.raises(AnalysisError, match="overlapping highlights"):
            analyse(
                SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
                "motd_2025-26_2025-11-01", backend=fake_backend(both),
            )

    def test_the_schema_reaching_the_backend_asks_for_one_match(self) -> None:
        captured: dict[str, dict] = {}

        def capturing(prompt: Prompt, schema: dict) -> LlmResult:
            captured["schema"] = schema
            reply = next(r for label, r in REPLIES_BY_LABEL.items() if label in prompt.task)
            return LlmResult(text=json.dumps(reply), model="fake-model")

        analyse(
            SAMPLE_TRANSCRIPT, SAMPLE_CANDIDATES,
            "motd_2025-26_2025-11-01", backend=capturing,
        )
        assert set(captured["schema"]["properties"]) == {"handover", *SEGMENT_KEYS, "notes"}

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
                backend=replying_by_match(),
            )

    def test_analyse_raises_without_candidates(self) -> None:
        with pytest.raises(AnalysisError, match="No candidate fixtures"):
            analyse(
                SAMPLE_TRANSCRIPT, [], "motd_2025-26_2025-11-01",
                backend=replying_by_match(),
            )

    def test_backend_satisfies_protocol(self) -> None:
        assert isinstance(replying_by_match(), LlmBackend)
