"""
MOTD Analyser CLI

Command-line interface for video analysis pipeline.
"""

import click
import json
import logging
import sys
import yaml
from pathlib import Path
from typing import Any

from motd.scene_detection.detector import detect_scenes
from motd.scene_detection.frame_extractor import extract_key_frames_for_scenes


def load_config(config_path: Path = Path("config/config.yaml")) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if not config_path.exists():
        click.echo(f"Warning: Config file not found at {config_path}", err=True)
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


def setup_logging(config: dict[str, Any]) -> None:
    """Configure logging based on config settings."""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO"))
    format_str = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Optionally add file handler
    if log_config.get("file"):
        log_file = Path(log_config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_str))
        logging.getLogger().addHandler(file_handler)


@click.group()
@click.version_option(version="0.1.0", prog_name="motd")
def cli():
    """MOTD Analyser - Analyse Match of the Day videos for coverage bias."""
    pass


@cli.command("detect-scenes")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--threshold",
    type=float,
    default=None,
    help="Scene detection threshold (lower = more sensitive). Defaults to config value."
)
@click.option(
    "--min-scene-duration",
    type=float,
    default=None,
    help="Minimum scene duration in seconds. Defaults to config value."
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file path. Defaults to data/cache/{video_name}/scenes.json"
)
@click.option(
    "--frames-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory for extracted frames. Defaults to data/cache/{video_name}/frames/"
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/config.yaml"),
    help="Path to configuration file"
)
def detect_scenes_command(
    video_path: Path,
    threshold: float | None,
    min_scene_duration: float | None,
    output: Path | None,
    frames_dir: Path | None,
    config: Path
):
    """
    Detect scene transitions in a video and extract key frames.

    Analyses VIDEO_PATH to identify scene transitions (e.g., studio to highlights,
    match to match) and extracts a key frame for each scene.

    Example:

        python -m motd detect-scenes data/videos/motd_2025-26_2025-11-01.mp4
    """
    # Load configuration
    config_data = load_config(config)
    setup_logging(config_data)

    logger = logging.getLogger(__name__)
    logger.info("Starting scene detection")
    logger.info(f"Video: {video_path}")

    # Get default values from config
    scene_config = config_data.get("scene_detection", {})
    cache_config = config_data.get("cache", {})

    # Use CLI args if provided, otherwise fall back to config
    threshold = threshold if threshold is not None else scene_config.get("threshold", 30.0)
    min_scene_duration = min_scene_duration if min_scene_duration is not None else scene_config.get("min_scene_duration", 3.0)

    # Determine output paths
    video_name = video_path.stem
    default_cache_dir = Path(cache_config.get("directory", "data/cache")) / video_name

    if output is None:
        output = default_cache_dir / "scenes.json"

    if frames_dir is None:
        frames_dir = default_cache_dir / "frames"

    # Create output directories
    output.parent.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Configuration: threshold={threshold}, min_scene_duration={min_scene_duration}")
    logger.info(f"Output: {output}")
    logger.info(f"Frames: {frames_dir}")

    try:
        # Detect scenes
        click.echo("Detecting scenes...")
        scenes = detect_scenes(
            video_path=str(video_path),
            threshold=threshold,
            min_scene_duration=min_scene_duration
        )

        click.echo(f"Detected {len(scenes)} scenes")

        # Extract key frames
        click.echo("Extracting key frames...")
        extract_key_frames_for_scenes(
            video_path=video_path,
            scenes=scenes,
            output_dir=frames_dir,
            extract_position="start"
        )

        # Prepare output JSON
        output_data = {
            "video_path": str(video_path),
            "video_name": video_name,
            "threshold": threshold,
            "min_scene_duration": min_scene_duration,
            "total_scenes": len(scenes),
            "scenes": [
                {
                    "scene_index": i,
                    "scene_id": scene["scene_id"],
                    "start_time": scene["start_time"],
                    "end_time": scene["end_time"],
                    "start_seconds": scene["start_seconds"],
                    "end_seconds": scene["end_seconds"],
                    "duration": scene["duration_seconds"],
                    "frames": [scene.get("key_frame_path")] if scene.get("key_frame_path") else []
                }
                for i, scene in enumerate(scenes)
            ]
        }

        # Save to JSON
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)

        click.echo(f"\nScene detection complete!")
        click.echo(f"  Scenes detected: {len(scenes)}")
        click.echo(f"  Output JSON: {output}")
        click.echo(f"  Frames directory: {frames_dir}")

        # Provide guidance based on scene count
        if len(scenes) < 20:
            click.echo("\nWarning: Very few scenes detected (<20).", err=True)
            click.echo("  Consider lowering threshold (try 25.0 or 20.0)", err=True)
        elif len(scenes) > 200:
            click.echo("\nWarning: Very many scenes detected (>200).", err=True)
            click.echo("  Consider raising threshold (try 35.0 or 40.0)", err=True)
        else:
            click.echo(f"\n  Scene count looks reasonable for video analysis.")

        logger.info("Scene detection completed successfully")

    except Exception as e:
        logger.error(f"Scene detection failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
