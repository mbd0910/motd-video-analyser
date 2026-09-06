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
    # The transcript line the studio hands over on, checked against the transcript
    # rather than trusted: it is what makes the timings evidence instead of a claim.
    handover: str | None = None


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
    # Only on analyses from prompt version 3 and earlier, where one call produced the
    # whole running order and its sweep of the transcript was kept to audit coverage.
    walkthrough: str | None = None


class Credit(BaseModel):
    """One role/contributor pair as BBC publishes it.

    Kept in BBC's own vocabulary rather than mapped down to the roster's: their
    "Expert" is only approximately a pundit, and roles the roster has no slot for
    — Editor above all, which changes week to week — are the point of storing this.
    """

    role: str = Field(min_length=1)
    name: str = Field(min_length=1)


class ContentWindow(BaseModel):
    """Where the programme proper sits inside the recording.

    An episode file opens on a trailer and closes on end credits, neither of which
    is airtime any match could have been given.
    """

    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(gt=0.0)

    @model_validator(mode="after")
    def window_runs_forwards(self) -> ContentWindow:
        if self.end_seconds <= self.start_seconds:
            msg = f"end ({self.end_seconds}) must be > start ({self.start_seconds})"
            raise ValueError(msg)
        return self

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class EpisodeMetadata(BaseModel):
    """BBC's own record of an episode, stored as published.

    Committed rather than cached, though `/programmes` serves it indefinitely: it is
    the provenance for a derived roster, and a claim about editorial bias should carry
    the broadcaster's own billing alongside it.
    """

    episode_id: str
    broadcast_date: str
    season: str
    programme_pid: str
    # What yt-dlp actually downloads: the episode pid addresses the programme, this
    # addresses the recording, and only this one appears in the media selection.
    version_pid: str
    title: str
    subtitle: str
    editorial_title: str | None = None
    first_broadcast: str
    duration_seconds: int = Field(gt=0)
    content_window: ContentWindow | None = None
    synopsis_short: str = ""
    synopsis_medium: str = ""
    synopsis_long: str = ""
    synopsis_editorial: str | None = None
    credits: list[Credit] = Field(default_factory=list)
    available_until: str | None = None
    image_pid: str | None = None
    fetched_at: str

    def named_for_role(self, role: str) -> list[str]:
        """Everyone credited in a role, in the order BBC lists them."""
        return [credit.name for credit in self.credits if credit.role.lower() == role.lower()]


class RosterOverride(BaseModel):
    """The hand-entered half of a roster: what BBC's credits do not carry.

    Guests are the standing case — a visiting manager is on screen but never
    credited — and the rest are escape hatches for a credit that is wrong or absent.
    """

    presenter: str | None = Field(default=None, min_length=1)
    pundits: list[str] | None = None
    guests: list[str] = Field(default_factory=list)
    editor: str | None = Field(default=None, min_length=1)


class EpisodeRoster(BaseModel):
    """Who was on screen in the studio for an episode.

    Derived from BBC's credits and overlaid with `data/rosters/`, which supplies the
    guests they never credit. Nothing here is recoverable from a transcript: the
    subtitles carry a four-colour speaker palette but no names.
    """

    presenter: str = Field(min_length=1)
    pundits: list[str] = Field(default_factory=list)
    guests: list[str] = Field(default_factory=list)
    # Not on screen, but the person who chose the running order — the variable a
    # study of editorial bias would most want to test against.
    editor: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def people_are_named_once(self) -> EpisodeRoster:
        people = [self.presenter, *self.pundits, *self.guests]
        if any(not name.strip() for name in people):
            raise ValueError(f"Blank name in roster: {people}")
        if len(set(people)) != len(people):
            raise ValueError(f"Same person listed twice: {people}")
        return self


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


class PublishedEpisode(EpisodeAnalysis):
    """The wire format: an analysis with its episode metadata joined in.

    A separate type so `data/analysis/` stays purely what the model produced and
    `data/rosters/` stays purely hand-entered — the two meet only on the way out,
    which lets a roster be corrected by re-publishing rather than re-analysing.
    """

    roster: EpisodeRoster | None = None

    @staticmethod
    def compose(
        analysis: EpisodeAnalysis, roster: EpisodeRoster | None
    ) -> PublishedEpisode:
        return PublishedEpisode(**analysis.model_dump(), roster=roster)
