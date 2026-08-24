"""Pipeline orchestrator — sequences all stages of the MOTD analysis pipeline.

Stages: Download (optional) → Transcribe → Analyse → Publish
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from motd.cache import get_or_compute, load
from motd.episode import DEFAULT_CACHE_DIR, Episode
from motd.models import EpisodeAnalysis, Fixture, Transcript

logger = logging.getLogger(__name__)

STAGES = ("download", "transcribe", "analyse", "publish")


class PipelineError(Exception):
    """Raised when the pipeline encounters a non-recoverable error."""


def run(
    video_path: str | None = None,
    url: str | None = None,
    broadcast_date: str | None = None,
    episode_id: str | None = None,
    skip_to: str | None = None,
    force: bool = False,
    cache_dir: str = str(DEFAULT_CACHE_DIR),
) -> None:
    """Run the full analysis pipeline.

    Args:
        video_path: Path to a local video file (skip download).
        url: BBC iPlayer URL (triggers download first).
        broadcast_date: Air date (YYYY-MM-DD); required alongside url.
        episode_id: Episode ID for re-running specific stages.
        skip_to: Stage to skip to (e.g. "analyse").
        force: Force re-processing even if cached.
        cache_dir: Base directory for cached outputs.
    """
    pipeline_start = time.monotonic()
    logger.info("Pipeline starting")

    # Validate inputs
    if skip_to and not episode_id:
        raise PipelineError("--skip-to requires --episode-id")
    if not video_path and not url and not skip_to:
        raise PipelineError("Provide video_path or url (or --skip-to with --episode-id)")
    if url and not broadcast_date:
        raise PipelineError("--url requires --date (YYYY-MM-DD)")

    # Determine which stages to run
    start_stage = skip_to or ("download" if url else "transcribe")
    active_stages = STAGES[STAGES.index(start_stage):]

    # --- Download ---
    if "download" in active_stages and url:
        video_path, episode_id = _timed(
            "download", _do_download, url=url, broadcast_date=broadcast_date
        )

    # Derive episode_id from video filename if not set
    if not episode_id and video_path:
        episode_id = Path(video_path).stem

    if not episode_id:
        raise PipelineError("Could not determine episode_id")

    # Resolve episode identity and cache paths
    try:
        ep = Episode.from_id(episode_id, cache_base=Path(cache_dir))
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    ep.ensure_cache_dir()

    # --- Subtitles ---
    # iPlayer only serves subtitles inside an episode's availability window,
    # so they are fetched alongside the video rather than at transcribe time.
    if url and (not ep.subtitles_path.exists() or force):
        _timed(
            "subtitles", _do_fetch_subtitles,
            url=url, destination=ep.subtitles_path,
        )

    # --- Transcribe ---
    transcript: Transcript | None = None

    if "transcribe" in active_stages:
        if not ep.subtitles_path.exists() and (not ep.transcript_path.exists() or force):
            raise PipelineError(
                f"No subtitles found for {episode_id} at {ep.subtitles_path}. "
                f"Run `python -m motd subtitles URL_OR_ID {ep.broadcast_date}` first."
            )
        transcript, was_computed = get_or_compute(
            ep.transcript_path, Transcript,
            lambda: _timed(
                "transcribe", _do_transcribe,
                subtitles_path=ep.subtitles_path, episode_id=episode_id,
            ),
            force=force,
        )
        if was_computed:
            logger.info(
                "Transcript cached: %s (%d segments)",
                ep.transcript_path, len(transcript.segments),
            )
        else:
            logger.info("Using cached transcript: %s", ep.transcript_path)
    elif "analyse" in active_stages or "publish" in active_stages:
        transcript = load(ep.transcript_path, Transcript)

    # --- Analyse ---
    analysis: EpisodeAnalysis | None = None

    if "analyse" in active_stages:
        if not transcript:
            raise PipelineError(
                f"No transcript found for {episode_id}. Run transcription first."
            )

        candidates = _load_candidates(ep.broadcast_date)
        if not candidates:
            raise PipelineError(
                f"No fixtures found for {ep.broadcast_date}. "
                "This may not be a Premier League matchday."
            )

        analysis = _timed(
            "analyse", _do_analyse,
            transcript=transcript, candidates=candidates, episode_id=episode_id,
        )
        ep.analysis_path.write_text(analysis.model_dump_json(indent=2))
        logger.info(
            "Analysis cached: %s (%d matches)",
            ep.analysis_path, len(analysis.matches),
        )
    elif "publish" in active_stages:
        analysis = load(ep.analysis_path, EpisodeAnalysis)

    # --- Publish ---
    if "publish" in active_stages:
        if not analysis:
            raise PipelineError(
                f"No analysis found for {episode_id}. Run analysis first."
            )
        key = _timed("publish", _do_publish, analysis=analysis)
        logger.info("Published: %s", key)

    elapsed = time.monotonic() - pipeline_start
    logger.info("Pipeline complete (%.1fs)", elapsed)


def _timed(stage_name: str, fn, **kwargs):  # type: ignore[no-untyped-def]
    """Run a stage function with timing logs."""
    logger.info("Stage [%s] starting", stage_name)
    start = time.monotonic()
    result = fn(**kwargs)
    elapsed = time.monotonic() - start
    logger.info("Stage [%s] complete (%.1fs)", stage_name, elapsed)
    return result


def _load_candidates(broadcast_date: str) -> list[Fixture]:
    """Load the fixtures an episode broadcast on this date could have shown."""
    from motd.episode import season_for_date
    from motd.fixtures import FileFixtureProvider, fixtures_path_for_season

    path = fixtures_path_for_season(season_for_date(broadcast_date))
    if not path.exists():
        raise PipelineError(
            f"Fixtures file not found: {path}. Run `python -m motd fixtures sync`."
        )

    provider = FileFixtureProvider(path)
    return provider.get_candidates(broadcast_date)


def _do_download(url: str, broadcast_date: str) -> tuple[str, str]:
    """Download an episode and return (video_path, episode_id)."""
    from motd.downloader import download

    result = download(url, broadcast_date)
    return result.video_path, result.episode_id


def _do_fetch_subtitles(url: str, destination: Path) -> Path:
    """Fetch an episode's subtitles from iPlayer."""
    from motd.subtitles import SubtitleError, download_subtitles

    try:
        return download_subtitles(url, destination)
    except SubtitleError as exc:
        raise PipelineError(str(exc)) from exc


def _do_transcribe(subtitles_path: Path, episode_id: str) -> Transcript:
    """Build a transcript from an episode's subtitles."""
    from motd.subtitles import SubtitleError, parse_ttml

    try:
        return parse_ttml(subtitles_path, episode_id)
    except SubtitleError as exc:
        raise PipelineError(str(exc)) from exc


def _do_analyse(
    transcript: Transcript,
    candidates: list[Fixture],
    episode_id: str,
) -> EpisodeAnalysis:
    """Extract running order and timings from a transcript."""
    from motd.analyser import analyse

    return analyse(transcript, candidates, episode_id)


def _do_publish(analysis: EpisodeAnalysis) -> str:
    """Publish analysis to R2."""
    from motd.publisher import publish

    return publish(analysis)
