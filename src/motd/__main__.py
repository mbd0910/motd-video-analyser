"""CLI entry point for the MOTD analysis pipeline.

Usage: python -m motd [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

logger = logging.getLogger(__name__)


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
def download(url_or_id: str) -> None:
    """Download an MOTD episode from BBC iPlayer."""
    click.echo("Download not yet implemented — see issue #23")


@cli.command()
@click.argument("video_path")
@click.option("--output", type=click.Path(), help="Output path for transcript JSON.")
@click.option("--force", is_flag=True, help="Force re-transcription even if cached.")
@click.option("--episode-id", help="Episode ID (derived from filename if omitted).")
def transcribe(video_path: str, output: str | None, force: bool, episode_id: str | None) -> None:
    """Transcribe a video file to structured JSON."""
    from motd.transcriber import transcribe as do_transcribe

    video = Path(video_path)
    if not video.exists():
        click.echo(f"Error: video file not found: {video_path}", err=True)
        sys.exit(1)

    if episode_id is None:
        episode_id = video.stem

    # Determine output path
    cache_dir = Path("data/cache") / episode_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(output) if output else cache_dir / "transcript.json"

    if out_path.exists() and not force:
        click.echo(f"Transcript already exists: {out_path} (use --force to overwrite)")
        return

    transcript = do_transcribe(str(video), episode_id)

    out_path.write_text(transcript.model_dump_json(indent=2))
    click.echo(f"Transcript saved: {out_path} ({len(transcript.segments)} segments)")


@cli.command()
@click.argument("episode_id")
@click.option("--output", type=click.Path(), help="Output path for analysis JSON.")
@click.option("--force", is_flag=True, help="Force re-analysis even if cached.")
def analyse(episode_id: str, output: str | None, force: bool) -> None:
    """Analyse a transcript and produce structured episode analysis."""
    from motd.analyser import analyse as do_analyse
    from motd.fixtures import FileFixtureProvider
    from motd.models import Transcript

    cache_dir = Path("data/cache") / episode_id
    transcript_path = cache_dir / "transcript.json"

    if not transcript_path.exists():
        click.echo(f"Error: transcript not found: {transcript_path}", err=True)
        click.echo("Run `python -m motd transcribe` first.")
        sys.exit(1)

    out_path = Path(output) if output else cache_dir / "analysis.json"

    if out_path.exists() and not force:
        click.echo(f"Analysis already exists: {out_path} (use --force to overwrite)")
        return

    # Load transcript
    transcript = Transcript.model_validate_json(transcript_path.read_text())

    # Derive broadcast date from episode_id (motd_YYYY-YY_YYYY-MM-DD)
    parts = episode_id.split("_")
    if len(parts) >= 3:
        broadcast_date = parts[2]
        season = parts[1]
    else:
        click.echo(f"Error: cannot derive date from episode_id: {episode_id}", err=True)
        click.echo("Expected format: motd_YYYY-YY_YYYY-MM-DD")
        sys.exit(1)

    # Load fixtures
    fixtures_path = Path("data/fixtures/premier_league_2025_26.json")
    if not fixtures_path.exists():
        click.echo(f"Error: fixtures file not found: {fixtures_path}", err=True)
        sys.exit(1)

    provider = FileFixtureProvider(fixtures_path)
    fixtures = provider.get_fixtures_for_date(broadcast_date)

    if not fixtures:
        click.echo(f"Error: no fixtures found for {broadcast_date}", err=True)
        click.echo("This may not be a Premier League matchday.")
        sys.exit(1)

    analysis = do_analyse(transcript, fixtures, episode_id, broadcast_date, season)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(analysis.model_dump_json(indent=2))
    click.echo(f"Analysis saved: {out_path} ({len(analysis.matches)} matches)")


@cli.command()
@click.argument("episode_id")
def publish(episode_id: str) -> None:
    """Publish analysis JSON to Cloudflare R2."""
    from motd.models import EpisodeAnalysis
    from motd.publisher import publish as do_publish

    cache_dir = Path("data/cache") / episode_id
    analysis_path = cache_dir / "analysis.json"

    if not analysis_path.exists():
        click.echo(f"Error: analysis not found: {analysis_path}", err=True)
        click.echo("Run `python -m motd analyse` first.")
        sys.exit(1)

    analysis = EpisodeAnalysis.model_validate_json(analysis_path.read_text())
    key = do_publish(analysis)
    click.echo(f"Published: {key}")


@cli.command()
@click.argument("video_path", required=False)
@click.option("--url", help="BBC iPlayer URL to download and process.")
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
    episode_id: str | None,
    skip_to: str | None,
    force: bool,
) -> None:
    """Run the full analysis pipeline."""
    click.echo("Pipeline not yet implemented — see issue #24")


if __name__ == "__main__":
    cli()
