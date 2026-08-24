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
from typing import Any, Protocol, runtime_checkable

from pydantic import ValidationError

from motd.episode import Episode
from motd.models import (
    AnalysisProvenance,
    EpisodeAnalysis,
    Fixture,
    MatchCoverage,
    Transcript,
)

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5"
PROMPT_VERSION = "2"
MAX_TOKENS = 16000

# Post-match interviews fall inside the highlights run rather than standing alone.
SEGMENT_KEYS = ("studio_intro", "highlights", "studio_analysis")


class AnalysisError(Exception):
    """Raised when analysis fails."""


@dataclass(frozen=True, slots=True)
class LlmResult:
    """A backend's response, plus what it cost and which model produced it."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class LlmBackend(Protocol):
    """Protocol for schema-constrained LLM backends."""

    def __call__(self, prompt: str, schema: dict[str, Any]) -> LlmResult:
        """Send a prompt and return a response conforming to the JSON schema."""
        ...


def _anthropic_backend(prompt: str, schema: dict[str, Any]) -> LlmResult:
    """Default backend — the Claude API with the response shape pinned to `schema`."""
    import anthropic

    client = anthropic.Anthropic()
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[{"role": "user", "content": prompt}],
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
        backend = _anthropic_backend

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
        "properties": {
            "running_order": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "match": {"type": "string", "enum": labels},
                        "order": {"type": "integer", "minimum": 1},
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
        "required": ["running_order"],
        "additionalProperties": False,
    }


def _build_prompt(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> str:
    """Build the analysis prompt from transcript and candidate fixtures."""
    transcript_lines = []
    for seg in transcript.segments:
        mm_start = int(seg.start) // 60
        ss_start = int(seg.start) % 60
        transcript_lines.append(f"[{mm_start:02d}:{ss_start:02d}] {seg.text}")
    transcript_text = "\n".join(transcript_lines)

    candidate_lines = []
    for f in candidates:
        score = f"{f.score.home}-{f.score.away}" if f.score else "TBC"
        played = "played this day" if f.date == broadcast_date else f"played {f.date}"
        candidate_lines.append(f'- "{fixture_label(f)}" ({score}) at {f.venue} — {played}')
    candidates_text = "\n".join(candidate_lines)

    return f"""You are reading a BBC Match of the Day transcript to record which matches got \
screen time, in what order, and when.

## Episode
- Episode ID: {episode_id}
- Broadcast date: {broadcast_date}
- Season: {season}

## Candidate matches
These are every fixture in the gameweek that had been played by the broadcast date.
The episode will not have shown all of them. Some were played on an earlier date:
those may appear as a full package held over to this episode, or as a brief round-up
of action an earlier episode already covered — record both the same way.

{candidates_text}

## Transcript
{transcript_text}

## Your task

Return the matches that got screen time in this episode, in the order they appeared.

- Include a match only if the episode shows footage of it. Naming a club in transfer
  talk, league-table discussion or a player's history is not coverage.
- `match` must be copied exactly from the candidate list above.
- `order` is the position in this episode's sequence, starting at 1, with no gaps.
  A round-up of earlier matches takes its real place in that sequence.
- Timestamps are MM:SS from the start of the episode. Use null for a boundary you
  cannot place, and null for both ends of a segment that is absent.

Segments to time where present:
- `studio_intro`: pundits setting up the match, ending at the commentator credit
- `highlights`: match action with commentary, including any pitchside interviews
- `studio_analysis`: pundits discussing the match afterwards

Use `notes` only for something that would otherwise be misread — an interrupted
segment, a match shown in two parts. Leave it null when there is nothing to flag."""


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
