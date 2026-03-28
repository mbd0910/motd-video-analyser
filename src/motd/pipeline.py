"""Pipeline orchestrator — sequences all stages of the MOTD analysis pipeline.

Stages: Download (optional) → Transcribe → Analyse → Publish
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from motd.models import EpisodeAnalysis, Fixture, Transcript

logger = logging.getLogger(__name__)

STAGES = ("download", "transcribe", "analyse", "publish")
DEFAULT_CACHE_DIR = "data/cache"


class PipelineError(Exception):
    """Raised when the pipeline encounters a non-recoverable error."""


def run(
    video_path: str | None = None,
    url: str | None = None,
    episode_id: str | None = None,
    skip_to: str | None = None,
    force: bool = False,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> None:
    """Run the full analysis pipeline.

    Args:
        video_path: Path to a local video file (skip download).
        url: BBC iPlayer URL (triggers download first).
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

    # Determine which stages to run
    start_stage = skip_to or ("download" if url else "transcribe")
    active_stages = STAGES[STAGES.index(start_stage):]

    # --- Download ---
    if "download" in active_stages and url:
        video_path, episode_id = _timed("download", _do_download, url=url)

    # Derive episode_id from video filename if not set
    if not episode_id and video_path:
        episode_id = Path(video_path).stem

    if not episode_id:
        raise PipelineError("Could not determine episode_id")

    ep_cache = Path(cache_dir) / episode_id
    ep_cache.mkdir(parents=True, exist_ok=True)

    # --- Transcribe ---
    transcript: Transcript | None = None
    transcript_path = ep_cache / "transcript.json"

    if "transcribe" in active_stages:
        if transcript_path.exists() and not force:
            logger.info("Using cached transcript: %s", transcript_path)
            transcript = Transcript.model_validate_json(transcript_path.read_text())
        else:
            if not video_path:
                raise PipelineError("Transcription requires a video path")
            transcript = _timed(
                "transcribe", _do_transcribe,
                video_path=video_path, episode_id=episode_id,
            )
            transcript_path.write_text(transcript.model_dump_json(indent=2))
            logger.info("Transcript cached: %s (%d segments)",
                        transcript_path, len(transcript.segments))
    elif "analyse" in active_stages or "publish" in active_stages:
        # Need transcript for analyse — load from cache
        if transcript_path.exists():
            transcript = Transcript.model_validate_json(transcript_path.read_text())

    # --- Analyse ---
    analysis: EpisodeAnalysis | None = None
    analysis_path = ep_cache / "analysis.json"

    if "analyse" in active_stages:
        if not transcript:
            raise PipelineError(
                f"No transcript found for {episode_id}. Run transcription first."
            )

        # Parse broadcast date and season from episode_id
        from motd.downloader import parse_episode_id

        try:
            broadcast_date, season = parse_episode_id(episode_id)
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

        fixtures = _load_fixtures(broadcast_date)
        if not fixtures:
            raise PipelineError(
                f"No fixtures found for {broadcast_date}. "
                "This may not be a Premier League matchday."
            )

        analysis = _timed(
            "analyse", _do_analyse,
            transcript=transcript, fixtures=fixtures,
            episode_id=episode_id, broadcast_date=broadcast_date, season=season,
        )
        analysis_path.write_text(analysis.model_dump_json(indent=2))
        logger.info("Analysis cached: %s (%d matches)",
                    analysis_path, len(analysis.matches))
    elif "publish" in active_stages:
        # Need analysis for publish — load from cache
        if analysis_path.exists():
            analysis = EpisodeAnalysis.model_validate_json(analysis_path.read_text())

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


def _load_fixtures(broadcast_date: str) -> list[Fixture]:
    """Load fixtures for a broadcast date."""
    from motd.fixtures import DEFAULT_FIXTURES_PATH, FileFixtureProvider

    if not DEFAULT_FIXTURES_PATH.exists():
        raise PipelineError(f"Fixtures file not found: {DEFAULT_FIXTURES_PATH}")

    provider = FileFixtureProvider(DEFAULT_FIXTURES_PATH)
    return provider.get_fixtures_for_date(broadcast_date)


def _do_download(url: str) -> tuple[str, str]:
    """Download an episode and return (video_path, episode_id)."""
    from motd.downloader import download

    result = download(url)
    return result.video_path, result.episode_id


def _do_transcribe(video_path: str, episode_id: str) -> Transcript:
    """Transcribe a video file."""
    from motd.transcriber import transcribe

    return transcribe(video_path, episode_id)


def _do_analyse(
    transcript: Transcript,
    fixtures: list[Fixture],
    episode_id: str,
    broadcast_date: str,
    season: str,
) -> EpisodeAnalysis:
    """Analyse a transcript against fixtures."""
    from motd.analyser import analyse

    return analyse(transcript, fixtures, episode_id, broadcast_date, season)


def _do_publish(analysis: EpisodeAnalysis) -> str:
    """Publish analysis to R2."""
    from motd.publisher import publish

    return publish(analysis)
