"""Pydantic data contracts for the MOTD analysis pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech."""

    start: float = Field(ge=0.0, description="Start time in seconds")
    end: float = Field(ge=0.0, description="End time in seconds")
    text: str = Field(min_length=1, description="Transcribed text")
    speaker: str | None = Field(
        default=None,
        description="Speaker marker where the source distinguishes speakers. "
        "Distinguishes speakers within an episode only — not a stable identity.",
    )

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
    """A Premier League fixture.

    `fpl_code` is the join key, not `match_id`: match_id embeds the date, so a
    postponed fixture silently becomes a different id, while the FPL code follows
    the fixture through rescheduling.
    """

    fpl_code: int
    match_id: str
    date: str
    home_team: str
    away_team: str
    home_code: str
    away_code: str
    venue: str
    score: Score | None = None
    gameweek: int | None = Field(default=None, gt=0)
    kickoff: str | None = None
    played: bool = False


class Segment(BaseModel):
    """A timed segment within an episode (start/end can be null if unclear)."""

    start: str | None = None
    end: str | None = None


class MatchCoverage(BaseModel):
    """A match that got screen time in an episode.

    Carries no team names or scores — those live on the Fixture that `fpl_code`
    resolves to. Whether this was a full package or a brief round-up of a game
    already covered elsewhere is derived at analysis time from duration and
    earlier episodes, not recorded here.
    """

    fpl_code: int
    order: int = Field(gt=0, description="Position in the episode's sequence (1-indexed)")
    segments: dict[str, Segment] = Field(default_factory=dict)
    notes: str | None = None


class AnalysisProvenance(BaseModel):
    """What produced an analysis, and what it was allowed to choose from.

    `candidate_fpl_codes` is the one input that cannot be reconstructed later:
    re-syncing fixtures or changing the candidate window would yield a different
    list than the run actually saw.
    """

    model: str
    prompt_version: str
    analysed_at: str
    candidate_fpl_codes: list[int] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    # The model's sweep of the transcript, kept so a run's coverage can be audited
    # after the fact — it names the trails and breaks that leave gaps between matches.
    walkthrough: str | None = None


class EpisodeAnalysis(BaseModel):
    """Running order and segment timings for one MOTD episode."""

    episode_id: str
    broadcast_date: str
    season: str
    gameweek: int | None = Field(default=None, gt=0)
    matches: list[MatchCoverage] = Field(default_factory=list)
    provenance: AnalysisProvenance | None = None

    @model_validator(mode="after")
    def orders_are_a_contiguous_sequence(self) -> EpisodeAnalysis:
        codes = [m.fpl_code for m in self.matches]
        if len(set(codes)) != len(codes):
            raise ValueError(f"Duplicate fixtures in running order: {codes}")
        orders = sorted(m.order for m in self.matches)
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(f"Running order must be 1..{len(orders)}, got {orders}")
        return self
