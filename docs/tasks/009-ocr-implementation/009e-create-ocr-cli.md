# Task 009e: Create OCR CLI Command

## Objective
Wire up OCR reader, team matcher, and fixture matcher into a CLI command with smart filtering based on reconnaissance findings.

## Prerequisites
- Task 009d completed (fixture matcher working)
- All OCR modules implemented: reader, team_matcher, fixture_matcher
- Pattern documentation from 009a provides filtering guidance

## Tasks

### 1. Create CLI Command (45-60 min)
- [ ] Add `extract-teams` command to `src/motd/__main__.py`
- [ ] Follow Click framework pattern from `detect-scenes` command
- [ ] Accept parameters:
  - [ ] `--scenes`: Path to scenes JSON (from Task 008)
  - [ ] `--episode-id`: Episode identifier
  - [ ] `--output`: Output path for OCR results JSON
  - [ ] Optional `--config`: Config file path (default: config/config.yaml)
- [ ] Load config, fixtures, teams, manifest

### 2. Implement Smart Scene Filtering (30-45 min)
- [ ] Review filtering recommendations from `docs/motd_visual_patterns.md`
- [ ] Implement filters based on 009a findings (target: 810 → 160-240 scenes, 70-80% reduction):
  - [ ] Skip intro: First 50 seconds (scenes 1-125, ~15%)
  - [ ] Skip MOTD 2 interlude: 52:01-52:47 (scenes ~580-600, ~2-3%)
  - [ ] Skip short transitions: <2 seconds duration (~200 scenes, 25%)
  - [ ] Skip studio via process-of-elimination: Non-highlights/interviews (~100 scenes, 12%)
  - [ ] Skip interviews: Post-match interviews identified (~50 scenes, 6%)
  - [ ] Keep highlights with scoreboards/FT graphics: Target OCR regions (~160-240 scenes, 20-30%)
- [ ] Log filtering stats (e.g., "Filtered 810 → 183 scenes (77% reduction)")

### 3. Wire Up OCR Pipeline (30-45 min)
- [ ] For each scene (after filtering):
  - [ ] Load frame image
  - [ ] Run OCR on both regions (scoreboard, formation)
  - [ ] Extract text from OCR results
  - [ ] Match text against teams with fixture candidates
  - [ ] Validate against expected fixtures
  - [ ] Apply confidence boost if validated
- [ ] Aggregate results per scene
- [ ] Handle errors gracefully (log and continue)

### 4. Create Output JSON (20-30 min)
- [ ] Structure output with:
  - [ ] Episode metadata
  - [ ] Expected fixtures
  - [ ] Per-scene OCR results
  - [ ] Summary statistics
- [ ] Save to cache directory
- [ ] Pretty-print JSON for human readability

### 5. Add Progress Logging (15-20 min)
- [ ] Log processing progress (e.g., "Processing scene 50/243")
- [ ] Log OCR results as processed (team names detected)
- [ ] Log validation results (validated vs unexpected teams)
- [ ] Summary at end (total teams detected, accuracy)

## Implementation Details

### CLI Command Structure

Add to `src/motd/__main__.py`:

```python
@click.command()
@click.option(
    '--scenes',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to scenes JSON file from scene detection'
)
@click.option(
    '--episode-id',
    required=True,
    help='Episode identifier (e.g., motd_2025-26_2025-11-01)'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    help='Output path for OCR results JSON (default: cache/{episode_id}/ocr_results.json)'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    default=Path('config/config.yaml'),
    help='Path to config file'
)
def extract_teams(scenes: Path, episode_id: str, output: Optional[Path], config: Path):
    """Extract team names from video frames using OCR and fixture matching."""

    # Load config
    with open(config) as f:
        cfg = yaml.safe_load(f)

    # Setup logging
    setup_logging(cfg['logging'])
    logger = logging.getLogger(__name__)

    logger.info(f"Starting team extraction for episode: {episode_id}")

    # Load scenes
    with open(scenes) as f:
        scenes_data = json.load(f)

    total_scenes = len(scenes_data['scenes'])
    logger.info(f"Loaded {total_scenes} scenes")

    # Initialize OCR components
    ocr_reader = OCRReader(cfg['ocr'])
    team_matcher = TeamMatcher(Path('data/teams/premier_league_2025_26.json'))
    fixture_matcher = FixtureMatcher(
        Path('data/fixtures/premier_league_2025_26.json'),
        Path('data/episodes/episode_manifest.json')
    )

    # Get expected teams for fixture-aware matching
    expected_teams = fixture_matcher.get_expected_teams(episode_id)
    expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)
    logger.info(f"Expected {len(expected_fixtures)} fixtures with {len(expected_teams)} teams")

    # Filter scenes (based on 009a reconnaissance)
    filtered_scenes = filter_scenes(scenes_data['scenes'], cfg)
    logger.info(f"Filtered scenes: {total_scenes} → {len(filtered_scenes)}")

    # Process scenes
    ocr_results = []
    for idx, scene in enumerate(filtered_scenes, 1):
        if idx % 10 == 0:
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

    # Build output
    output_data = {
        'episode_id': episode_id,
        'video_path': scenes_data.get('video_path'),
        'total_scenes': total_scenes,
        'filtered_scenes': len(filtered_scenes),
        'expected_fixtures': [
            {
                'match_id': f['match_id'],
                'home_team': f['home_team'],
                'away_team': f['away_team']
            }
            for f in expected_fixtures
        ],
        'ocr_results': ocr_results,
        'summary': generate_summary(ocr_results, expected_teams)
    }

    # Save output
    if not output:
        cache_dir = Path('data/cache') / episode_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        output = cache_dir / 'ocr_results.json'

    with open(output, 'w') as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"OCR results saved to: {output}")
    logger.info(f"Summary: {output_data['summary']}")

# Add to cli group
cli.add_command(extract_teams)
```

### Scene Filtering Helper

```python
def filter_scenes(scenes: List[Dict], config: Dict) -> List[Dict]:
    """
    Filter scenes based on reconnaissance findings from 009a.

    Target: 810 → 160-240 scenes (70-80% reduction)

    Filters out:
    - Intro scenes (first 50 seconds)
    - MOTD 2 interlude (52:01-52:47)
    - Very short scenes (transitions <2 seconds)
    - Studio segments (process-of-elimination)
    - Interviews
    """
    filtering = config.get('ocr', {}).get('filtering', {})

    filtered = []

    # Skip intro (50 seconds = scenes 1-125, ~15%)
    intro_seconds = filtering.get('skip_intro_seconds', 50)

    # Skip MOTD 2 interlude (52:01-52:47)
    motd2_start = filtering.get('motd2_interlude_start', 3121)  # 52:01
    motd2_end = filtering.get('motd2_interlude_end', 3167)      # 52:47

    # Skip short scenes (transitions <2 seconds)
    min_duration = filtering.get('min_scene_duration', 2.0)

    for scene in scenes:
        # Skip intro
        if scene['start_seconds'] < intro_seconds:
            continue

        # Skip MOTD 2 interlude
        if motd2_start <= scene['start_seconds'] <= motd2_end:
            continue

        # Skip short scenes (transitions)
        if scene['duration'] < min_duration:
            continue

        # Process-of-elimination studio filtering:
        # Keep highlights/interviews (will have scoreboards or post-match content)
        # Studio = remainder (can be filtered post-OCR if no teams detected)

        filtered.append(scene)

    return filtered
```

### Scene Processing Helper

```python
def process_scene(
    scene: Dict,
    ocr_reader: OCRReader,
    team_matcher: TeamMatcher,
    fixture_matcher: FixtureMatcher,
    expected_teams: List[str],
    episode_id: str,
    logger
) -> Optional[Dict]:
    """Process single scene: OCR → team matching → validation."""

    try:
        frame_path = Path(scene['frames'][0])

        # Run OCR on all regions
        ocr_extractions = ocr_reader.extract_all_regions(frame_path)

        detected_teams = []

        # Process each region
        for region_name, texts in ocr_extractions.items():
            if isinstance(texts, dict) and 'error' in texts:
                continue

            # Combine text from region
            combined_text = ' '.join([t['text'] for t in texts])

            if not combined_text:
                continue

            # Match teams (with fixture candidates)
            matches = team_matcher.match_multiple(
                combined_text,
                candidate_teams=expected_teams,
                max_teams=2
            )

            for match in matches:
                detected_teams.append({
                    'team': match['team'],
                    'confidence': match['confidence'],
                    'region': region_name,
                    'matched_text': match['matched_text']
                })

        if not detected_teams:
            return None

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
            'detected_teams': detected_teams,
            'validation': validation,
            'matched_fixture': matched_fixture['match_id'] if matched_fixture else None
        }

    except Exception as e:
        logger.error(f"Error processing scene {scene['scene_id']}: {e}")
        return None
```

### Summary Generator

```python
def generate_summary(ocr_results: List[Dict], expected_teams: List[str]) -> Dict:
    """Generate summary statistics."""

    all_detected = set()
    validated_count = 0
    unexpected_count = 0

    for result in ocr_results:
        teams = [t['team'] for t in result['detected_teams']]
        all_detected.update(teams)

        validated_count += len(result['validation']['validated_teams'])
        unexpected_count += len(result['validation']['unexpected_teams'])

    return {
        'total_scenes_processed': len(ocr_results),
        'unique_teams_detected': len(all_detected),
        'expected_teams_found': len(all_detected & set(expected_teams)),
        'validated_detections': validated_count,
        'unexpected_detections': unexpected_count
    }
```

### Config Updates

Add to `config/config.yaml`:

```yaml
ocr:
  filtering:
    skip_intro_seconds: 50           # Skip first 50 seconds (intro + theme song)
    motd2_interlude_start: 3121      # MOTD 2 interlude start (52:01)
    motd2_interlude_end: 3167        # MOTD 2 interlude end (52:47)
    min_scene_duration: 2.0          # Skip scenes <2 seconds (transitions)
    # Target: 810 → 160-240 scenes (70-80% reduction)
```

## Success Criteria
- [ ] `extract-teams` command added to CLI
- [ ] Command accepts all required parameters
- [ ] Loads config, fixtures, teams, manifest successfully
- [ ] Implements scene filtering based on 009a findings
- [ ] Processes scenes through OCR pipeline
- [ ] Outputs structured JSON with results
- [ ] Logs progress and summary statistics
- [ ] Handles errors gracefully (doesn't crash on bad frame)
- [ ] Output JSON is valid and human-readable
- [ ] Code follows Python guidelines (type hints, docstrings)

## Estimated Time
1 hour:
- CLI command: 45-60 min
- Scene filtering: 30-45 min
- Pipeline wiring: 30-45 min
- Output JSON: 20-30 min
- Logging: 15-20 min

## Testing

Run the command manually:

```bash
python -m motd extract-teams \
  --scenes data/cache/motd_2025-26_2025-11-01/scenes.json \
  --episode-id motd_2025-26_2025-11-01 \
  --output data/cache/motd_2025-26_2025-11-01/ocr_results.json
```

Expected output:
- Filters 810 → 160-240 scenes (70-80% reduction based on 009a findings)
- Processes each scene with OCR (FT scores primary, scoreboards backup)
- Detects teams from expected fixtures via fuzzy matching
- Saves results to JSON with validation metadata

## Output Files
- `src/motd/__main__.py` (updated with new command)
- `config/config.yaml` (updated with filtering config)

## Next Task
[009f-run-ocr-on-test-video.md](009f-run-ocr-on-test-video.md) - Execute CLI and collect results
