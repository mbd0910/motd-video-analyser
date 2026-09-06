"""Analyser module — locates each of the gameweek's matches in an episode transcript.

The model is never asked which matches were shown, or in what order. MOTD is the
highlights show for every Premier League match played, so the candidate window already
answers the first question, and the running order falls out of sorting the timestamps.
What is left is the one thing a transcript alone can settle: where each match sits.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from pydantic import ValidationError

from motd.episode import Episode
from motd.models import (
    AnalysisProvenance,
    EpisodeAnalysis,
    Fixture,
    MatchCoverage,
    Transcript,
)
from motd.squads import SquadError, SquadIndex

if TYPE_CHECKING:
    from anthropic.types import OutputConfigParam, TextBlockParam

logger = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high", "xhigh", "max"]
CacheTtl = Literal["5m", "1h"]

DEFAULT_MODEL = "claude-opus-5"
# Reading 80 minutes of transcript for boundaries is the kind of long analysis
# where effort matters more than model choice; `high` stopped a third of the way in.
DEFAULT_EFFORT: Effort = "xhigh"
# Every match after the first reads the transcript from cache, so the write is paid
# once per episode rather than once per call. 1h only helps when iterating.
DEFAULT_CACHE_TTL: CacheTtl = "5m"
PROMPT_VERSION = "5"
# The answer is a few hundred tokens, but thinking is billed against this too and a
# match with a fuzzy boundary can spend thousands working it out.
MAX_TOKENS = 16000

# Post-match interviews fall inside the highlights run rather than standing alone.
SEGMENT_KEYS = ("studio_intro", "highlights", "studio_analysis")

# A handover quote is checked when there is one, so it has to be long enough that
# matching it means something. Round-up flashes have no handover at all.
MIN_QUOTE_CHARS = 15

# Two calls placing the same boundary disagree by a few seconds after a clean handover
# and by more in the round-up, where matches pass in flashes of a second or two and the
# subtitle cues themselves overlap. Drift is a property of the boundary, not of the
# packages either side, so it does not scale with their length. Whether a span is the
# right match at all is the squad check's job, not this one's.
MAX_BOUNDARY_DRIFT_SECONDS = 20

# Backstop for timings that are individually well-formed but collectively wrong. An
# episode is match packages nearly end to end — titles, the table and trailers are the
# only gaps — so a real running order clears this comfortably.
MIN_TIMELINE_SHARE = 0.4


class AnalysisError(Exception):
    """Raised when analysis fails."""


@dataclass(frozen=True, slots=True)
class Prompt:
    """A prompt split at its cache boundary.

    `context` is the episode and `task` is the one match being located, so the whole
    transcript is written to cache once and read back by every match after the first.
    """

    context: str
    task: str

    def joined(self) -> str:
        return f"{self.context}\n\n{self.task}"


@dataclass(frozen=True, slots=True)
class LlmResult:
    """A backend's response, plus what it cost and which model produced it."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_written: int | None = None
    cache_read: int | None = None


@runtime_checkable
class LlmBackend(Protocol):
    """Protocol for schema-constrained LLM backends."""

    def __call__(self, prompt: Prompt, schema: dict[str, Any]) -> LlmResult:
        """Send a prompt and return a response conforming to the JSON schema."""
        ...


def anthropic_backend(
    model: str = DEFAULT_MODEL,
    effort: Effort = DEFAULT_EFFORT,
    cache_ttl: CacheTtl | None = DEFAULT_CACHE_TTL,
) -> LlmBackend:
    """Backend factory — the Claude API with the response shape pinned to `schema`."""

    def backend(prompt: Prompt, schema: dict[str, Any]) -> LlmResult:
        return _call_claude(prompt, schema, model, effort, cache_ttl)

    return backend


def _content_blocks(prompt: Prompt, cache_ttl: CacheTtl | None) -> list[TextBlockParam]:
    context: TextBlockParam = {"type": "text", "text": prompt.context}
    if cache_ttl:
        context["cache_control"] = {"type": "ephemeral", "ttl": cache_ttl}
    return [context, {"type": "text", "text": prompt.task}]


def _call_claude(
    prompt: Prompt,
    schema: dict[str, Any],
    model: str,
    effort: Effort,
    cache_ttl: CacheTtl | None,
) -> LlmResult:
    import anthropic

    output_config: OutputConfigParam = {
        "effort": effort,
        "format": {"type": "json_schema", "schema": schema},
    }
    client = anthropic.Anthropic()
    try:
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config=output_config,
            messages=[{"role": "user", "content": _content_blocks(prompt, cache_ttl)}],
        ) as stream:
            response = stream.get_final_message()
    except anthropic.APIError as exc:
        raise AnalysisError(f"Claude API call failed: {exc}") from exc

    if response.stop_reason == "refusal":
        raise AnalysisError(f"Claude declined the request: {response.stop_details}")

    if response.stop_reason == "max_tokens":
        raise AnalysisError(
            f"Claude hit the {MAX_TOKENS}-token ceiling and the reply is truncated. "
            f"Raise MAX_TOKENS rather than trusting a partial answer."
        )

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise AnalysisError(f"Claude returned no text block (stop_reason={response.stop_reason})")

    return LlmResult(
        text=text,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_written=response.usage.cache_creation_input_tokens,
        cache_read=response.usage.cache_read_input_tokens,
    )


def fixture_label(fixture: Fixture) -> str:
    """How a match is named to the model, and in every error it raises."""
    return f"{fixture.date} {fixture.home_team} v {fixture.away_team}"


def analyse(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
    *,
    squads: SquadIndex | None = None,
    backend: LlmBackend | None = None,
) -> EpisodeAnalysis:
    """Locate every candidate match in the episode and order them by when they aired.

    One call per match: a single call asked to produce every match at once collapses to
    one entry or none, whatever shape the answer is given, while the same model locates
    each match correctly when that is the whole question.

    Args:
        transcript: Episode transcript with timestamped segments.
        candidates: Fixtures the episode showed — see `fixtures.candidates_for_broadcast`.
        episode_id: Episode identifier (format: motd_YYYY-YY_YYYY-MM-DD).
        squads: Squad lookup for checking spans. Defaults to the season's squads file.
        backend: LLM backend. Defaults to the Claude API.

    Returns:
        Validated EpisodeAnalysis.

    Raises:
        AnalysisError: If any match cannot be located, its span does not name either
            club, or the located matches do not add up to a coherent episode.
    """
    if backend is None:
        backend = anthropic_backend()

    if not candidates:
        raise AnalysisError(f"No candidate fixtures for {episode_id}")

    try:
        ep = Episode.from_id(episode_id)
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc

    if squads is None:
        try:
            squads = SquadIndex.load(ep.season)
        except SquadError as exc:
            raise AnalysisError(str(exc)) from exc

    labels = [fixture_label(f) for f in candidates]
    if len(set(labels)) != len(labels):
        raise AnalysisError(f"Candidate fixtures produce duplicate labels: {labels}")

    schema = _build_schema()
    context = _build_context(transcript, candidates, episode_id, ep.broadcast_date, ep.season)
    haystack = _normalise(" ".join(seg.text for seg in transcript.segments))

    logger.info(
        "Analysing %s (%d segments, %d matches to locate)",
        episode_id, len(transcript.segments), len(candidates),
    )

    located = []
    model, input_tokens, output_tokens = "", 0, 0
    for n, fixture in enumerate(candidates, 1):
        label = fixture_label(fixture)
        prompt = Prompt(context=context, task=_build_task(fixture))
        result = backend(prompt, schema)
        model = result.model
        input_tokens += result.input_tokens or 0
        output_tokens += result.output_tokens or 0
        logger.info(
            "  %d/%d %s — %s output tokens (cache: %s written, %s read)",
            n, len(candidates), label, result.output_tokens,
            result.cache_written, result.cache_read,
        )
        located.append(_resolve_location(_parse_response(result.text), fixture, haystack))

    matches = _in_broadcast_order(located)
    _assert_highlights_do_not_overlap(matches, labels)
    _assert_spans_name_the_clubs(
        matches, {f.fpl_code: f for f in candidates}, transcript, squads
    )
    _assert_episode_is_accounted_for(matches, transcript, episode_id)

    gameweeks = {f.gameweek for f in candidates if f.gameweek is not None}
    try:
        analysis = EpisodeAnalysis(
            episode_id=episode_id,
            broadcast_date=ep.broadcast_date,
            season=ep.season,
            gameweek=gameweeks.pop() if len(gameweeks) == 1 else None,
            matches=matches,
            provenance=AnalysisProvenance(
                model=model,
                prompt_version=PROMPT_VERSION,
                analysed_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                candidate_fpl_codes=[f.fpl_code for f in candidates],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )
    except ValidationError as exc:
        raise AnalysisError(f"LLM response failed validation: {exc}") from exc

    logger.info("Analysis complete: %d matches in running order", len(analysis.matches))
    return analysis


def _build_schema() -> dict[str, Any]:
    """JSON schema for one match's location. The same every call, so it compiles once.

    Absence is an empty string, never null: structured outputs cap a schema at 16
    union-typed parameters, and nothing here needs to distinguish null from empty.
    """
    segment_span = {
        "type": "object",
        "properties": {
            "start": {"type": "string"},
            "end": {"type": "string"},
        },
        "required": ["start", "end"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        # Property order is generation order, so the quote is written before the timings
        # it anchors: the model finds the handover in the transcript, then times around it.
        "properties": {
            "handover": {"type": "string"},
            **dict.fromkeys(SEGMENT_KEYS, segment_span),
            "notes": {"type": "string"},
        },
        "required": ["handover", *SEGMENT_KEYS, "notes"],
        "additionalProperties": False,
    }


def _build_context(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> str:
    """The half that is identical for every match, and so is read from cache."""
    transcript_lines = []
    previous_speaker = None
    for seg in transcript.segments:
        mm_start = int(seg.start) // 60
        ss_start = int(seg.start) % 60
        # Only the change carries information; repeating the marker every line
        # would trade a tenth of the prompt for nothing.
        marker = ""
        if seg.speaker and seg.speaker != previous_speaker:
            marker = f"<speaker {seg.speaker}> "
        previous_speaker = seg.speaker
        transcript_lines.append(f"[{mm_start:02d}:{ss_start:02d}] {marker}{seg.text}")
    transcript_text = "\n".join(transcript_lines)

    candidate_lines = []
    for f in candidates:
        score = f"{f.score.home}-{f.score.away}" if f.score else "TBC"
        played = "played this day" if f.date == broadcast_date else f"played {f.date}"
        candidate_lines.append(f"- {fixture_label(f)} ({score}) at {f.venue} — {played}")
    candidates_text = "\n".join(candidate_lines)

    total_seconds = int(transcript.duration_seconds)
    runtime = f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

    return f"""## Episode
- Episode ID: {episode_id}
- Broadcast date: {broadcast_date}
- Season: {season}
- Running time: {runtime}

## Matches in this episode
Every one of these was shown. A match played on an earlier date appears either as a full
package held over, or as a brief round-up of action an earlier episode already covered —
both are coverage, and both are timed the same way.

{candidates_text}

## Transcript
`<speaker ...>` marks a change of speaker, taken from the colour the broadcaster gave
the subtitle. The colours carry no meaning across episodes, but within this one a change
marks a different voice — the handover from studio to commentary is usually one of them.

{transcript_text}"""


def _build_task(fixture: Fixture) -> str:
    """The half that names the one match to locate."""
    return f"""You are reading a BBC Match of the Day transcript to locate one match in it.

## The match

{fixture_label(fixture)} at {fixture.venue}

## Your task

Find where this match's coverage sits in the transcript and report only what you can
point at. Do not judge whether it belongs in the episode — it was shown, and the only
question is where.

- `handover` first: the words, copied verbatim from the transcript, where the studio
  hands over to this match. The handover takes no fixed form — it may credit the
  commentator, or simply point at the ground ("let's go to the Emirates") — so judge it
  by the shift from studio talk to match commentary, not by any particular phrase.
- `studio_intro`: pundits in the studio setting the match up, ending at that handover.
- `highlights`: match action with commentary, including any pitchside interviews.
- `studio_analysis`: pundits discussing the match afterwards, until they move on.

Timestamps are MM:SS from the start of the episode. Use empty strings for a boundary you
cannot place, and for both ends of a segment that is absent. Naming a club in transfer
talk, league-table discussion or a player's history is not coverage of this match — the
round-up of a match played on an earlier date is, however brief.

Use `notes` only for something that would otherwise be misread — an interrupted segment,
a match shown in two parts. Leave it empty when there is nothing to flag."""


def _build_prompt(
    transcript: Transcript,
    candidates: list[Fixture],
    fixture: Fixture,
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> Prompt:
    """One match's prompt, both halves — what `analyse` sends per call."""
    return Prompt(
        context=_build_context(transcript, candidates, episode_id, broadcast_date, season),
        task=_build_task(fixture),
    )


def _parse_response(response_text: str) -> dict[str, Any]:
    """The model's reply as a dict, with a schema violation surfaced as AnalysisError."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"Failed to parse LLM response as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AnalysisError(f"Expected a JSON object, got {type(data).__name__}")
    return data


def _normalise(text: str) -> str:
    """Lowercase alphanumerics and single spaces, so a quote survives punctuation drift."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _resolve_location(
    data: dict[str, Any], fixture: Fixture, haystack: str
) -> tuple[MatchCoverage, float]:
    """One match's timings, with its handover quote checked against the transcript.

    Returns the coverage alongside the second its highlights start, which is what puts
    it in the running order — the model is never asked for a position. Every disagreement raises:
    a match that cannot be located is a broken run, not an editorial judgement, and a
    half-filled analysis is worse than none because the transcript cannot be re-fetched
    once iPlayer drops the episode.
    """
    label = fixture_label(fixture)

    segments = {}
    for key in SEGMENT_KEYS:
        span = data.get(key) or {}
        if not isinstance(span, dict):
            raise AnalysisError(f"{label}: malformed {key} {span!r}")
        start, end = span.get("start") or None, span.get("end") or None
        if start or end:
            segments[key] = {"start": start, "end": end}
    if not segments:
        raise AnalysisError(
            f"{label}: not found in the episode. Every match in the candidate window is "
            f"shown, so this is a failed run rather than a match that did not air."
        )

    # Checked when offered, never demanded: the round-up runs matches back to back and
    # the studio hands over to none of them. The squad check is what holds every match
    # to its timings — see `_assert_spans_name_the_clubs`.
    quote = _normalise(str(data.get("handover", "")))
    if len(quote) >= MIN_QUOTE_CHARS and quote not in haystack:
        raise AnalysisError(
            f"{label}: handover quote is not in the transcript, so the timings around "
            f"it are not evidence — {quote!r}"
        )

    # Highlights first, because that is when the match is on screen. A studio intro can
    # be shared — the round-up introduces six matches once — so the earliest segment of
    # any kind ties every one of them together and loses the order between them.
    start = next(
        (
            seconds
            for key in ("highlights", "studio_intro", "studio_analysis")
            if (span := segments.get(key))
            and span["start"]
            and (seconds := _timestamp_seconds(span["start"])) is not None
        ),
        None,
    )
    if start is None:
        raise AnalysisError(f"{label}: located but carries no usable start time")

    try:
        coverage = MatchCoverage.model_validate({
            "fpl_code": fixture.fpl_code,
            # Overwritten once every match is in; the model never emits a position.
            "order": 1,
            "segments": segments,
            "notes": data.get("notes") or None,
            "handover": data.get("handover") or None,
        })
    except ValidationError as exc:
        raise AnalysisError(f"{label}: malformed coverage: {exc}") from exc

    return coverage, start


def _in_broadcast_order(located: list[tuple[MatchCoverage, float]]) -> list[MatchCoverage]:
    """Rank the matches by when they aired. Derived, so it cannot have gaps or repeats."""
    return [
        match.model_copy(update={"order": position})
        for position, (match, _) in enumerate(sorted(located, key=lambda pair: pair[1]), 1)
    ]


def _timestamp_seconds(value: str) -> float | None:
    """Seconds from a MM:SS or HH:MM:SS timestamp, or None if it is not one."""
    parts = value.split(":")
    if not all(part.isdigit() for part in parts) or not 2 <= len(parts) <= 3:
        return None
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _span_seconds(match: MatchCoverage, key: str) -> tuple[float, float] | None:
    segment = match.segments.get(key)
    if not segment or not (segment.start and segment.end):
        return None
    start, end = _timestamp_seconds(segment.start), _timestamp_seconds(segment.end)
    if start is None or end is None or end <= start:
        return None
    return start, end


def _assert_highlights_do_not_overlap(matches: list[MatchCoverage], labels: list[str]) -> None:
    """Catch two matches claiming the same screen time.

    Each match is located by its own call, so nothing but this stops two of them landing
    on one package. Abutting is normal — one match's analysis runs into the next one's
    intro, and the round-up hands from one flash to the next — so only an overlap past
    what two independent calls drift by is an error.
    """
    # Sorted by highlights, not by running order: a match is placed in the order by its
    # earliest segment of any kind, so the two sequences are not always the same.
    timed = sorted(
        ((span, m) for m in matches if (span := _span_seconds(m, "highlights"))),
        key=lambda pair: pair[0],
    )
    for (first_span, first), (second_span, second) in zip(timed, timed[1:], strict=False):
        overlap = min(first_span[1], second_span[1]) - second_span[0]
        if overlap > MAX_BOUNDARY_DRIFT_SECONDS:
            raise AnalysisError(
                f"Two matches claim overlapping highlights: fixture {first.fpl_code} "
                f"({first.segments['highlights'].start}-{first.segments['highlights'].end}) "
                f"and fixture {second.fpl_code} "
                f"({second.segments['highlights'].start}-{second.segments['highlights'].end}). "
                f"Candidates were {labels}."
            )


def _text_between(transcript: Transcript, span: tuple[float, float]) -> str:
    start, end = span
    return " ".join(seg.text for seg in transcript.segments if start <= seg.start <= end)


def _assert_spans_name_the_clubs(
    matches: list[MatchCoverage],
    by_code: dict[int, Fixture],
    transcript: Transcript,
    squads: SquadIndex,
) -> None:
    """Check each claimed span against who is actually named in it.

    A quote only proves a line exists somewhere in the transcript; this proves the
    timings point at the right match, which is the thing being claimed. Players belong
    to one club, so commentary over a match names that match — and it is the only
    separator the round-up has.
    """
    for match in matches:
        fixture = by_code[match.fpl_code]
        span = _span_seconds(match, "highlights") or _span_seconds(match, "studio_analysis")
        if span is None:
            continue
        named = squads.clubs_named_in(_text_between(transcript, span))
        expected = {fixture.home_code, fixture.away_code}
        if not named & expected:
            raise AnalysisError(
                f"{fixture_label(fixture)}: no {fixture.home_code} or {fixture.away_code} "
                f"player is named between {match.segments['highlights'].start} and "
                f"{match.segments['highlights'].end}"
                + (f", but {', '.join(sorted(named))} are" if named else "")
                + " — the span is not this match."
            )


def _timeline_share(
    matches: list[MatchCoverage], bounds: tuple[float, float]
) -> float | None:
    """Fraction of the episode the running order accounts for, or None if untimeable.

    Spans are clipped to `bounds` before being counted, so a studio intro that starts
    on the trailer cannot explain more of the show than the show contains.
    """
    lower, upper = bounds
    accountable_seconds = upper - lower
    if accountable_seconds <= 0:
        return None

    spans = []
    for match in matches:
        for key in SEGMENT_KEYS:
            span = _span_seconds(match, key)
            if not span:
                continue
            start, end = max(span[0], lower), min(span[1], upper)
            if end > start:
                spans.append((start, end))
    if not spans:
        return None

    # Segments of one match abut and a round-up can sit inside a fuller package, so the
    # union is the only honest measure of how much screen time was accounted for.
    covered = 0.0
    ordered = sorted(spans)
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start > current_end:
            covered += current_end - current_start
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    covered += current_end - current_start

    return covered / accountable_seconds


def _content_bounds(transcript: Transcript, episode_id: str) -> tuple[float, float]:
    """The stretch of the recording matches could have been given, as (start, end).

    BBC marks where the programme proper starts and ends, so the opening trailer and
    the end credits count towards neither the airtime accounted for nor the airtime
    available. Falls back to the whole recording when the metadata has not been fetched.
    """
    from motd.programme import ProgrammeError
    from motd.programme import load as load_metadata

    try:
        metadata = load_metadata(episode_id)
    except ProgrammeError:
        metadata = None
    if metadata is None or metadata.content_window is None:
        return 0.0, transcript.duration_seconds

    window = metadata.content_window
    logger.info(
        "%s: measuring against BBC's content window (%.0fs-%.0fs of %.0fs)",
        episode_id, window.start_seconds, window.end_seconds, transcript.duration_seconds,
    )
    return window.start_seconds, window.end_seconds


def _assert_episode_is_accounted_for(
    matches: list[MatchCoverage], transcript: Transcript, episode_id: str
) -> None:
    """Reject timings that are individually plausible but leave the episode unexplained."""
    share = _timeline_share(matches, _content_bounds(transcript, episode_id))
    if share is None:
        logger.warning("%s: running order carries no usable timings to check", episode_id)
        return

    logger.info("%s: running order accounts for %.0f%% of the episode", episode_id, share * 100)
    if share < MIN_TIMELINE_SHARE:
        raise AnalysisError(
            f"{episode_id}: {len(matches)} matches account for only {share:.0%} of the "
            f"episode, below the {MIN_TIMELINE_SHARE:.0%} floor — the timings do not add "
            f"up to a whole show. Re-run before trusting it."
        )
