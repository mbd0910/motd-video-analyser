"""Pydantic data contracts for the MOTD analysis pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech."""

    start: float = Field(ge=0.0, description="Start time in seconds")
    end: float = Field(ge=0.0, description="End time in seconds")
    text: str = Field(min_length=1, description="Transcribed text")

    @model_validator(mode="after")
    def end_after_start(self) -> TranscriptSegment:
        if self.end < self.start:
            msg = f"end ({self.end}) must be >= start ({self.start})"
            raise ValueError(msg)
        return self


class Transcript(BaseModel):
    """Complete transcript for an episode."""

    episode_id: str
    duration_seconds: float = Field(ge=0.0)
    segments: list[TranscriptSegment] = Field(default_factory=list)


class Score(BaseModel):
    """Final score for a match."""

    home: int = Field(ge=0)
    away: int = Field(ge=0)


class Fixture(BaseModel):
    """A Premier League fixture."""

    match_id: str
    date: str
    home_team: str
    away_team: str
    venue: str
    score: Score | None = None


class Segment(BaseModel):
    """A timed segment within an episode (start/end can be null if unclear)."""

    start: str | None = None
    end: str | None = None


class MatchCoverage(BaseModel):
    """Coverage data for a single match within an episode."""

    order: int = Field(gt=0, description="Running order position (1-indexed)")
    home_team: str
    away_team: str
    venue: str
    score: Score
    segments: dict[str, Segment] = Field(default_factory=dict)
    notes: str | None = None


class EpisodeAnalysis(BaseModel):
    """Complete analysis output for one MOTD episode."""

    episode_id: str
    broadcast_date: str
    season: str
    matches: list[MatchCoverage] = Field(default_factory=list)
