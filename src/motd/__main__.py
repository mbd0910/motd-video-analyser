"""CLI entry point for the MOTD analysis pipeline.

Usage: python -m motd [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import cast

import click
from dotenv import find_dotenv, load_dotenv

from motd.episode import Episode


@click.group()
@click.version_option(version="0.2.0", prog_name="motd-analyser")
def cli() -> None:
    """MOTD Analyser — measure coverage bias in Match of the Day."""
    # usecwd: the bare call resolves against this file, which finds the repo's own
    # .env even when run from elsewhere. Data paths are cwd-relative, so .env is too.
    load_dotenv(find_dotenv(usecwd=True))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@cli.command()
@click.argument("url_or_id")
@click.argument("broadcast_date")
@click.option(
    "--output-dir",
    default="data/videos",
    type=click.Path(),
    help="Directory to save downloaded video.",
)
def download(url_or_id: str, broadcast_date: str, output_dir: str) -> None:
    """Download an MOTD episode from BBC iPlayer.

    URL_OR_ID is the iPlayer URL or programme ID; BROADCAST_DATE is the
    air date as YYYY-MM-DD.
    """
    from motd.downloader import DownloadError
    from motd.downloader import download as do_download

    try:
        result = do_download(url_or_id, broadcast_date, output_dir=output_dir)
    except DownloadError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Episode ID: {result.episode_id}")
    click.echo(f"Video path: {result.video_path}")


@cli.command()
@click.argument("url_or_id")
@click.argument("broadcast_date")
@click.option("--force", is_flag=True, help="Re-fetch and re-parse even if cached.")
def subtitles(url_or_id: str, broadcast_date: str, force: bool) -> None:
    """Fetch iPlayer subtitles and build a transcript from them.

    URL_OR_ID is the iPlayer URL or programme ID; BROADCAST_DATE is the
    air date as YYYY-MM-DD.
    """
    from motd.downloader import normalise_url
    from motd.subtitles import SubtitleError, download_subtitles, parse_ttml

    try:
        ep = Episode.from_broadcast_date(broadcast_date)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    ep.ensure_cache_dir()

    if ep.transcript_path.exists() and not force:
        click.echo(
            f"Transcript already exists: {ep.transcript_path} (use --force to overwrite)"
        )
        return

    try:
        if not ep.subtitles_path.exists() or force:
            download_subtitles(normalise_url(url_or_id), ep.subtitles_path)
        else:
            click.echo(f"Using cached subtitles: {ep.subtitles_path}")
        transcript = parse_ttml(ep.subtitles_path, ep.episode_id)
    except SubtitleError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    ep.transcript_path.write_text(transcript.model_dump_json(indent=2))

    speakers = {seg.speaker for seg in transcript.segments if seg.speaker}
    click.echo(f"Subtitles saved: {ep.subtitles_path}")
    click.echo(
        f"Transcript saved: {ep.transcript_path} "
        f"({len(transcript.segments)} segments, "
        f"{transcript.duration_seconds / 60:.1f} min, "
        f"{len(speakers)} speaker markers)"
    )


@cli.command()
@click.argument("video_path")
@click.option("--output", type=click.Path(), help="Output path for transcript JSON.")
@click.option("--force", is_flag=True, help="Force re-transcription even if cached.")
@click.option("--episode-id", help="Episode ID (derived from filename if omitted).")
def transcribe(video_path: str, output: str | None, force: bool, episode_id: str | None) -> None:
    """Transcribe a video file to structured JSON via the Whisper API."""
    from motd.transcriber import TranscriptionError
    from motd.transcriber import transcribe as do_transcribe

    video = Path(video_path)
    if not video.exists():
        click.echo(f"Error: video file not found: {video_path}", err=True)
        sys.exit(1)

    if episode_id is None:
        episode_id = video.stem

    try:
        ep = Episode.from_id(episode_id)
    except ValueError:
        # Non-standard episode_id — use basic cache path
        ep = None

    if ep:
        ep.ensure_cache_dir()
        out_path = Path(output) if output else ep.transcript_path
    else:
        out_path = Path(output) if output else Path("data/cache") / episode_id / "transcript.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not force:
        click.echo(f"Transcript already exists: {out_path} (use --force to overwrite)")
        return

    try:
        transcript = do_transcribe(str(video), episode_id)
    except TranscriptionError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    out_path.write_text(transcript.model_dump_json(indent=2))
    click.echo(f"Transcript saved: {out_path} ({len(transcript.segments)} segments)")


@cli.command()
@click.argument("episode_id")
@click.option("--output", type=click.Path(), help="Output path for analysis JSON.")
@click.option("--force", is_flag=True, help="Force re-analysis even if cached.")
@click.option("--model", help="Claude model to analyse with (defaults to Opus 5).")
@click.option(
    "--effort", type=click.Choice(["low", "medium", "high", "xhigh", "max"]),
    help="Reasoning effort (defaults to xhigh).",
)
@click.option(
    "--cache-ttl", type=click.Choice(["5m", "1h", "off"]), default="5m", show_default=True,
    help="Prompt cache lifetime for the transcript half. Use 1h when iterating on one episode.",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Write the prompt that would be sent to PATH and stop, without calling the API.",
)
def analyse(
    episode_id: str, output: str | None, force: bool, model: str | None,
    effort: str | None, cache_ttl: str, dry_run: bool,
) -> None:
    """Analyse a transcript and produce structured episode analysis."""
    from motd.analyser import (
        DEFAULT_EFFORT,
        DEFAULT_MODEL,
        AnalysisError,
        CacheTtl,
        Effort,
        _build_prompt,
        anthropic_backend,
    )
    from motd.analyser import analyse as do_analyse
    from motd.fixtures import FileFixtureProvider, fixtures_path_for_season
    from motd.models import Transcript

    try:
        ep = Episode.from_id(episode_id)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not ep.transcript_path.exists():
        click.echo(f"Error: transcript not found: {ep.transcript_path}", err=True)
        click.echo("Run `python -m motd transcribe` first.")
        sys.exit(1)

    out_path = Path(output) if output else ep.analysis_path

    if out_path.exists() and not force and not dry_run:
        click.echo(f"Analysis already exists: {out_path} (use --force to overwrite)")
        return

    # Load transcript
    transcript = Transcript.model_validate_json(ep.transcript_path.read_text())

    # Load fixtures
    fixtures_path = fixtures_path_for_season(ep.season)
    if not fixtures_path.exists():
        click.echo(f"Error: fixtures file not found: {fixtures_path}", err=True)
        click.echo("Run `python -m motd fixtures sync` first.")
        sys.exit(1)

    provider = FileFixtureProvider(fixtures_path)
    candidates = provider.get_candidates(ep.broadcast_date)

    if not candidates:
        click.echo(f"Error: no fixtures found for {ep.broadcast_date}", err=True)
        click.echo("This may not be a Premier League matchday.")
        sys.exit(1)

    if dry_run:
        prompt = _build_prompt(
            transcript, candidates, episode_id, ep.broadcast_date, ep.season
        )
        # Two files rather than one: the halves land either side of the cache
        # breakpoint, and iteration diffs the task half on its own.
        ep.cache_dir.mkdir(parents=True, exist_ok=True)
        for half, text in (("context", prompt.context), ("task", prompt.task)):
            half_path = ep.cache_dir / f"prompt.{half}.txt"
            half_path.write_text(text)
            click.echo(f"Prompt {half}: {half_path} ({len(text):,} chars)")
        click.echo(f"Candidates: {len(candidates)} — no API call made")
        return

    try:
        analysis = do_analyse(
            transcript, candidates, episode_id,
            backend=anthropic_backend(
                model or DEFAULT_MODEL,
                cast(Effort, effort) if effort else DEFAULT_EFFORT,
                None if cache_ttl == "off" else cast(CacheTtl, cache_ttl),
            ),
        )
    except AnalysisError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(analysis.model_dump_json(indent=2))
    click.echo(
        f"Analysis saved: {out_path} "
        f"({len(analysis.matches)} of {len(candidates)} candidates covered)"
    )


@cli.command()
@click.argument("episode_id")
def publish(episode_id: str) -> None:
    """Publish analysis JSON to Cloudflare R2."""
    from motd.models import EpisodeAnalysis
    from motd.publisher import publish as do_publish

    try:
        ep = Episode.from_id(episode_id)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not ep.analysis_path.exists():
        click.echo(f"Error: analysis not found: {ep.analysis_path}", err=True)
        click.echo("Run `python -m motd analyse` first.")
        sys.exit(1)

    analysis = EpisodeAnalysis.model_validate_json(ep.analysis_path.read_text())
    key = do_publish(analysis)
    click.echo(f"Published: {key}")


@cli.group()
def fixtures() -> None:
    """Manage season fixture data."""


@fixtures.command("sync")
@click.option("--output", type=click.Path(), help="Output path (derived from season if omitted).")
@click.option("--dry-run", is_flag=True, help="Report what would change without writing.")
def fixtures_sync(output: str | None, dry_run: bool) -> None:
    """Fetch the current season's fixtures from the FPL API."""
    from motd.clubs import ClubDirectory
    from motd.fixtures import fixtures_path_for_season
    from motd.fpl import FplError, fetch_fixtures, write_fixtures

    try:
        clubs = ClubDirectory.load()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        document = fetch_fixtures(clubs)
    except (FplError, KeyError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    season = document["season"]
    all_fixtures = document["fixtures"]
    played = sum(1 for f in all_fixtures if f["played"])
    out_path = Path(output) if output else fixtures_path_for_season(season)

    click.echo(f"Fetched {len(all_fixtures)} fixtures ({season}), {played} played")

    if dry_run:
        click.echo(f"Dry run — would write {out_path}")
        return

    write_fixtures(document, out_path)
    click.echo(f"Wrote {out_path}")


@cli.command()
@click.argument("video_path", required=False)
@click.option("--url", help="BBC iPlayer URL to download and process.")
@click.option("--date", "broadcast_date", help="Broadcast date (YYYY-MM-DD); required with --url.")
@click.option("--episode-id", help="Episode ID for re-running specific stages.")
@click.option(
    "--skip-to",
    type=click.Choice(["transcribe", "analyse", "publish"]),
    help="Skip to a specific pipeline stage.",
)
@click.option("--force", is_flag=True, help="Force re-processing of all stages.")
def run(
    video_path: str | None,
    url: str | None,
    broadcast_date: str | None,
    episode_id: str | None,
    skip_to: str | None,
    force: bool,
) -> None:
    """Run the full analysis pipeline."""
    from motd.pipeline import PipelineError
    from motd.pipeline import run as do_run

    try:
        do_run(
            video_path=video_path,
            url=url,
            broadcast_date=broadcast_date,
            episode_id=episode_id,
            skip_to=skip_to,
            force=force,
        )
    except PipelineError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
