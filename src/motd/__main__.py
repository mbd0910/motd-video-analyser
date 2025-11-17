"""
MOTD Analyser CLI

Command-line interface for video analysis pipeline.
"""

import click
import json
import logging
import sys
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motd.scene_detection.detector import detect_scenes
from motd.scene_detection.frame_extractor import extract_key_frames_for_scenes
from motd.config.defaults import (
    DEFAULT_THRESHOLD,
    DEFAULT_MIN_SCENE_DURATION,
    DEFAULT_DETECTOR_TYPE
)
from motd.ocr import OCRReader, TeamMatcher, FixtureMatcher
from motd.transcription import AudioExtractor, WhisperTranscriber


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

    # Use CLI args if provided, otherwise fall back to config, then to defaults
    threshold = threshold if threshold is not None else scene_config.get("threshold", DEFAULT_THRESHOLD)
    min_scene_duration = min_scene_duration if min_scene_duration is not None else scene_config.get("min_scene_duration", DEFAULT_MIN_SCENE_DURATION)
    detector_type = scene_config.get("detector_type", DEFAULT_DETECTOR_TYPE)

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

    logger.info(f"Configuration: detector_type={detector_type}, threshold={threshold}, min_scene_duration={min_scene_duration}")
    logger.info(f"Output: {output}")
    logger.info(f"Frames: {frames_dir}")

    try:
        # Detect scenes
        click.echo("Detecting scenes...")
        scenes = detect_scenes(
            video_path=str(video_path),
            threshold=threshold,
            min_scene_duration=min_scene_duration,
            detector_type=detector_type
        )

        click.echo(f"Detected {len(scenes)} scenes")

        # Extract frames (hybrid or traditional)
        ocr_config = config_data.get('ocr', {})
        sampling_config = ocr_config.get('sampling', {})
        use_hybrid = sampling_config.get('use_hybrid', False)

        if use_hybrid:
            click.echo("Extracting frames using hybrid strategy (scene changes + intervals)...")
            from motd.scene_detection.detector import hybrid_frame_extraction
            from motd.scene_detection.frame_extractor import extract_hybrid_frames

            # Get filtering config
            filtering = ocr_config.get('filtering', {})
            skip_intro = filtering.get('skip_intro_seconds', 0)
            motd2_start = filtering.get('motd2_interlude_start', 0)
            motd2_end = filtering.get('motd2_interlude_end', 0)
            skip_intervals = [(motd2_start, motd2_end)] if motd2_start and motd2_end else []

            # Generate hybrid frame list
            hybrid_frames = hybrid_frame_extraction(
                video_path=str(video_path),
                scenes=scenes,
                interval=sampling_config.get('interval', 5.0),
                dedupe_threshold=sampling_config.get('dedupe_threshold', 1.0),
                skip_intro=skip_intro,
                skip_intervals=skip_intervals
            )

            # Extract frames
            hybrid_frames = extract_hybrid_frames(video_path, hybrid_frames, frames_dir)

            # Update scenes with hybrid frame paths (for compatibility with existing code)
            # Each scene gets the first hybrid frame that falls within its timespan
            for scene in scenes:
                matching_frames = [
                    f['frame_path'] for f in hybrid_frames
                    if f.get('frame_path') and
                       scene['start_seconds'] <= f['timestamp'] < scene['end_seconds']
                ]
                if matching_frames:
                    scene['key_frame_path'] = matching_frames[0]
                    scene['frames'] = matching_frames  # Store all matching frames
                else:
                    scene['key_frame_path'] = None
                    scene['frames'] = []

            click.echo(f"  Extracted {len(hybrid_frames)} hybrid frames")
            click.echo(f"  Scene frames: {sum(1 for f in hybrid_frames if f['source'] == 'scene_change')}")
            click.echo(f"  Interval samples: {sum(1 for f in hybrid_frames if f['source'] == 'interval_sampling')}")
        else:
            click.echo("Extracting key frames (scene changes only)...")
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
            "detector_type": detector_type,
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


def filter_scenes(scenes: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Filter scenes based on reconnaissance findings from Task 009a.

    Note: With hybrid frame extraction (Task 011b), min_scene_duration filtering
    is removed. Hybrid approach guarantees coverage regardless of scene duration.

    Filters out:
    - Intro scenes (first 50 seconds)
    - MOTD 2 interlude (52:01-52:47)
    """
    filtering = config.get('ocr', {}).get('filtering', {})

    filtered = []

    # Skip intro (50 seconds)
    intro_seconds = filtering.get('skip_intro_seconds', 50)

    # Skip MOTD 2 interlude (52:01-52:47)
    motd2_start = filtering.get('motd2_interlude_start', 3121)  # 52:01
    motd2_end = filtering.get('motd2_interlude_end', 3167)      # 52:47

    # Note: min_scene_duration filtering removed (Task 011b)
    # Hybrid frame extraction now handles coverage of brief graphics

    for scene in scenes:
        # Skip intro
        if scene['start_seconds'] < intro_seconds:
            continue

        # Skip MOTD 2 interlude
        if motd2_start <= scene['start_seconds'] <= motd2_end:
            continue

        filtered.append(scene)

    return filtered


def process_scene(
    scene: dict[str, Any],
    ocr_reader: OCRReader,
    team_matcher: TeamMatcher,
    fixture_matcher: FixtureMatcher,
    expected_teams: list[str],
    episode_id: str,
    logger: logging.Logger
) -> dict[str, Any] | None:
    """Process single scene: OCR → team matching → validation."""

    try:
        # Get frame path
        if not scene.get('frames') or len(scene['frames']) == 0:
            return None

        frame_path = Path(scene['frames'][0])

        if not frame_path.exists():
            logger.warning(f"Frame not found: {frame_path}")
            return None

        # Run OCR with fallback strategy (FT score → scoreboard)
        ocr_result = ocr_reader.extract_with_fallback(frame_path)

        if not ocr_result['results']:
            return None

        # Combine text from OCR results
        combined_text = ' '.join([r['text'] for r in ocr_result['results']])

        if not combined_text or not combined_text.strip():
            return None

        # Match teams (with fixture candidates)
        matches = team_matcher.match_multiple(
            combined_text,
            candidate_teams=expected_teams,
            max_teams=2
        )

        if not matches:
            return None

        detected_teams = [
            {
                'team': match['team'],
                'confidence': match['confidence'],
                'matched_text': match['matched_text'],
                'fixture_validated': match['fixture_validated']
            }
            for match in matches
        ]

        # Validate against fixtures
        team_names = [t['team'] for t in detected_teams]
        validation = fixture_matcher.validate_teams(team_names, episode_id)

        # Apply confidence boost
        for team in detected_teams:
            team['confidence'] *= validation['confidence_boost']

        # Try to identify fixture
        matched_fixture = None
        if len(detected_teams) >= 2:
            matched_fixture = fixture_matcher.identify_fixture(
                detected_teams[0]['team'],
                detected_teams[1]['team'],
                episode_id
            )

        return {
            'scene_id': scene['scene_id'],
            'start_time': scene['start_time'],
            'start_seconds': scene['start_seconds'],
            'frame_path': str(frame_path),
            'ocr_source': ocr_result['primary_source'],
            'detected_teams': detected_teams,
            'validated_teams': validation['validated_teams'],
            'unexpected_teams': validation['unexpected_teams'],
            'confidence_boost': validation['confidence_boost'],
            'matched_fixture': matched_fixture['match_id'] if matched_fixture else None
        }

    except Exception as e:
        logger.error(f"Error processing scene {scene.get('scene_id', 'unknown')}: {e}")
        return None


def generate_summary(ocr_results: list[dict[str, Any]], expected_teams: list[str]) -> dict[str, Any]:
    """Generate summary statistics."""

    all_detected = set()
    validated_count = 0
    unexpected_count = 0
    fixtures_identified = 0

    for result in ocr_results:
        teams = [t['team'] for t in result['detected_teams']]
        all_detected.update(teams)

        validated_count += len(result['validated_teams'])
        unexpected_count += len(result['unexpected_teams'])

        if result['matched_fixture']:
            fixtures_identified += 1

    return {
        'total_scenes_processed': len(ocr_results),
        'unique_teams_detected': len(all_detected),
        'expected_teams_found': len(all_detected & set(expected_teams)),
        'validated_detections': validated_count,
        'unexpected_detections': unexpected_count,
        'fixtures_identified': fixtures_identified
    }


@cli.command("extract-teams")
@click.option(
    '--scenes',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to scenes JSON file from scene detection'
)
@click.option(
    '--episode-id',
    required=True,
    help='Episode identifier (e.g., motd-2025-11-01)'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=None,
    help='Output path for OCR results JSON (default: cache/{episode_id}/ocr_results.json)'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    default=Path('config/config.yaml'),
    help='Path to config file'
)
def extract_teams_command(
    scenes: Path,
    episode_id: str,
    output: Path | None,
    config: Path
):
    """
    Extract team names from video frames using OCR and fixture matching.

    Processes scenes from SCENES JSON, runs OCR on key frames, matches team names
    using fuzzy matching, and validates against expected fixtures for the episode.

    Example:

        python -m motd extract-teams \\
          --scenes data/cache/motd-2025-11-01/scenes.json \\
          --episode-id motd-2025-11-01
    """
    # Load config
    cfg = load_config(config)
    setup_logging(cfg)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting team extraction for episode: {episode_id}")
    click.echo(f"Processing episode: {episode_id}")

    # Load scenes
    with open(scenes) as f:
        scenes_data = json.load(f)

    total_scenes = len(scenes_data['scenes'])
    click.echo(f"Loaded {total_scenes} scenes")
    logger.info(f"Loaded {total_scenes} scenes from {scenes}")

    try:
        # Initialise OCR components
        click.echo("Initialising OCR components...")
        ocr_reader = OCRReader(cfg['ocr'])
        team_matcher = TeamMatcher(Path('data/teams/premier_league_2025_26.json'))
        fixture_matcher = FixtureMatcher(
            Path('data/fixtures/premier_league_2025_26.json'),
            Path('data/episodes/episode_manifest.json')
        )
        click.echo("✓ OCR components initialised")

        # Get expected teams for fixture-aware matching
        expected_teams = fixture_matcher.get_expected_teams(episode_id)
        expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)
        click.echo(f"✓ Expected {len(expected_fixtures)} fixtures with {len(expected_teams)} teams")
        logger.info(f"Expected {len(expected_fixtures)} fixtures with {len(expected_teams)} teams")

        # Filter scenes (based on 009a reconnaissance)
        click.echo("\nFiltering scenes...")
        filtered_scenes = filter_scenes(scenes_data['scenes'], cfg)
        reduction_pct = ((total_scenes - len(filtered_scenes)) / total_scenes) * 100
        click.echo(f"✓ Filtered: {total_scenes} → {len(filtered_scenes)} scenes ({reduction_pct:.1f}% reduction)")
        logger.info(f"Filtered scenes: {total_scenes} → {len(filtered_scenes)} ({reduction_pct:.1f}% reduction)")

        # Process scenes
        click.echo("\nProcessing scenes (this may take several minutes)...")
        ocr_results = []

        for idx, scene in enumerate(filtered_scenes, 1):
            if idx % 50 == 0 or idx == 1:
                click.echo(f"  Processing scene {idx}/{len(filtered_scenes)}...")
                logger.info(f"Processing scene {idx}/{len(filtered_scenes)}")

            result = process_scene(
                scene,
                ocr_reader,
                team_matcher,
                fixture_matcher,
                expected_teams,
                episode_id,
                logger
            )

            if result:
                ocr_results.append(result)

                # Log interesting findings
                if result['unexpected_teams']:
                    logger.warning(
                        f"Scene {result['scene_id']}: Unexpected teams detected: "
                        f"{result['unexpected_teams']}"
                    )

                if result['matched_fixture']:
                    logger.debug(
                        f"Scene {result['scene_id']}: Identified fixture: "
                        f"{result['matched_fixture']}"
                    )

        click.echo(f"✓ Processed {len(filtered_scenes)} scenes, found teams in {len(ocr_results)} scenes")

        # Build output
        summary = generate_summary(ocr_results, expected_teams)

        output_data = {
            'episode_id': episode_id,
            'video_path': scenes_data.get('video_path'),
            'total_scenes': total_scenes,
            'filtered_scenes': len(filtered_scenes),
            'scenes_with_teams': len(ocr_results),
            'expected_fixtures': [
                {
                    'match_id': f['match_id'],
                    'home_team': f['home_team'],
                    'away_team': f['away_team']
                }
                for f in expected_fixtures
            ],
            'ocr_results': ocr_results,
            'summary': summary
        }

        # Save output
        if not output:
            cache_dir = Path('data/cache') / episode_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            output = cache_dir / 'ocr_results.json'

        with open(output, 'w') as f:
            json.dump(output_data, f, indent=2)

        # Display summary
        click.echo(f"\n{'='*60}")
        click.echo("Summary:")
        click.echo(f"{'='*60}")
        click.echo(f"  Total scenes processed:     {summary['total_scenes_processed']}")
        click.echo(f"  Unique teams detected:      {summary['unique_teams_detected']}")
        click.echo(f"  Expected teams found:       {summary['expected_teams_found']}/{len(expected_teams)}")
        click.echo(f"  Validated detections:       {summary['validated_detections']}")
        click.echo(f"  Unexpected detections:      {summary['unexpected_detections']}")
        click.echo(f"  Fixtures identified:        {summary['fixtures_identified']}")
        click.echo(f"{'='*60}")
        click.echo(f"\nOutput saved to: {output}")

        logger.info(f"Team extraction completed successfully")
        logger.info(f"Summary: {summary}")
        logger.info(f"Output: {output}")

    except Exception as e:
        logger.error(f"Team extraction failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command("transcribe")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=None,
    help='Output path for transcript JSON (default: cache/{video_name}/transcript.json)'
)
@click.option(
    '--model-size',
    type=str,
    default=None,
    help='Whisper model size (default: from config)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force re-transcription even if cache exists'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    default=Path('config/config.yaml'),
    help='Path to config file'
)
def transcribe_command(
    video_path: Path,
    output: Path | None,
    model_size: str | None,
    force: bool,
    config: Path
):
    """
    Extract and transcribe audio from video using faster-whisper.

    Extracts audio from VIDEO_PATH, transcribes it with word-level timestamps,
    and caches results to avoid re-processing (3-15 min per video).

    Example:

        python -m motd transcribe data/videos/motd_2025-26_2025-11-01.mp4
    """
    # Load config
    cfg = load_config(config)
    setup_logging(cfg)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting transcription for: {video_path}")
    click.echo(f"Processing video: {video_path.name}")

    # Determine cache directory
    video_name = video_path.stem
    cache_dir = Path('data/cache') / video_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Determine output path
    if not output:
        output = cache_dir / 'transcript.json'

    audio_path = cache_dir / 'audio.wav'

    # Override model size if specified
    transcription_config = cfg.get('transcription', {}).copy()
    if model_size:
        transcription_config['model_size'] = model_size

    # Check cache and validate configuration hasn't changed
    cache_valid = False
    if output.exists() and not force:
        # Load cached transcript
        with open(output) as f:
            cached = json.load(f)

        # Validate cache against current configuration
        cached_metadata = cached.get('metadata', {})
        cached_model = cached_metadata.get('model_size')
        cached_device = cached_metadata.get('device')

        current_model = transcription_config.get('model_size', 'large-v3')
        current_device = transcription_config.get('device', 'auto')

        # Check if configuration has changed
        config_changed = (cached_model != current_model or
                         (current_device != 'auto' and cached_device != current_device))

        if config_changed:
            click.echo(f"\n⚠️  Cache invalid: configuration changed")
            click.echo(f"   Cached model: {cached_model}, Current: {current_model}")
            if cached_device != current_device and current_device != 'auto':
                click.echo(f"   Cached device: {cached_device}, Current: {current_device}")
            click.echo("   Re-transcribing with new configuration...")
            logger.info(f"Cache invalidated: model {cached_model}→{current_model} or device changed")
            cache_valid = False
        else:
            click.echo(f"\n✓ Cached transcript found: {output}")
            click.echo("Use --force to re-transcribe")
            logger.info(f"Using cached transcript: {output}")

            click.echo(f"\nCached transcript info:")
            click.echo(f"  Duration: {cached.get('duration', 'unknown')}s")
            click.echo(f"  Segments: {cached.get('segment_count', 'unknown')}")
            click.echo(f"  Model: {cached_model}")
            click.echo(f"  Device: {cached_device}")
            click.echo(f"  Processed: {cached_metadata.get('processed_at', 'unknown')}")
            cache_valid = True

    if cache_valid:
        return

    try:
        start_time = time.time()

        # Extract audio
        click.echo("\nExtracting audio from video...")
        logger.info("Starting audio extraction")

        audio_config = cfg.get('transcription', {})
        extractor = AudioExtractor(audio_config)
        extraction_result = extractor.extract(str(video_path), str(audio_path))

        click.echo(
            f"✓ Audio extracted: {extraction_result['output_size_mb']:.1f} MB, "
            f"{extraction_result['duration_seconds']:.1f}s"
        )
        logger.info(f"Audio extraction complete: {extraction_result}")

        # Transcribe audio
        click.echo(f"\nTranscribing audio with Whisper...")
        logger.info("Starting transcription")

        # transcription_config already set earlier for cache validation
        transcriber = WhisperTranscriber(transcription_config)
        transcription_result = transcriber.transcribe(str(audio_path))

        elapsed = time.time() - start_time
        duration = transcription_result['duration']
        rtf = duration / elapsed if elapsed > 0 else 0

        click.echo(
            f"✓ Transcribed {transcription_result['segment_count']} segments "
            f"in {elapsed:.1f}s (RTF: {rtf:.1f}x real-time)"
        )
        logger.info(f"Transcription complete: {transcription_result['segment_count']} segments")

        # Build output with metadata
        output_data = {
            'metadata': {
                'video_path': str(video_path),
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'model_size': transcription_config.get('model_size', 'large-v3'),
                'device': transcriber.device,
                'processing_time_seconds': round(elapsed, 2),
                'real_time_factor': round(rtf, 2)
            },
            **transcription_result
        }

        # Save transcript
        with open(output, 'w') as f:
            json.dump(output_data, f, indent=2)

        click.echo(f"\n{'='*60}")
        click.echo("Transcription Summary:")
        click.echo(f"{'='*60}")
        click.echo(f"  Duration:           {duration:.1f}s ({duration/60:.1f} min)")
        click.echo(f"  Segments:           {transcription_result['segment_count']}")
        click.echo(f"  Language:           {transcription_result['language']}")
        click.echo(f"  Model:              {output_data['metadata']['model_size']}")
        click.echo(f"  Device:             {output_data['metadata']['device']}")
        click.echo(f"  Processing time:    {elapsed:.1f}s ({elapsed/60:.1f} min)")
        click.echo(f"  Real-time factor:   {rtf:.1f}x")
        click.echo(f"{'='*60}")
        click.echo(f"\nTranscript saved to: {output}")

        logger.info(f"Transcription completed successfully")
        logger.info(f"Output: {output}")

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
