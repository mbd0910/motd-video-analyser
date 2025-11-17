# Task 011e: Pipeline Orchestrator & CLI Implementation

## Objective
Wire all analysis components together into an end-to-end pipeline with caching, error handling, and a CLI command. This is the integration layer that produces the final analysis output.

## Prerequisites
- [x] Task 011d complete (airtime calculator)
- [x] All analysis components ready (segment classifier, match boundary detector, airtime calculator)

## Estimated Time
2-2.5 hours

## What This Component Does

### Pipeline Flow
```
Input: video.mp4 path

1. Check cache for existing analysis.json
   ├─ If exists + not --force → Return cached
   └─ If missing or --force → Continue

2. Load cached intermediate data
   ├─ scenes.json (from Task 008)
   ├─ ocr_results.json (from Task 009)
   └─ transcript.json (from Task 010)

3. Run analysis pipeline
   ├─ Segment Classifier → classified_scenes.json
   ├─ Match Boundary Detector → matches.json
   └─ Airtime Calculator → airtime.json

4. Merge all results into final output
   └─ Validate against PRD schema

5. Write final analysis.json
   └─ Cache for future runs

Output: analysis.json (PRD-compliant)
```

## Implementation Steps

### 1. Create Module Structure
- [ ] Create `src/motd/pipeline/` directory
- [ ] Create `src/motd/pipeline/__init__.py`
- [ ] Create `src/motd/pipeline/orchestrator.py`

### 2. Implement PipelineOrchestrator Class

```python
class PipelineOrchestrator:
    """Orchestrates the full analysis pipeline from cached data to final output."""

    def __init__(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        force: bool = False
    ):
        """
        Args:
            video_path: Path to video file
            output_path: Optional output path for analysis.json
            cache_dir: Optional cache directory (auto-detected if not provided)
            force: Force re-run even if cached output exists
        """
        self.video_path = Path(video_path)
        self.force = force

        # Auto-detect cache directory
        if cache_dir is None:
            episode_id = self._extract_episode_id(video_path)
            self.cache_dir = Path("data/cache") / episode_id
        else:
            self.cache_dir = Path(cache_dir)

        # Set output path
        if output_path is None:
            self.output_path = self.cache_dir / "analysis.json"
        else:
            self.output_path = Path(output_path)

        logger.info(f"Pipeline initialized for {self.video_path.name}")
        logger.info(f"Cache directory: {self.cache_dir}")
        logger.info(f"Output path: {self.output_path}")

    def run(self) -> Dict:
        """
        Run the full analysis pipeline.

        Returns:
            Final analysis dictionary (PRD-compliant)
        """
        pass

    def _check_cache(self) -> Optional[Dict]:
        """Check if cached analysis.json exists and is valid."""
        pass

    def _load_cached_data(self) -> Dict:
        """Load all cached intermediate data (scenes, OCR, transcript)."""
        pass

    def _run_segment_classifier(self, data: Dict) -> List[Dict]:
        """Run segment classification."""
        pass

    def _run_match_boundary_detector(self, classified_scenes: List[Dict], data: Dict) -> List[Dict]:
        """Run match boundary detection."""
        pass

    def _run_airtime_calculator(self, matches: List[Dict], scenes: List[Dict]) -> List[Dict]:
        """Run airtime calculation."""
        pass

    def _merge_results(self, matches_with_airtime: List[Dict]) -> Dict:
        """Merge all results into final PRD-compliant structure."""
        pass

    def _validate_output(self, output: Dict) -> None:
        """Validate output matches PRD schema."""
        pass

    def _write_output(self, output: Dict) -> None:
        """Write final analysis to JSON file."""
        pass
```

### 3. Implement Cache Management

```python
def _check_cache(self) -> Optional[Dict]:
    """Check if cached analysis.json exists and is valid."""

    if self.force:
        logger.info("Force mode enabled, ignoring cached output")
        return None

    if not self.output_path.exists():
        logger.info("No cached output found")
        return None

    try:
        with open(self.output_path) as f:
            cached_output = json.load(f)

        # Validate cached output has required fields
        if "episode_date" in cached_output and "matches" in cached_output:
            logger.info("Using cached analysis output")
            return cached_output
        else:
            logger.warning("Cached output is invalid, re-running pipeline")
            return None

    except json.JSONDecodeError as e:
        logger.error(f"Failed to load cached output: {e}")
        return None

def _load_cached_data(self) -> Dict:
    """Load all cached intermediate data."""

    data = {}

    # Load scenes
    scenes_path = self.cache_dir / "scenes.json"
    if not scenes_path.exists():
        raise FileNotFoundError(f"scenes.json not found at {scenes_path}")
    with open(scenes_path) as f:
        data["scenes"] = json.load(f)
    logger.info(f"Loaded {len(data['scenes'])} scenes")

    # Load OCR results
    ocr_path = self.cache_dir / "ocr_results.json"
    if not ocr_path.exists():
        raise FileNotFoundError(f"ocr_results.json not found at {ocr_path}")
    with open(ocr_path) as f:
        data["ocr_results"] = json.load(f)
    logger.info(f"Loaded OCR results for {len(data['ocr_results'])} scenes")

    # Load transcript
    transcript_path = self.cache_dir / "transcript.json"
    if not transcript_path.exists():
        raise FileNotFoundError(f"transcript.json not found at {transcript_path}")
    with open(transcript_path) as f:
        data["transcript"] = json.load(f)
    logger.info(f"Loaded transcript with {len(data['transcript']['segments'])} segments")

    # Load team data
    team_data_path = Path("data/teams/premier_league_2025_26.json")
    if not team_data_path.exists():
        raise FileNotFoundError(f"Team data not found at {team_data_path}")
    with open(team_data_path) as f:
        data["team_data"] = json.load(f)
    logger.info(f"Loaded {len(data['team_data']['teams'])} teams")

    return data
```

### 4. Implement Pipeline Execution

```python
def run(self) -> Dict:
    """Run the full analysis pipeline."""

    # Check cache first
    cached_output = self._check_cache()
    if cached_output is not None:
        return cached_output

    # Load all cached intermediate data
    logger.info("Loading cached intermediate data...")
    data = self._load_cached_data()

    # Step 1: Segment Classification
    logger.info("Running segment classification...")
    classified_scenes = self._run_segment_classifier(data)
    logger.info(f"Classified {len(classified_scenes)} scenes")

    # Step 2: Match Boundary Detection
    logger.info("Running match boundary detection...")
    matches = self._run_match_boundary_detector(classified_scenes, data)
    logger.info(f"Detected {len(matches)} matches")

    # Step 3: Airtime Calculation
    logger.info("Running airtime calculation...")
    matches_with_airtime = self._run_airtime_calculator(matches, data["scenes"])
    logger.info("Airtime calculated for all matches")

    # Step 4: Merge Results
    logger.info("Merging results into final output...")
    output = self._merge_results(matches_with_airtime)

    # Step 5: Validate Output
    logger.info("Validating output against PRD schema...")
    self._validate_output(output)

    # Step 6: Write Output
    logger.info(f"Writing output to {self.output_path}...")
    self._write_output(output)

    logger.info("Pipeline complete!")
    return output
```

### 5. Implement Output Merging (PRD Schema)

```python
def _merge_results(self, matches_with_airtime: List[Dict]) -> Dict:
    """Merge all results into final PRD-compliant structure."""

    # Extract episode date from video filename or cache directory
    episode_date = self._extract_episode_date()

    # Build final structure
    output = {
        "episode_date": episode_date,
        "video_path": str(self.video_path),
        "total_matches": len(matches_with_airtime),
        "matches": []
    }

    # Format each match according to PRD schema
    for match in matches_with_airtime:
        match_output = {
            "running_order": match["running_order"],
            "teams": match["teams"],
            "match_id": match["match_id"],
            "segments": match["segments"],
            "total_airtime_seconds": match["total_airtime_seconds"]
        }
        output["matches"].append(match_output)

    return output
```

### 6. Implement Schema Validation

```python
def _validate_output(self, output: Dict) -> None:
    """Validate output matches PRD schema (section 3.4)."""

    # Required top-level fields
    required_fields = ["episode_date", "matches"]
    for field in required_fields:
        if field not in output:
            raise ValueError(f"Missing required field: {field}")

    # Validate matches
    if not isinstance(output["matches"], list):
        raise ValueError("matches must be a list")

    for i, match in enumerate(output["matches"]):
        # Required match fields
        match_fields = ["running_order", "teams", "segments", "total_airtime_seconds"]
        for field in match_fields:
            if field not in match:
                raise ValueError(f"Match {i}: Missing required field: {field}")

        # Validate running order is sequential
        if match["running_order"] != i + 1:
            raise ValueError(f"Match {i}: running_order should be {i+1}, got {match['running_order']}")

        # Validate teams is list of 2
        if not isinstance(match["teams"], list) or len(match["teams"]) != 2:
            raise ValueError(f"Match {i}: teams must be list of 2 team names")

        # Validate segments
        for seg in match["segments"]:
            if "type" not in seg or "duration_seconds" not in seg:
                raise ValueError(f"Match {i}: Invalid segment structure")

            valid_types = ["studio_intro", "highlights", "interviews", "studio_analysis"]
            if seg["type"] not in valid_types:
                raise ValueError(f"Match {i}: Invalid segment type: {seg['type']}")

    logger.info("Output validation passed")
```

### 7. Implement Error Handling

```python
def run(self) -> Dict:
    """Run the full analysis pipeline with error handling."""

    try:
        # ... (pipeline steps)
        return output

    except FileNotFoundError as e:
        logger.error(f"Missing cached data: {e}")
        logger.error("Please run scene detection (008), OCR (009), and transcription (010) first")
        raise

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error in pipeline: {e}")
        logger.error("Pipeline failed - see logs for details")
        raise
```

### 8. Implement CLI Command

- [ ] Update `src/motd/__main__.py` to add `process` command

```python
@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output path for analysis.json")
@click.option("--cache-dir", type=click.Path(), help="Cache directory (auto-detected if not provided)")
@click.option("--force", is_flag=True, help="Force re-run even if cached output exists")
def process(video_path: str, output: Optional[str], cache_dir: Optional[str], force: bool):
    """
    Run full analysis pipeline on a video.

    Combines scene detection, OCR, transcription, and analysis into final output.

    Example:
        python -m motd process data/videos/video.mp4
        python -m motd process data/videos/video.mp4 --output analysis.json --force
    """
    from motd.pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(
        video_path=video_path,
        output_path=output,
        cache_dir=cache_dir,
        force=force
    )

    try:
        result = orchestrator.run()
        click.echo(f"✓ Analysis complete: {orchestrator.output_path}")
        click.echo(f"  Detected {result['total_matches']} matches")
    except Exception as e:
        click.echo(f"✗ Pipeline failed: {e}", err=True)
        sys.exit(1)
```

### 9. Implement Unit Tests

- [ ] Create `tests/unit/pipeline/test_orchestrator.py`
- [ ] Test cache checking
- [ ] Test data loading
- [ ] Test pipeline execution (mock components)
- [ ] Test output merging
- [ ] Test schema validation
- [ ] Test error handling
- [ ] Test CLI command

### 10. Integration Testing

- [ ] Run full pipeline on test video
- [ ] Verify all steps execute without errors
- [ ] Verify output file is created
- [ ] Verify output matches PRD schema
- [ ] Test --force flag (re-run)
- [ ] Test with missing cached data (error handling)
- [ ] Test caching (second run should be instant)

## Deliverables

### 1. Source Code
- `src/motd/pipeline/__init__.py`
- `src/motd/pipeline/orchestrator.py`
- Updated `src/motd/__main__.py` with `process` command

### 2. Tests
- `tests/unit/pipeline/test_orchestrator.py`
- Integration test script

### 3. Documentation
- Docstrings for all classes/methods
- CLI help text
- Example usage

## Success Criteria
- [ ] PipelineOrchestrator class implemented
- [ ] Cache management working (check/load/write)
- [ ] All pipeline steps orchestrated correctly
- [ ] Output merging produces PRD-compliant JSON
- [ ] Schema validation working
- [ ] Error handling for missing data
- [ ] CLI `process` command working
- [ ] Unit tests passing
- [ ] Integration test successful on full video
- [ ] Caching works (second run is instant)
- [ ] Code follows Python style guidelines
- [ ] Ready for 011f (validation)

## Testing Commands

```bash
# Run unit tests
pytest tests/unit/pipeline/test_orchestrator.py -v

# Run full pipeline
python -m motd process data/videos/motd_2025-26_2025-11-01.mp4

# Force re-run
python -m motd process data/videos/motd_2025-26_2025-11-01.mp4 --force

# Custom output path
python -m motd process data/videos/motd_2025-26_2025-11-01.mp4 \
  --output data/output/analysis.json

# Test caching (should be instant)
time python -m motd process data/videos/motd_2025-26_2025-11-01.mp4
time python -m motd process data/videos/motd_2025-26_2025-11-01.mp4  # Should be <1 second
```

## Example Output

```json
{
  "episode_date": "2025-11-01",
  "video_path": "data/videos/motd_2025-26_2025-11-01.mp4",
  "total_matches": 7,
  "matches": [
    {
      "running_order": 1,
      "teams": ["Liverpool", "Aston Villa"],
      "match_id": "2025-11-01-liverpool-astonvilla",
      "segments": [
        {
          "type": "studio_intro",
          "duration_seconds": 20,
          "scene_count": 1
        },
        {
          "type": "highlights",
          "duration_seconds": 518,
          "scene_count": 90
        },
        {
          "type": "interviews",
          "duration_seconds": 52,
          "scene_count": 5
        },
        {
          "type": "studio_analysis",
          "duration_seconds": 201,
          "scene_count": 9,
          "first_team_mentioned": "Liverpool"
        }
      ],
      "total_airtime_seconds": 791
    }
  ]
}
```

## Edge Cases to Handle

1. **Missing cached data**: Error with helpful message
2. **Invalid cached output**: Re-run pipeline
3. **Component failures**: Wrap in try-except, log details
4. **Schema validation failures**: Clear error messages
5. **File write permissions**: Check before running
6. **Cache directory doesn't exist**: Create it
7. **Multiple videos with same name**: Use full path for cache key

## Notes
- This is the "glue" that ties everything together
- Focus on clean error handling - failures should be debuggable
- Caching is critical - never re-run Whisper unnecessarily
- Output must be PRD-compliant for downstream use
- CLI should be user-friendly with good help text
- Logging at each step helps with debugging
- Make it easy to run pipeline multiple times during development

## Next Task
[011f-validation.md](011f-validation.md)
