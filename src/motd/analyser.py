"""Analyser module — extracts running order and segment timings from a transcript.

The model never invents an identifier. It is handed the gameweek's fixtures as
an enumerated candidate list and constrained by a JSON schema to echo back one of
those exact labels, which this module resolves to a fixture in code. Its only
judgements are which candidates got screen time, in what order, and when.
"""

from __future__ import annotations

import json
import logging
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

if TYPE_CHECKING:
    from anthropic.types import OutputConfigParam, TextBlockParam

logger = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high", "xhigh", "max"]
CacheTtl = Literal["5m", "1h"]

DEFAULT_MODEL = "claude-opus-5"
# Reading 80 minutes of transcript for boundaries is the kind of long analysis
# where effort matters more than model choice; `high` stopped a third of the way in.
DEFAULT_EFFORT: Effort = "xhigh"
# Writing a 5m cache costs 1.25x input against 2x for 1h, so it is the cheap default
# for a pipeline that calls once per episode. Use 1h when iterating on one episode.
DEFAULT_CACHE_TTL: CacheTtl = "5m"
PROMPT_VERSION = "3"
MAX_TOKENS = 16000

# Post-match interviews fall inside the highlights run rather than standing alone.
SEGMENT_KEYS = ("studio_intro", "highlights", "studio_analysis")


class AnalysisError(Exception):
    """Raised when analysis fails."""


@dataclass(frozen=True, slots=True)
class Prompt:
    """A prompt split at its cache boundary.

    `context` is everything about one episode and `task` is the instructions. The
    split is that way round because iteration holds the episode fixed and rewrites
    the instructions — so the transcript is the reusable half, even though across a
    season it is the half that always changes.
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
    """The exact string the model picks from, and the key it is resolved by."""
    return f"{fixture.date} {fixture.home_team} v {fixture.away_team}"


def analyse(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
    *,
    backend: LlmBackend | None = None,
) -> EpisodeAnalysis:
    """Extract running order and segment timings for an episode.

    Args:
        transcript: Episode transcript with timestamped segments.
        candidates: Fixtures the episode could have shown — see
            `fixtures.candidates_for_broadcast`.
        episode_id: Episode identifier (format: motd_YYYY-YY_YYYY-MM-DD).
        backend: LLM backend. Defaults to the Claude API.

    Returns:
        Validated EpisodeAnalysis.

    Raises:
        AnalysisError: If episode_id parsing, LLM invocation, or response
            resolution fails.
    """
    if backend is None:
        backend = anthropic_backend()

    if not candidates:
        raise AnalysisError(f"No candidate fixtures for {episode_id}")

    try:
        ep = Episode.from_id(episode_id)
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc

    by_label = {fixture_label(f): f for f in candidates}
    if len(by_label) != len(candidates):
        raise AnalysisError(f"Candidate fixtures produce duplicate labels: {candidates}")

    prompt = _build_prompt(transcript, candidates, episode_id, ep.broadcast_date, ep.season)
    schema = _build_schema(sorted(by_label))
    logger.info(
        "Analysing %s (%d segments, %d candidate fixtures)",
        episode_id, len(transcript.segments), len(candidates),
    )

    result = backend(prompt, schema)
    logger.info(
        "%s returned %s output tokens for %s input (cache: %s written, %s read)",
        result.model, result.output_tokens, result.input_tokens,
        result.cache_written, result.cache_read,
    )
    matches = _resolve_matches(result.text, by_label)

    gameweeks = {f.gameweek for f in candidates if f.gameweek is not None}
    try:
        analysis = EpisodeAnalysis(
            episode_id=episode_id,
            broadcast_date=ep.broadcast_date,
            season=ep.season,
            gameweek=gameweeks.pop() if len(gameweeks) == 1 else None,
            matches=matches,
            provenance=AnalysisProvenance(
                model=result.model,
                prompt_version=PROMPT_VERSION,
                analysed_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                candidate_fpl_codes=[f.fpl_code for f in candidates],
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            ),
        )
    except ValidationError as exc:
        raise AnalysisError(f"LLM response failed validation: {exc}") from exc

    logger.info("Analysis complete: %d matches in running order", len(analysis.matches))
    return analysis


def _build_schema(labels: list[str]) -> dict[str, Any]:
    """JSON schema constraining every pick to one of the candidate labels."""
    segment_span = {
        "type": "object",
        "properties": {
            "start": {"type": ["string", "null"]},
            "end": {"type": ["string", "null"]},
        },
        "required": ["start", "end"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        # Property order is generation order: the walkthrough is emitted before the
        # array, so the array is written against a commitment already in the stream.
        # Reasoning cannot do this job — thinking does not constrain the answer block.
        "properties": {
            "walkthrough": {"type": "string"},
            "running_order": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "match": {"type": "string", "enum": labels},
                        # Structured outputs reject `minimum`; MatchCoverage and the
                        # contiguity check on EpisodeAnalysis enforce the range instead.
                        "order": {"type": "integer"},
                        "segments": {
                            "type": "object",
                            "properties": dict.fromkeys(SEGMENT_KEYS, segment_span),
                            "required": list(SEGMENT_KEYS),
                            "additionalProperties": False,
                        },
                        "notes": {"type": ["string", "null"]},
                    },
                    "required": ["match", "order", "segments", "notes"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["walkthrough", "running_order"],
        "additionalProperties": False,
    }


def _build_prompt(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> Prompt:
    """Build the analysis prompt from transcript and candidate fixtures."""
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
        candidate_lines.append(f'- "{fixture_label(f)}" ({score}) at {f.venue} — {played}')
    candidates_text = "\n".join(candidate_lines)

    total_seconds = int(transcript.duration_seconds)
    runtime = f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

    context = f"""## Episode
- Episode ID: {episode_id}
- Broadcast date: {broadcast_date}
- Season: {season}
- Running time: {runtime}

## Candidate matches
These are every fixture in the gameweek that had been played by the broadcast date.
The episode will not have shown all of them. Some were played on an earlier date:
those may appear as a full package held over to this episode, or as a brief round-up
of action an earlier episode already covered — record both the same way.

{candidates_text}

## Transcript
`<speaker ...>` marks a change of speaker, taken from the colour the broadcaster gave
the subtitle. The colours carry no meaning across episodes, but within this one a change
marks a different voice — the handover from studio to commentary is usually one of them.

{transcript_text}"""

    task = f"""You are reading a BBC Match of the Day transcript to record which matches got \
screen time, in what order, and when.

## Your task

Return the matches that got screen time in this episode, in the order they appeared.
An episode runs matches back to back for most of its {runtime}, so expect several — a
Saturday show typically carries five to seven. Fill the two fields in the order below.

**`walkthrough` first.** Sweep the transcript from 00:00 to {runtime} and write one line
per match: the two clubs, the minute the studio hands over, the minute the highlights end.
Reach the end of the running time before you stop. This field is working-out rather than
data — it is read to check the sweep was complete, then discarded.

**`running_order` second.** The same matches, in the same order, one entry each, timed as
below. Every match named in the walkthrough gets an entry.

- Include a match only if the episode shows footage of it. Naming a club in transfer
  talk, league-table discussion or a player's history is not coverage.
- `match` must be copied exactly from the candidate list above.
- `order` is the position in this episode's sequence, starting at 1, with no gaps.
  A round-up of earlier matches takes its real place in that sequence.
- Timestamps are MM:SS from the start of the episode. Use null for a boundary you
  cannot place, and null for both ends of a segment that is absent.

Segments to time where present:
- `studio_intro`: pundits in the studio setting up the match, ending where the programme
  hands over to the match itself. The handover takes no fixed form — it may credit the
  commentator, or simply point at the ground ("let's go to the Emirates") — so judge it by
  the shift from studio talk to match commentary, not by any particular phrase.
- `highlights`: match action with commentary, including any pitchside interviews
- `studio_analysis`: pundits discussing the match afterwards, until they move on

Use `notes` only for something that would otherwise be misread — an interrupted
segment, a match shown in two parts. Leave it null when there is nothing to flag."""

    return Prompt(context=context, task=task)


def _resolve_matches(response_text: str, by_label: dict[str, Fixture]) -> list[MatchCoverage]:
    """Map the model's label picks onto fixtures, rejecting anything unresolvable."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"Failed to parse LLM response as JSON: {exc}") from exc

    picks = data.get("running_order")
    if not isinstance(picks, list):
        raise AnalysisError(f"Expected 'running_order' to be a list, got {type(picks).__name__}")

    matches = []
    for pick in picks:
        label = pick.get("match")
        fixture = by_label.get(label)
        if fixture is None:
            raise AnalysisError(
                f"LLM returned {label!r}, which is not a candidate. "
                f"Candidates: {sorted(by_label)}"
            )
        segments = {
            key: span
            for key, span in (pick.get("segments") or {}).items()
            if span and (span.get("start") or span.get("end"))
        }
        try:
            matches.append(
                MatchCoverage.model_validate({
                    "fpl_code": fixture.fpl_code,
                    "order": pick.get("order"),
                    "segments": segments,
                    "notes": pick.get("notes"),
                })
            )
        except ValidationError as exc:
            raise AnalysisError(f"Malformed running order entry {pick}: {exc}") from exc

    return matches
