"""CLI entry point for the MOTD analysis pipeline.

Usage: python -m motd [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from motd.episode import Episode


@click.group()
@click.version_option(version="0.2.0", prog_name="motd-analyser")
def cli() -> None:
    """MOTD Analyser — measure coverage bias in Match of the Day."""
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
@click.argument("video_path")
@click.option("--output", type=click.Path(), help="Output path for transcript JSON.")
@click.option("--force", is_flag=True, help="Force re-transcription even if cached.")
@click.option("--episode-id", help="Episode ID (derived from filename if omitted).")
def transcribe(video_path: str, output: str | None, force: bool, episode_id: str | None) -> None:
    """Transcribe a video file to structured JSON."""
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
def analyse(episode_id: str, output: str | None, force: bool) -> None:
    """Analyse a transcript and produce structured episode analysis."""
    from motd.analyser import AnalysisError
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

    if out_path.exists() and not force:
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
    fixtures = provider.get_fixtures_for_date(ep.broadcast_date)

    if not fixtures:
        click.echo(f"Error: no fixtures found for {ep.broadcast_date}", err=True)
        click.echo("This may not be a Premier League matchday.")
        sys.exit(1)

    try:
        analysis = do_analyse(transcript, fixtures, episode_id)
    except AnalysisError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(analysis.model_dump_json(indent=2))
    click.echo(f"Analysis saved: {out_path} ({len(analysis.matches)} matches)")


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
