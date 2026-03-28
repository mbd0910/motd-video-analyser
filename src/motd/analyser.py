"""Analyser module — produces structured episode analysis from transcript + fixtures.

Constructs a prompt from Transcript and fixture data, invokes Claude,
and parses the response into a validated EpisodeAnalysis.
"""

from __future__ import annotations

from motd.models import EpisodeAnalysis, Fixture, Transcript


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
    """
    raise NotImplementedError("Analyser not yet implemented — see issue #20")
