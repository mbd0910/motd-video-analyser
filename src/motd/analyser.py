"""Analyser module — produces structured episode analysis from transcript + fixtures.

Constructs a prompt from Transcript and fixture data, invokes Claude
via `claude -p`, and parses the response into a validated EpisodeAnalysis.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess

from pydantic import ValidationError

from motd.models import EpisodeAnalysis, Fixture, MatchCoverage, Transcript

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Raised when analysis fails."""


def analyse(
    transcript: Transcript,
    fixtures: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> EpisodeAnalysis:
    """Analyse a transcript against fixtures and return structured analysis.

    Args:
        transcript: Episode transcript with timestamped segments.
        fixtures: Fixtures for the episode's broadcast date.
        episode_id: Episode identifier.
        broadcast_date: Broadcast date (YYYY-MM-DD).
        season: Season identifier (e.g. "2025-26").

    Returns:
        Validated EpisodeAnalysis.

    Raises:
        AnalysisError: If Claude invocation or response parsing fails.
    """
    prompt = _build_prompt(transcript, fixtures, episode_id, broadcast_date, season)
    logger.info("Analysing %s (%d segments, %d fixtures)",
                episode_id, len(transcript.segments), len(fixtures))

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AnalysisError(
            f"Claude analysis failed for {episode_id}: {e.stderr or e}"
        ) from e

    response_text = result.stdout.strip()
    logger.debug("Claude response length: %d chars", len(response_text))

    analysis = _parse_response(response_text, episode_id, broadcast_date, season)
    logger.info("Analysis complete: %d matches identified", len(analysis.matches))
    return analysis


def _build_prompt(
    transcript: Transcript,
    fixtures: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> str:
    """Build the analysis prompt from transcript and fixture data.

    Args:
        transcript: Episode transcript.
        fixtures: Fixtures for the broadcast date.
        episode_id: Episode identifier.
        broadcast_date: Broadcast date.
        season: Season identifier.

    Returns:
        Complete prompt string for Claude.
    """
    # Format transcript with timestamps
    transcript_lines = []
    for seg in transcript.segments:
        mm_start = int(seg.start) // 60
        ss_start = int(seg.start) % 60
        transcript_lines.append(f"[{mm_start:02d}:{ss_start:02d}] {seg.text}")
    transcript_text = "\n".join(transcript_lines)

    # Format fixture data
    fixture_lines = []
    for f in fixtures:
        score_str = f"{f.score.home}-{f.score.away}" if f.score else "TBC"
        fixture_lines.append(
            f"- {f.home_team} vs {f.away_team} ({score_str}) at {f.venue}"
        )
    fixtures_text = "\n".join(fixture_lines)

    return f"""You are analysing a BBC Match of the Day episode transcript to identify which \
Premier League matches were covered, in what order, and the timing of each segment.

## Episode Details
- Episode ID: {episode_id}
- Broadcast date: {broadcast_date}
- Season: {season}

## Fixtures played on {broadcast_date}
{fixtures_text}

## Transcript
{transcript_text}

## Your Task

Analyse the transcript and identify:
1. Which matches from the fixture list were covered in this episode
2. The running order (which match was shown first, second, etc.)
3. The timestamp boundaries for each segment type

For each match covered, identify these segment types where present:
- **studio_intro**: When pundits begin discussing the upcoming match, ends at commentator credit
- **lineups**: After commentator credit, team formations shown
- **highlights**: Match action with commentary
- **post_match_interviews**: Pitchside interviews with players/managers
- **studio_analysis**: Pundits return to discuss the match

## Output Format

Return ONLY valid JSON (no markdown fences, no explanation) in this exact structure:

{{
  "matches": [
    {{
      "order": 1,
      "home_team": "Team Name",
      "away_team": "Team Name",
      "venue": "Stadium Name",
      "score": {{"home": 0, "away": 0}},
      "segments": {{
        "studio_intro": {{"start": "MM:SS", "end": "MM:SS"}},
        "highlights": {{"start": "MM:SS", "end": "MM:SS"}},
        "studio_analysis": {{"start": "MM:SS", "end": "MM:SS"}}
      }},
      "notes": null
    }}
  ]
}}

Timestamps must be in MM:SS format. Use null for start or end if unclear.
Only include matches that were actually covered in the episode.
Order must be sequential starting from 1."""


def _parse_response(
    response_text: str,
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> EpisodeAnalysis:
    """Parse Claude's JSON response into a validated EpisodeAnalysis.

    Args:
        response_text: Raw text response from Claude.
        episode_id: Episode identifier.
        broadcast_date: Broadcast date.
        season: Season identifier.

    Returns:
        Validated EpisodeAnalysis.

    Raises:
        AnalysisError: If the response cannot be parsed as valid JSON or
            doesn't match the expected schema.
    """
    # Strip markdown fences if present
    cleaned = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AnalysisError(f"Failed to parse Claude response as JSON: {e}") from e

    # Build EpisodeAnalysis from parsed data
    try:
        matches_data = data.get("matches", [])
        if not isinstance(matches_data, list):
            raise AnalysisError(
                f"Expected 'matches' to be a list, got {type(matches_data).__name__}"
            )
        matches = [MatchCoverage.model_validate(m) for m in matches_data]

        return EpisodeAnalysis(
            episode_id=episode_id,
            broadcast_date=broadcast_date,
            season=season,
            matches=matches,
        )
    except ValidationError as e:
        raise AnalysisError(
            f"Claude response doesn't match expected schema: {e}"
        ) from e
