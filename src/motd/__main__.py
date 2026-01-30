"""
MOTD Analyser CLI

Command-line interface for video analysis pipeline.
"""

import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import yaml

from motd.config.defaults import (
    DEFAULT_DETECTOR_TYPE,
    DEFAULT_MIN_SCENE_DURATION,
    DEFAULT_THRESHOLD,
)
from motd.llm import PromptBuilder
from motd.llm.prompt_builder import BuiltPrompt
from motd.pipeline.factory import ServiceFactory
from motd.pipeline.models import Scene
from motd.scene_detection.detector import detect_scenes
from motd.scene_detection.frame_extractor import extract_key_frames_for_scenes
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


def run_scene_detection(
    video_path: Path,
    config: dict[str, Any],
    threshold: float | None = None,
    min_scene_duration: float | None = None,
    output: Path | None = None,
    frames_dir: Path | None = None,
    force: bool = False
) -> tuple[Path, Path, bool]:
    """
    Run scene detection and frame extraction (pure business logic).

    Args:
        video_path: Path to video file
        config: Configuration dictionary
        threshold: Scene detection threshold (overrides config)
        min_scene_duration: Minimum scene duration (overrides config)
        output: Output JSON path (overrides default)
        frames_dir: Frames output directory (overrides default)
        force: Force re-detection even if cache exists

    Returns:
        Tuple of (output_json_path, frames_directory_path, cache_was_used)
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting scene detection")
    logger.info(f"Video: {video_path}")

    # Get default values from config
    scene_config = config.get("scene_detection", {})
    cache_config = config.get("cache", {})
    ocr_config = config.get('ocr', {})
    sampling_config = ocr_config.get('sampling', {})

    # Use provided args if not None, otherwise fall back to config, then to defaults
    threshold = threshold if threshold is not None else scene_config.get("threshold", DEFAULT_THRESHOLD)
    min_scene_duration = min_scene_duration if min_scene_duration is not None else scene_config.get("min_scene_duration", DEFAULT_MIN_SCENE_DURATION)
    detector_type = scene_config.get("detector_type", DEFAULT_DETECTOR_TYPE)
    use_hybrid = sampling_config.get('use_hybrid', False)
    interval = sampling_config.get('interval', 5.0)
    dedupe_threshold = sampling_config.get('dedupe_threshold', 1.0)

    # Determine output paths
    video_name = video_path.stem
    default_cache_dir = Path(cache_config.get("directory", "data/cache")) / video_name

    if output is None:
        output = default_cache_dir / "scenes.json"

    if frames_dir is None:
        frames_dir = default_cache_dir / "frames"

    # Check cache validity (unless force=True)
    cache_valid = False
    if output.exists() and not force:
        try:
            with open(output) as f:
                cached = json.load(f)

            # Validate metadata matches current configuration
            metadata = cached.get('metadata', {})

            # Track which config parameters changed
            changed_fields = []
            if metadata.get('detector_type') != detector_type:
                changed_fields.append(f"detector_type: {metadata.get('detector_type')} → {detector_type}")
            if metadata.get('threshold') != threshold:
                changed_fields.append(f"threshold: {metadata.get('threshold')} → {threshold}")
            if metadata.get('min_scene_duration') != min_scene_duration:
                changed_fields.append(f"min_scene_duration: {metadata.get('min_scene_duration')} → {min_scene_duration}")
            if metadata.get('use_hybrid') != use_hybrid:
                changed_fields.append(f"use_hybrid: {metadata.get('use_hybrid')} → {use_hybrid}")
            if metadata.get('interval') != interval:
                changed_fields.append(f"interval: {metadata.get('interval')} → {interval}")
            if metadata.get('dedupe_threshold') != dedupe_threshold:
                changed_fields.append(f"dedupe_threshold: {metadata.get('dedupe_threshold')} → {dedupe_threshold}")

            if changed_fields:
                print(f"\n⚠️  Cache invalid: {', '.join(changed_fields)}")
                cache_valid = False
            else:
                print(f"\n✓ Cached scene detection found: {output}")
                cache_valid = True
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Cache validation failed: {e}")
            cache_valid = False

    if cache_valid:
        logger.info("Using cached scene detection results")
        return output, frames_dir, True

    # Create output directories
    output.parent.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Configuration: detector_type={detector_type}, threshold={threshold}, min_scene_duration={min_scene_duration}")
    logger.info(f"Output: {output}")
    logger.info(f"Frames: {frames_dir}")

    # Detect scenes
    print("Detecting scenes...")
    scenes = detect_scenes(
        video_path=str(video_path),
        threshold=threshold,
        min_scene_duration=min_scene_duration,
        detector_type=detector_type
    )

    print(f"Detected {len(scenes)} scenes")

    # Extract frames (hybrid or traditional)
    if use_hybrid:
        print("Extracting frames using hybrid strategy (scene changes + intervals)...")
        from motd.scene_detection.detector import hybrid_frame_extraction
        from motd.scene_detection.frame_extractor import extract_hybrid_frames

        # Generate hybrid frame list (processes entire video)
        hybrid_frames = hybrid_frame_extraction(
            video_path=str(video_path),
            scenes=scenes,
            interval=interval,
            dedupe_threshold=dedupe_threshold
        )

        # Extract frames
        hybrid_frames = extract_hybrid_frames(video_path, hybrid_frames, frames_dir)

        # Update scenes with hybrid frame paths (for compatibility with existing code)
        # Optimized O(n+m) single-pass algorithm using sorted timestamps
        from collections import defaultdict

        # Pre-group frames by scene (single pass, assumes sorted timestamps)
        frames_by_scene = defaultdict(list)
        scene_idx = 0

        for frame in hybrid_frames:
            if not frame.get('frame_path'):
                continue

            # Advance to the scene containing this frame
            while scene_idx < len(scenes) and frame['timestamp'] >= scenes[scene_idx]['end_seconds']:
                scene_idx += 1

            # Assign frame to scene if within bounds
            if scene_idx < len(scenes):
                scene = scenes[scene_idx]
                if scene['start_seconds'] <= frame['timestamp'] < scene['end_seconds']:
                    frames_by_scene[scene['scene_id']].append(frame['frame_path'])

        # Assign frames to scenes
        for scene in scenes:
            scene_frames = frames_by_scene.get(scene['scene_id'], [])
            scene['key_frame_path'] = scene_frames[0] if scene_frames else None
            scene['frames'] = scene_frames

        print(f"  Extracted {len(hybrid_frames)} hybrid frames")
        print(f"  Scene frames: {sum(1 for f in hybrid_frames if f['source'] == 'scene_change')}")
        print(f"  Interval samples: {sum(1 for f in hybrid_frames if f['source'] == 'interval_sampling')}")
    else:
        print("Extracting key frames (scene changes only)...")
        extract_key_frames_for_scenes(
            video_path=video_path,
            scenes=scenes,
            output_dir=frames_dir,
            extract_position="start"
        )

    # Prepare output JSON with metadata section
    from datetime import datetime

    output_data = {
        "metadata": {
            "video_path": str(video_path),
            "video_name": video_name,
            "processed_at": datetime.now().isoformat(),
            "detector_type": detector_type,
            "threshold": threshold,
            "min_scene_duration": min_scene_duration,
            "use_hybrid": use_hybrid,
            "interval": interval,
            "dedupe_threshold": dedupe_threshold
        },
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
                "frames": scene.get("frames", [])
            }
            for i, scene in enumerate(scenes)
        ]
    }

    # Save to JSON
    with open(output, "w") as f:
        json.dump(output_data, f, indent=2)

    print("\nScene detection complete!")
    print(f"  Scenes detected: {len(scenes)}")
    print(f"  Output JSON: {output}")
    print(f"  Frames directory: {frames_dir}")

    # Provide guidance based on scene count
    if len(scenes) < 20:
        click.echo("\nWarning: Very few scenes detected (<20).", err=True)
        click.echo("  Consider lowering threshold (try 25.0 or 20.0)", err=True)
    elif len(scenes) > 200:
        click.echo("\nWarning: Very many scenes detected (>200).", err=True)
        click.echo("  Consider raising threshold (try 35.0 or 40.0)", err=True)
    else:
        print("\n  Scene count looks reasonable for video analysis.")

    logger.info("Scene detection completed successfully")

    return output, frames_dir, False


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

    try:
        # Ignore cache_was_used return (CLI shows timing info already)
        _, _, _ = run_scene_detection(
            video_path=video_path,
            config=config_data,
            threshold=threshold,
            min_scene_duration=min_scene_duration,
            output=output,
            frames_dir=frames_dir
        )
    except Exception as e:
        logger.error(f"Scene detection failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


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


def run_team_extraction(
    scenes_path: Path,
    episode_id: str,
    config: dict[str, Any],
    output: Path | None = None,
    force: bool = False
) -> tuple[Path, bool]:
    """
    Run team extraction via OCR and fixture matching (pure business logic).

    Args:
        scenes_path: Path to scenes JSON file
        episode_id: Episode identifier
        config: Configuration dictionary
        output: Output JSON path (overrides default)
        force: Force re-extraction even if cache exists

    Returns:
        Tuple of (output_ocr_results_path, cache_was_used)
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting team extraction for episode: {episode_id}")
    print(f"Processing episode: {episode_id}")

    # Determine output path
    cache_config = config.get("cache", {})
    cache_dir = Path(cache_config.get("directory", "data/cache")) / episode_id

    if output is None:
        output = cache_dir / "ocr_results.json"

    # Get OCR config for cache validation
    ocr_config = config.get("ocr", {})
    ocr_library = ocr_config.get("library", "easyocr")
    gpu = ocr_config.get("gpu", True)
    confidence_threshold = ocr_config.get("confidence_threshold", 0.7)

    # Check cache validity (unless force=True)
    cache_valid = False
    if output.exists() and not force:
        try:
            with open(output) as f:
                cached = json.load(f)

            # Validate metadata matches current configuration
            metadata = cached.get('metadata', {})

            # Track which config parameters changed
            changed_fields = []
            if metadata.get('ocr_library') != ocr_library:
                changed_fields.append(f"ocr_library: {metadata.get('ocr_library')} → {ocr_library}")
            if metadata.get('gpu') != gpu:
                changed_fields.append(f"gpu: {metadata.get('gpu')} → {gpu}")
            if metadata.get('confidence_threshold') != confidence_threshold:
                changed_fields.append(f"confidence_threshold: {metadata.get('confidence_threshold')} → {confidence_threshold}")

            if changed_fields:
                print(f"\n⚠️  Cache invalid: {', '.join(changed_fields)}")
                cache_valid = False
            else:
                print(f"\n✓ Cached team extraction found: {output}")
                cache_valid = True
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Cache validation failed: {e}")
            cache_valid = False

    if cache_valid:
        logger.info("Using cached team extraction results")
        return output, True

    # Load scenes
    with open(scenes_path) as f:
        scenes_data = json.load(f)

    total_scenes = len(scenes_data['scenes'])
    print(f"Loaded {total_scenes} scenes")
    logger.info(f"Loaded {total_scenes} scenes from {scenes_path}")

    # Initialise components using ServiceFactory
    print("Initialising OCR components...")
    factory = ServiceFactory(config)
    ocr_reader = factory.create_ocr_reader()
    team_matcher = factory.create_team_matcher()
    fixture_matcher = factory.create_fixture_matcher()
    print("✓ OCR components initialised")

    # Get expected teams and create episode context
    expected_teams = fixture_matcher.get_expected_teams(episode_id)
    expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)
    print(f"✓ Expected {len(expected_fixtures)} fixtures with {len(expected_teams)} teams")
    logger.info(f"Expected {len(expected_fixtures)} fixtures with {len(expected_teams)} teams")

    # Import here to avoid circular dependency
    from motd.ocr.scene_processor import EpisodeContext, SceneProcessor

    # Create episode context and scene processor
    context = EpisodeContext(
        episode_id=episode_id,
        expected_teams=expected_teams,
        expected_fixtures=expected_fixtures
    )
    processor = SceneProcessor(
        ocr_reader=ocr_reader,
        team_matcher=team_matcher,
        fixture_matcher=fixture_matcher,
        context=context
    )

    # Process all scenes (no filtering - process entire video)
    print("\nProcessing scenes (this may take several minutes)...")
    ocr_results = []
    all_scenes = scenes_data['scenes']

    for idx, scene_dict in enumerate(all_scenes, 1):
        if idx % 50 == 0 or idx == 1:
            print(f"  Processing scene {idx}/{len(all_scenes)}...")
            logger.info(f"Processing scene {idx}/{len(all_scenes)}")

        # Convert dict to Scene model
        scene = Scene(
            scene_number=scene_dict['scene_id'],
            start_time=scene_dict['start_time'],
            start_seconds=scene_dict['start_seconds'],
            end_seconds=scene_dict['end_seconds'],
            duration=scene_dict['duration'],
            frames=scene_dict.get('frames', []),
            key_frame_path=scene_dict.get('key_frame_path')
        )

        # Process with SceneProcessor
        processed_scene = processor.process(scene)

        if processed_scene:
            # Convert ProcessedScene model to dict for JSON output
            # Maintain backward compatibility with old output format
            result = {
                'scene_id': processed_scene.scene_number,
                'start_time': processed_scene.start_time,
                'start_seconds': processed_scene.start_seconds,
                'frame_path': processed_scene.frame_path,
                'ocr_source': processed_scene.ocr_source,
                'detected_teams': [
                    {
                        'team': processed_scene.team1,
                        'confidence': processed_scene.match_confidence,
                        'matched_text': 'detected',  # Simplified for now
                        'fixture_validated': processed_scene.fixture_id is not None
                    },
                    {
                        'team': processed_scene.team2,
                        'confidence': processed_scene.match_confidence,
                        'matched_text': 'detected',
                        'fixture_validated': processed_scene.fixture_id is not None
                    }
                ],
                'validated_teams': [processed_scene.team1, processed_scene.team2],
                'unexpected_teams': [],  # Simplified for now
                'confidence_boost': 1.0,  # Simplified for now
                'matched_fixture': processed_scene.fixture_id
            }

            ocr_results.append(result)

            # Log interesting findings
            if result['matched_fixture']:
                logger.debug(
                    f"Scene {result['scene_id']}: Identified fixture: "
                    f"{result['matched_fixture']}"
                )

    print(f"✓ Processed {len(all_scenes)} scenes, found teams in {len(ocr_results)} scenes")

    # Build output
    from datetime import datetime

    summary = generate_summary(ocr_results, expected_teams)

    output_data = {
        'metadata': {
            'episode_id': episode_id,
            'video_path': scenes_data.get('video_path'),
            'processed_at': datetime.now().isoformat(),
            'ocr_library': ocr_library,
            'gpu': gpu,
            'confidence_threshold': confidence_threshold
        },
        'total_scenes': total_scenes,
        'processed_scenes': len(all_scenes),
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
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    print(f"  Total scenes processed:     {summary['total_scenes_processed']}")
    print(f"  Unique teams detected:      {summary['unique_teams_detected']}")
    print(f"  Expected teams found:       {summary['expected_teams_found']}/{len(expected_teams)}")
    print(f"  Validated detections:       {summary['validated_detections']}")
    print(f"  Unexpected detections:      {summary['unexpected_detections']}")
    print(f"  Fixtures identified:        {summary['fixtures_identified']}")
    print(f"{'='*60}")
    print(f"\nOutput saved to: {output}")

    logger.info("Team extraction completed successfully")
    logger.info(f"Summary: {summary}")
    logger.info(f"Output: {output}")

    return output, False


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

    try:
        # Ignore cache_was_used return (CLI shows timing info already)
        _, _ = run_team_extraction(
            scenes_path=scenes,
            episode_id=episode_id,
            config=cfg,
            output=output
        )
    except Exception as e:
        logger.error(f"Team extraction failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


def run_transcription(
    video_path: Path,
    config: dict[str, Any],
    model_size: str | None = None,
    force: bool = False,
    output: Path | None = None
) -> tuple[Path, bool]:
    """
    Run audio transcription via faster-whisper (pure business logic).

    Args:
        video_path: Path to video file
        config: Configuration dictionary
        model_size: Optional Whisper model size override
        force: Force re-transcription even if cache exists
        output: Optional output path (defaults to cache/{video_name}/transcript.json)

    Returns:
        Tuple of (transcript_json_path, cache_was_used)

    Raises:
        Exception: If transcription fails
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting transcription for: {video_path}")

    # Determine cache directory
    video_name = video_path.stem
    cache_dir = Path('data/cache') / video_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Determine output path
    if not output:
        output = cache_dir / 'transcript.json'

    audio_path = cache_dir / 'audio.wav'

    # Override model size if specified
    transcription_config = config.get('transcription', {}).copy()
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

        # Track which config parameters changed
        changed_fields = []
        if cached_model != current_model:
            changed_fields.append(f"model_size: {cached_model} → {current_model}")
        if current_device != 'auto' and cached_device != current_device:
            changed_fields.append(f"device: {cached_device} → {current_device}")

        if changed_fields:
            print(f"\n⚠️  Cache invalid: {', '.join(changed_fields)}")
            print("   Re-transcribing with new configuration...")
            logger.info(f"Cache invalidated: {', '.join(changed_fields)}")
            cache_valid = False
        else:
            print(f"\n✓ Cached transcript found: {output}")
            print("Use --force to re-transcribe")
            logger.info(f"Using cached transcript: {output}")

            print("\nCached transcript info:")
            print(f"  Duration: {cached.get('duration', 'unknown')}s")
            print(f"  Segments: {cached.get('segment_count', 'unknown')}")
            print(f"  Model: {cached_model}")
            print(f"  Device: {cached_device}")
            print(f"  Processed: {cached_metadata.get('processed_at', 'unknown')}")
            cache_valid = True

    if cache_valid:
        return output, True

    start_time = time.time()

    # Extract audio
    print("\nExtracting audio from video...")
    logger.info("Starting audio extraction")

    audio_config = config.get('transcription', {})
    extractor = AudioExtractor(audio_config)
    extraction_result = extractor.extract(str(video_path), str(audio_path))

    print(
        f"✓ Audio extracted: {extraction_result['output_size_mb']:.1f} MB, "
        f"{extraction_result['duration_seconds']:.1f}s"
    )
    logger.info(f"Audio extraction complete: {extraction_result}")

    # Transcribe audio
    print("\nTranscribing audio with Whisper...")
    logger.info("Starting transcription")

    # transcription_config already set earlier for cache validation
    transcriber = WhisperTranscriber(transcription_config)
    transcription_result = transcriber.transcribe(str(audio_path))

    elapsed = time.time() - start_time
    duration = transcription_result['duration']
    rtf = duration / elapsed if elapsed > 0 else 0

    print(
        f"✓ Transcribed {transcription_result['segment_count']} segments "
        f"in {elapsed:.1f}s (RTF: {rtf:.1f}x real-time)"
    )
    logger.info(f"Transcription complete: {transcription_result['segment_count']} segments")

    # Build output with metadata
    output_data = {
        'metadata': {
            'video_path': str(video_path),
            'processed_at': datetime.now(UTC).isoformat(),
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

    print(f"\n{'='*60}")
    print("Transcription Summary:")
    print(f"{'='*60}")
    print(f"  Duration:           {duration:.1f}s ({duration/60:.1f} min)")
    print(f"  Segments:           {transcription_result['segment_count']}")
    print(f"  Language:           {transcription_result['language']}")
    print(f"  Model:              {output_data['metadata']['model_size']}")
    print(f"  Device:             {output_data['metadata']['device']}")
    print(f"  Processing time:    {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Real-time factor:   {rtf:.1f}x")
    print(f"{'='*60}")
    print(f"\nTranscript saved to: {output}")

    logger.info("Transcription completed successfully")
    logger.info(f"Output: {output}")

    return output, False


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
    cfg = load_config(config)
    setup_logging(cfg)
    logger = logging.getLogger(__name__)

    click.echo(f"Processing video: {video_path.name}")

    try:
        # Ignore cache_was_used return (CLI shows timing info already)
        _, _ = run_transcription(
            video_path=video_path,
            config=cfg,
            model_size=model_size,
            force=force,
            output=output
        )
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


def run_llm_prompt_generation(
    episode_id: str,
    include_hints: bool = True,
    force: bool = False,
    output: Path | None = None
) -> tuple[BuiltPrompt, Path, bool]:
    """
    Generate LLM prompt for episode analysis (pure business logic).

    Args:
        episode_id: Episode identifier (e.g., motd_2025-26_2025-11-01)
        include_hints: Whether to include OCR advisory hints
        force: Overwrite existing prompt file
        output: Optional output path (defaults to cache/{episode_id}/transcript_for_llm.txt)

    Returns:
        Tuple of (BuiltPrompt result, output path, cache_was_used)

    Raises:
        FileNotFoundError: If required cache files are missing
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating LLM prompt for: {episode_id}")

    # Determine cache path
    cache_path = Path("data/cache") / episode_id

    if not cache_path.exists():
        raise FileNotFoundError(f"Cache folder not found: {cache_path}")

    # Determine output path
    if output is None:
        output = cache_path / "transcript_for_llm.txt"

    # Check if output exists and we're not forcing regeneration
    if output.exists() and not force:
        logger.info(f"LLM prompt already exists, using cache: {output}")
        # Build the result to return stats (prompt building is fast, ~10ms)
        builder = PromptBuilder(cache_path, include_hints=include_hints)
        result = builder.build()
        return result, output, True

    # Build the prompt
    builder = PromptBuilder(cache_path, include_hints=include_hints)
    result = builder.build()

    # Write to file
    with open(output, "w") as f:
        f.write(result.content)

    logger.info(f"LLM prompt generated: {output}")
    logger.info(f"  Fixtures: {result.fixture_count}")
    logger.info(f"  Segments: {result.transcript_stats.segment_count}")
    logger.info(f"  Estimated tokens: ~{result.estimated_tokens:,}")

    return result, output, False


@cli.command("run")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force full pipeline run, ignoring cache"
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/config.yaml"),
    help="Path to configuration file"
)
def run_command(video_path: Path, force: bool, config: Path):
    """
    Run full MOTD analysis pipeline with automatic stage management.

    This command orchestrates all 4 pipeline stages sequentially:
    1. Scene Detection (video → scenes.json + frames/)
    2. Team Extraction (scenes.json → ocr_results.json)
    3. Transcription (video → transcript.json)
    4. LLM Prompt Generation (→ transcript_for_llm.txt)

    Smart caching automatically skips completed stages (unless --force).

    Example:
        motd run data/videos/motd_2025-26_2025-11-01.mp4
        motd run data/videos/motd_2025-26_2025-11-01.mp4 --force
    """
    # Load configuration
    config_data = load_config(config)
    setup_logging(config_data)

    logger = logging.getLogger(__name__)
    logger.info(f"Starting pipeline run for {video_path}")
    logger.info(f"Force mode: {force}")

    # Derive episode ID from video filename
    episode_id = video_path.stem
    logger.info(f"Episode ID: {episode_id}")

    # Validate episode exists in manifest
    manifest_path = Path("data/episodes/episode_manifest.json")
    if not manifest_path.exists():
        click.echo(f"\n❌ Error: Episode manifest not found at {manifest_path}", err=True)
        click.echo("   Create manifest file first.", err=True)
        sys.exit(1)

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        episodes = manifest.get("episodes", [])
        episode_ids = [ep["episode_id"] for ep in episodes]

        if episode_id not in episode_ids:
            click.echo(f"\n❌ Error: Episode '{episode_id}' not found in manifest", err=True)
            click.echo(f"   Available episodes: {', '.join(episode_ids[:3])}...", err=True)
            click.echo(f"   Add episode to {manifest_path} first.", err=True)
            sys.exit(1)

        logger.info("Episode validated in manifest")

    except Exception as e:
        logger.error(f"Failed to validate episode manifest: {e}", exc_info=True)
        click.echo(f"\n❌ Error reading manifest: {e}", err=True)
        sys.exit(1)

    # Run pipeline
    try:
        from motd.pipeline.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator(
            video_path=video_path,
            config=config_data,
            force=force
        )

        result, output_path = orchestrator.run_pipeline()

        # Display LLM prompt summary
        click.echo(f"\n{'='*60}")
        click.echo("LLM Prompt Generated:")
        click.echo(f"{'='*60}")
        click.echo(f"  Output: {output_path}")
        click.echo(f"  Fixtures: {result.fixture_count}")
        click.echo(f"  Transcript segments: {result.transcript_stats.segment_count}")
        click.echo(f"  OCR hints: {'Yes' if result.has_ocr_hints else 'No'}")
        click.echo(f"  Estimated tokens: ~{result.estimated_tokens:,}")
        click.echo(f"{'='*60}")

        click.echo("\n📋 To analyse, copy the prompt into Claude:")
        click.echo(f"   cat {output_path} | pbcopy  # macOS")
        click.echo("   Then paste into https://claude.ai")

        logger.info("Pipeline completed successfully")

    except FileNotFoundError as e:
        logger.error(f"Pipeline failed - file not found: {e}", exc_info=True)
        click.echo(f"\n❌ Pipeline Error: {e}", err=True)
        click.echo("\n   Check that all required files exist:", err=True)
        click.echo(f"   - data/cache/{episode_id}/ocr_results.json", err=True)
        click.echo(f"   - data/cache/{episode_id}/transcript.json", err=True)
        click.echo("   - data/fixtures/premier_league_2025_26.json", err=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        click.echo(f"\n❌ Pipeline Error: {e}", err=True)
        click.echo(f"\n   To resume, run: motd run {video_path}", err=True)
        sys.exit(1)


@cli.command("generate-llm-prompt")
@click.argument("episode_id")
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=None,
    help='Output path for prompt file (default: cache/{episode_id}/transcript_for_llm.txt)'
)
@click.option(
    '--include-hints/--no-hints',
    default=True,
    help='Include OCR advisory hints (FT graphics, scoreboards)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing prompt file'
)
def generate_llm_prompt_command(
    episode_id: str,
    output: Path | None,
    include_hints: bool,
    force: bool
):
    """
    Generate LLM-ready prompt from transcript for episode analysis.

    Creates a prompt file containing fixtures, instructions, output schema,
    optional OCR hints, and the deduplicated transcript. Ready for copy-paste
    into Claude web UI.

    EPISODE_ID should be in format: motd_2025-26_2025-11-22

    Example:

        python -m motd generate-llm-prompt motd_2025-26_2025-11-22
    """
    logger = logging.getLogger(__name__)

    # Determine cache path
    cache_path = Path("data/cache") / episode_id

    if not cache_path.exists():
        click.echo(f"Error: Cache folder not found: {cache_path}", err=True)
        click.echo("\nMake sure the episode has been processed first:", err=True)
        click.echo(f"  python -m motd run data/videos/{episode_id}.mp4", err=True)
        sys.exit(1)

    # Determine output path
    if output is None:
        output = cache_path / "transcript_for_llm.txt"

    # Check if output exists
    if output.exists() and not force:
        click.echo(f"Error: Output file already exists: {output}", err=True)
        click.echo("  Use --force to overwrite", err=True)
        sys.exit(1)

    click.echo(f"Generating LLM prompt for: {episode_id}")
    click.echo(f"  Cache path: {cache_path}")
    click.echo(f"  Include OCR hints: {include_hints}")

    try:
        # Build the prompt
        builder = PromptBuilder(cache_path, include_hints=include_hints)
        result = builder.build()

        # Write to file
        with open(output, "w") as f:
            f.write(result.content)

        # Display summary
        click.echo("\n✓ Prompt generated successfully!")
        click.echo(f"\n  Output: {output}")
        click.echo(f"  Fixtures: {result.fixture_count}")
        click.echo(f"  Transcript segments: {result.transcript_stats.segment_count}")
        click.echo(f"  Deduplication: {result.transcript_stats.deduplication_stats.removed_count} duplicates removed")
        click.echo(f"  OCR hints: {'Yes' if result.has_ocr_hints else 'No'}")
        click.echo(f"  Estimated tokens: ~{result.estimated_tokens:,}")
        click.echo(f"  File size: {output.stat().st_size / 1024:.1f} KB")

        click.echo("\n📋 To analyse, copy the contents of this file into Claude:")
        click.echo(f"   cat {output} | pbcopy  # macOS")
        click.echo("   Then paste into https://claude.ai")

    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        click.echo(f"\nError: {e}", err=True)
        click.echo("\nMake sure the episode has been processed:", err=True)
        click.echo("  - Transcription: python -m motd transcribe <video>", err=True)
        click.echo(f"  - OCR (optional): python -m motd extract-teams --episode {episode_id}", err=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Prompt generation failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
