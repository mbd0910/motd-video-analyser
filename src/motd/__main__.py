"""CLI entry point for the MOTD analysis pipeline.

Usage: python -m motd [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import click


@click.group()
@click.version_option(version="0.2.0", prog_name="motd-analyser")
def cli() -> None:
    """MOTD Analyser — measure coverage bias in Match of the Day."""


@cli.command()
@click.argument("url_or_id")
def download(url_or_id: str) -> None:
    """Download an MOTD episode from BBC iPlayer."""
    click.echo("Download not yet implemented — see issue #23")


@cli.command()
@click.argument("video_path")
@click.option("--output", type=click.Path(), help="Output path for transcript JSON.")
@click.option("--force", is_flag=True, help="Force re-transcription even if cached.")
def transcribe(video_path: str, output: str | None, force: bool) -> None:
    """Transcribe a video file to structured JSON."""
    click.echo("Transcribe not yet implemented — see issue #20")


@cli.command()
@click.argument("episode_id")
@click.option("--output", type=click.Path(), help="Output path for analysis JSON.")
@click.option("--force", is_flag=True, help="Force re-analysis even if cached.")
def analyse(episode_id: str, output: str | None, force: bool) -> None:
    """Analyse a transcript and produce structured episode analysis."""
    click.echo("Analyse not yet implemented — see issue #20")


@cli.command()
@click.argument("episode_id")
def publish(episode_id: str) -> None:
    """Publish analysis JSON to Cloudflare R2."""
    click.echo("Publish not yet implemented — see issue #21")


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
