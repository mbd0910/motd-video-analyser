# Match of the Day Analyser - Technical Architecture

## 1. System Overview

### Design Principles

1. **Modularity**: Each pipeline stage operates independently with clear input/output contracts
2. **Caching**: Intermediate results are cached to avoid expensive re-processing
3. **Reproducibility**: Same input + same config = same output, always
4. **Fail Gracefully**: Pipeline continues if one component fails; errors logged but don't block progress
5. **Validation-First**: Build tools for manual validation before full automation

### High-Level Pipeline Flow

```
┌─────────────────┐
│   Video Input   │
│   (MP4 file)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Scene Detection               │
│   • Detect frame transitions    │
│   • Extract key frames          │
│   • Output: scenes.json         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   OCR Processing                │
│   • Crop to regions of interest │
│   • Extract team names          │
│   • Validate against team list  │
│   • Output: ocr_results.json    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Audio Transcription           │
│   • Extract audio track         │
│   • Whisper transcription       │
│   • Output: transcript.json     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Analysis & Classification     │
│   • Segment classification      │
│   • Team mention detection      │
│   • Airtime calculation         │
│   • Output: analysis.json       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Validation (Optional)         │
│   • Load manual_labels.json     │
│   • Compare with automated      │
│   • Generate validation report  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Final Output                  │
│   • Merge all results           │
│   • Apply manual corrections    │
│   • Generate final JSON         │
└─────────────────────────────────┘
```

---

## 2. Project Structure

```
motd-analyzer/
├── src/
│   ├── motd_analyzer/
│   │   ├── __init__.py
│   │   ├── __main__.py              # CLI entry point
│   │   │
│   │   ├── scene_detection/
│   │   │   ├── __init__.py
│   │   │   ├── detector.py          # PySceneDetect integration
│   │   │   └── frame_extractor.py   # Extract key frames at transitions
│   │   │
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   ├── reader.py            # EasyOCR integration
│   │   │   ├── team_matcher.py      # Match OCR text to team names
│   │   │   ├── fixture_matcher.py   # Match OCR teams to fixture data
│   │   │   └── regions.py           # Define ROI for scoreboard/formations
│   │   │
│   │   ├── transcription/
│   │   │   ├── __init__.py
│   │   │   ├── whisper_transcriber.py  # Whisper integration
│   │   │   └── audio_extractor.py      # Extract audio from video
│   │   │
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── segment_classifier.py   # Classify scene types
│   │   │   ├── team_mention_detector.py # Find first team mentions
│   │   │   └── airtime_calculator.py    # Calculate durations
│   │   │
│   │   ├── validation/
│   │   │   ├── __init__.py
│   │   │   ├── manual_labeler.py       # Interactive labeling tool
│   │   │   └── comparator.py           # Compare auto vs manual
│   │   │
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py         # Main pipeline coordinator
│   │   │   ├── cache_manager.py        # Handle caching logic
│   │   │   └── config_loader.py        # Load YAML config
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── video_utils.py          # Video processing helpers
│   │       ├── json_utils.py           # JSON I/O helpers
│   │       └── logging_config.py       # Logging setup
│   │
│   └── setup.py
│
├── data/
│   ├── teams/
│   │   └── premier_league_2025_26.json  # Team names + variations
│   ├── fixtures/
│   │   └── premier_league_2025_26.json  # Match schedules for season
│   ├── episodes/
│   │   └── episode_manifest.json        # Video-to-fixture mapping
│   ├── videos/                           # Input videos (gitignored)
│   ├── cache/                            # Intermediate results (gitignored)
│   │   └── {episode_id}/
│   │       ├── scenes.json
│   │       ├── ocr_results.json
│   │       ├── fixture_matches.json
│   │       ├── transcript.json
│   │       ├── manual_labels.json
│   │       └── frames/
│   └── output/                           # Final JSON outputs
│       └── {episode_id}_analysis.json
│
├── config/
│   └── config.yaml                       # Pipeline configuration
│
├── tests/
│   ├── test_scene_detection.py
│   ├── test_ocr.py
│   ├── test_transcription.py
│   └── test_pipeline.py
│
├── docs/
│   ├── prd.md
│   ├── architecture.md
│   ├── tech-tradeoffs.md
│   └── roadmap.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 3. Technology Stack

For detailed comparisons of alternatives, see [tech-tradeoffs.md](tech-tradeoffs.md).

| Component | Library | Rationale |
|-----------|---------|-----------|
| **Scene Detection** | PySceneDetect | Purpose-built for scene transitions, handles fades/dissolves |
| **OCR** | EasyOCR | Better accuracy on stylized sports graphics, GPU support |
| **Transcription** | Whisper (local, large-v3) | State-of-the-art accuracy, runs well on M3 Pro |
| **Video Processing** | ffmpeg + opencv-python | Industry standard, comprehensive functionality |
| **Configuration** | PyYAML | Simple, human-readable config files |
| **CLI** | argparse (or click) | Standard Python CLI framework |

---

## 4. Pipeline Stages (Detailed)

### 4.1 Scene Detection

**Purpose**: Identify transitions between segments (studio → highlights → interview → analysis)

**Input**:
- Video file path (MP4)
- Config: threshold, min_scene_duration

**Output** (`cache/{episode_id}/scenes.json`):
```json
{
  "video_path": "data/videos/motd_2024_08_17.mp4",
  "total_scenes": 45,
  "scenes": [
    {
      "scene_id": 1,
      "start_time": "00:01:30.5",
      "end_time": "00:02:15.2",
      "start_frame": 2715,
      "end_frame": 4056,
      "duration_seconds": 44.7,
      "key_frame_path": "cache/{episode_id}/frames/scene_001.jpg"
    }
  ],
  "metadata": {
    "processed_at": "2024-11-06T10:30:00Z",
    "config": {"threshold": 30.0, "min_scene_duration": 3}
  }
}
```

**Caching**: Scene detection is expensive (~5-10 mins per video). Cache aggressively.

**Error Handling**:
- If 0 scenes detected → abort, something is wrong
- If >200 scenes detected → warn (threshold too sensitive), suggest tuning

---

### 4.2 OCR Processing

**Purpose**: Extract team names from scoreboard graphics and validate against known fixtures

**Input**:
- Key frames from scene detection
- Config: ROI coordinates, team names list, fixtures data
- Episode date (from manifest)

**Process**:
1. Load key frame
2. Crop to regions of interest:
   - Top-left: `[0, 0, 400, 100]` (scoreboard)
   - Bottom-right: `[800, 600, 1920, 1080]` (formation graphic - adjust for resolution)
3. Run EasyOCR on cropped regions
4. Match extracted text against team name list (fuzzy matching)
5. Cross-reference with fixture data for episode date (limits search to 6-8 expected matches)
6. If fixture match found with confidence > 0.7, boost confidence and use canonical team names
7. If no fixture match or low confidence, flag for manual review

**Output** (`cache/{episode_id}/ocr_results.json`):
```json
{
  "scene_id": 5,
  "key_frame": "cache/{episode_id}/frames/scene_005.jpg",
  "ocr_results": [
    {
      "region": "scoreboard",
      "raw_text": "Arsenal 2-1 Chelsea",
      "detected_teams": ["Arsenal", "Chelsea"],
      "confidence": 0.92
    },
    {
      "region": "formation",
      "raw_text": "ARSENAL 4-3-3 / CHELSEA 3-4-3",
      "detected_teams": ["Arsenal", "Chelsea"],
      "confidence": 0.88
    }
  ],
  "final_teams": {
    "home": "Arsenal",
    "away": "Chelsea",
    "confidence": 0.92
  },
  "fixture_match": {
    "found": true,
    "fixture_id": "2024-08-17-arsenal-chelsea",
    "confidence_boost": 0.15
  }
}
```

**Caching**: OCR results are cached per scene. If you change team list, re-run matching only (not OCR).

**Error Handling**:
- If no teams detected → log warning, continue
- If 1 team detected → log warning (expected 2), flag for manual review
- If 3+ teams detected → log error, flag for manual review

---

### 4.3 Fixture Matching

**Purpose**: Validate OCR results against known fixture data to improve accuracy

**Input**:
- OCR results with detected teams
- Fixture data for the season
- Episode date (from manifest)

**Process**:
1. Load fixtures for episode date (±1 day tolerance for recording delays)
2. Extract candidate matches (typically 6-8 fixtures per episode)
3. For each OCR team pair:
   - Calculate similarity score against each fixture (using fuzzy matching)
   - Find best matching fixture
   - If similarity > 0.7, consider it a match
4. Apply fixture data to OCR results:
   - Use canonical team names from fixtures
   - Add home/away designation
   - Add fixture_id for traceability
   - Boost confidence score (+0.10 to +0.20)
5. Output enriched results with fixture metadata

**Output** (`cache/{episode_id}/fixture_matches.json`):
```json
{
  "episode_date": "2024-08-17",
  "expected_fixtures": [
    {
      "fixture_id": "2024-08-17-arsenal-chelsea",
      "home_team": "Arsenal",
      "away_team": "Chelsea"
    }
  ],
  "matches": [
    {
      "scene_id": 5,
      "ocr_teams": ["Arsenal", "Chelsea"],
      "matched_fixture": "2024-08-17-arsenal-chelsea",
      "confidence": 0.95,
      "fixture_validated": true
    }
  ],
  "unmatched_scenes": [],
  "unexpected_teams": []
}
```

**Benefits**:
- **Improved Accuracy**: Reduces search space from 20 teams to 12-16 teams (6-8 fixtures)
- **Error Correction**: Partial OCR matches can be resolved (e.g., "Arsen" → "Arsenal")
- **Metadata Enrichment**: Automatically adds home/away designation without additional OCR
- **Validation**: Detects unexpected teams that shouldn't appear in this episode

**Error Handling**:
- If no fixture found for OCR teams → use OCR-only result, lower confidence
- If multiple fixtures match → log ambiguity, use highest confidence match
- If fixture expected but not detected → log missing match for investigation

---

### 4.4 Audio Transcription

**Purpose**: Convert speech to text for team mention detection

**Input**:
- Video file path
- Config: Whisper model size, language

**Process**:
1. Extract audio track using ffmpeg: `ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav`
2. Load Whisper model (large-v3)
3. Transcribe with timestamps: `model.transcribe(audio, language='en', word_timestamps=True)`
4. Output full transcript with word-level timestamps

**Output** (`cache/{episode_id}/transcript.json`):
```json
{
  "video_path": "data/videos/motd_2024_08_17.mp4",
  "model": "large-v3",
  "language": "en",
  "duration": 4965.2,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 4.5,
      "text": "Good evening and welcome to Match of the Day.",
      "words": [
        {"word": "Good", "start": 0.0, "end": 0.3},
        {"word": "evening", "start": 0.3, "end": 0.7}
      ]
    }
  ]
}
```

**Caching**: Transcription is the slowest step (~10-15 mins). Cache aggressively. Never re-run unless absolutely necessary.

**Error Handling**:
- If transcription fails → log error, continue with empty transcript
- If audio extraction fails → abort (can't proceed without audio)

---

### 4.5 Analysis & Classification

**Purpose**: Combine all data to classify segments and detect team mentions

**Input**:
- scenes.json
- ocr_results.json
- fixture_matches.json
- transcript.json
- Config: classification rules

**Process**:

1. **Segment Classification**:
   - Iterate through scenes
   - Classify each scene as: studio, highlights, interview, or analysis
   - Rules (heuristic-based initially):
     - If face detected + single person → interview
     - If OCR contains team names → highlights (likely)
     - If scene follows highlights + transcript contains pundit names → analysis
     - Default: studio

2. **Team Mention Detection** (for studio_analysis segments only):
   - Search transcript for team names (full names + abbreviations)
   - Find first chronological mention
   - Extract snippet (±10 words around mention)

3. **Airtime Calculation**:
   - Group consecutive scenes by match (using OCR team detection)
   - Sum durations by segment type
   - Calculate total airtime per match

**Output** (`cache/{episode_id}/analysis.json`):
```json
{
  "matches": [
    {
      "match_id": 1,
      "teams": ["Arsenal", "Chelsea"],
      "home_team": "Arsenal",
      "away_team": "Chelsea",
      "segments": [
        {
          "scene_ids": [5, 6],
          "type": "studio_intro",
          "start": "00:01:30",
          "end": "00:02:15",
          "duration_seconds": 45,
          "confidence": 0.75
        },
        {
          "scene_ids": [7, 8, 9, 10],
          "type": "highlights",
          "start": "00:02:15",
          "end": "00:08:30",
          "duration_seconds": 375,
          "confidence": 0.95
        },
        {
          "scene_ids": [11],
          "type": "interview",
          "location": "pitchside",
          "start": "00:08:30",
          "end": "00:10:00",
          "duration_seconds": 90,
          "confidence": 0.88
        },
        {
          "scene_ids": [12, 13],
          "type": "studio_analysis",
          "start": "00:10:00",
          "end": "00:13:45",
          "duration_seconds": 225,
          "first_team_mentioned": "Arsenal",
          "first_mention_timestamp": "00:10:05",
          "transcript_snippet": "So what did you make of Arsenal's performance Gary?",
          "confidence": 0.92
        }
      ],
      "total_airtime_seconds": 735
    }
  ]
}
```

**Error Handling**:
- If classification confidence < 0.7 → flag for manual review
- If no team mention found in analysis → log warning, leave null
- If team mention detection fails → log error, continue

---

### 4.6 Validation & Manual Override

**Purpose**: Allow manual correction and validation of automated results

**Manual Labels Format** (`cache/{episode_id}/manual_labels.json`):
```json
{
  "scene_5": {
    "type": "studio_intro",
    "teams": ["Arsenal", "Chelsea"],
    "notes": "Corrected OCR miss on Chelsea",
    "validated_by": "michael",
    "validated_at": "2024-11-06T15:30:00Z"
  },
  "scene_11": {
    "type": "interview",
    "location": "studio_remote",
    "notes": "Remote interview via video link, not pitchside"
  }
}
```

**Merge Logic**:
1. Load automated analysis
2. Load manual labels (if exists)
3. For each scene in manual labels:
   - Override automated classification
   - Increase confidence to 1.0 (manual = truth)
   - Add `manual_override: true` flag
4. Output final JSON with merged results

**Validation Report** (`cache/{episode_id}/validation_report.json`):
```json
{
  "total_scenes": 45,
  "manual_overrides": 3,
  "accuracy_metrics": {
    "segment_classification": {
      "correct": 38,
      "incorrect": 4,
      "accuracy": 0.90
    },
    "team_detection": {
      "correct": 12,
      "incorrect": 1,
      "accuracy": 0.92
    }
  }
}
```

---

## 5. Configuration Management

**Config File** (`config/config.yaml`):
```yaml
# Scene Detection
scene_detection:
  threshold: 30.0              # PySceneDetect threshold (lower = more sensitive)
  min_scene_duration: 3.0      # Minimum scene length in seconds

# OCR
ocr:
  library: easyocr
  languages: ['en']
  gpu: true                    # Use GPU acceleration if available
  regions:
    scoreboard:
      x: 0
      y: 0
      width: 400
      height: 100
    formation:
      x: 800
      y: 600
      width: 1920
      height: 1080
  confidence_threshold: 0.7    # Minimum confidence for automatic acceptance

# Fixtures
fixtures:
  path: data/fixtures/premier_league_2025_26.json
  use_for_validation: true
  confidence_boost: 0.15       # How much to boost OCR confidence when fixture matches
  date_tolerance_days: 1       # Allow ±1 day when matching episode date to fixtures

# Transcription
transcription:
  model: large-v3              # Whisper model size
  language: en
  device: auto                 # auto, cpu, cuda, mps
  word_timestamps: true

# Team Names
teams:
  path: data/teams/premier_league_2025_26.json

# Caching
cache:
  enabled: true
  directory: data/cache
  invalidate_on_config_change: true

# Output
output:
  directory: data/output
  format: json
  indent: 2
  include_metadata: true

# Logging
logging:
  level: INFO                  # DEBUG, INFO, WARNING, ERROR
  file: logs/pipeline.log
  console: true
```

---

## 6. Caching Strategy

### Cache Structure
```
data/cache/{episode_id}/
├── scenes.json              # Scene transitions + timestamps
├── ocr_results.json         # Raw OCR text per scene
├── fixture_matches.json     # OCR results matched to fixtures
├── transcript.json          # Full Whisper transcription
├── analysis.json            # Classified segments + team mentions
├── manual_labels.json       # Your corrections (if any)
├── validation_report.json   # Comparison report (if validated)
└── frames/                  # Key frames extracted (for debugging)
    ├── scene_001.jpg
    ├── scene_002.jpg
    └── ...
```

### Cache Invalidation Rules

| Change | Invalidates | Re-runs |
|--------|-------------|---------|
| Scene detection threshold changed | scenes.json | All downstream stages |
| OCR region coordinates changed | ocr_results.json | OCR, fixture matching, analysis |
| Team names list updated | Nothing | Re-run matching only (not OCR) |
| Fixture data updated | fixture_matches.json | Fixture matching, analysis |
| Whisper model changed | transcript.json | Transcription, analysis |
| Classification rules changed | analysis.json | Analysis only |

### Cache Version Hashing
Each cache file includes a `cache_version` hash:
```json
{
  "cache_version": "sha256:abc123...",
  "config_snapshot": {...},
  "data": {...}
}
```

If config changes → hash changes → cache invalidated.

---

## 7. Error Handling Philosophy

### Principles

1. **Fail Gracefully**: One match failing shouldn't block the entire episode
2. **Fail Loudly**: All errors logged with context (scene ID, timestamp, input data)
3. **Confidence Scores**: Low confidence → flag for manual review, don't abort
4. **Manual Override**: Always provide escape hatch for manual correction

### Error Levels

| Level | Action | Example |
|-------|--------|---------|
| **CRITICAL** | Abort pipeline | Can't read video file, ffmpeg not installed |
| **ERROR** | Skip item, continue | OCR fails on one scene, transcription crashes |
| **WARNING** | Flag for review | Low confidence classification, unexpected team count |
| **INFO** | Log for debugging | Using cached results, skipping already-processed scene |

### Confidence Thresholds

- **>0.9**: High confidence, auto-accept
- **0.7-0.9**: Medium confidence, accept but log for spot-check
- **<0.7**: Low confidence, flag for manual review

---

## 8. Testing Strategy

### Unit Tests
- `test_scene_detection.py`: Test PySceneDetect integration
- `test_ocr.py`: Test EasyOCR + team matching logic
- `test_transcription.py`: Test Whisper integration
- `test_analysis.py`: Test segment classification logic

### Integration Tests
- `test_pipeline.py`: Full pipeline on short sample video (30 seconds)
- Validate output JSON schema
- Test caching behavior
- Test error handling (bad input video, missing config)

### Validation Tests
- Manual validation on first 1-2 episodes
- Compare automated output vs. ground truth
- Calculate accuracy metrics
- Tune thresholds based on results

---

## 9. Performance Considerations

### Expected Processing Times (M3 Pro, 36GB RAM)

| Stage | Duration (90-min episode) | Bottleneck |
|-------|---------------------------|------------|
| Scene Detection | 3-5 minutes | CPU-bound (frame analysis) |
| OCR Processing | 2-3 minutes | GPU-bound (EasyOCR) |
| Transcription | 10-15 minutes | GPU-bound (Whisper large-v3) |
| Analysis | <1 minute | CPU-bound (lightweight) |
| **Total** | **15-25 minutes** | |

### Optimisation Opportunities (if needed)

1. **Parallel Processing**: Process multiple episodes in parallel (if you have >1 video)
2. **Smaller Whisper Model**: Use medium or small model (faster, slightly less accurate)
3. **Reduced OCR**: Only run OCR on scenes with scoreboard detected (via template matching)
4. **Frame Sampling**: Analyse every Nth frame instead of every frame (scene detection)

### Resource Usage

- **RAM**: ~8-12GB peak (Whisper large-v3 loaded)
- **GPU**: M3 Pro will handle Whisper + EasyOCR comfortably
- **Disk**: ~500MB per episode (cache + frames)

---

## 10. CLI Interface

### Commands

```bash
# Full pipeline (automated)
python -m motd_analyzer process video.mp4 --output results.json

# Scene detection only (for manual labeling)
python -m motd_analyzer detect-scenes video.mp4 --output scenes.json

# Run with manual labels
python -m motd_analyzer process video.mp4 --manual-labels scenes_labeled.json

# Validate automated output against manual labels
python -m motd_analyzer validate --auto analysis.json --manual manual_labels.json

# Batch process multiple videos
python -m motd_analyzer batch data/videos/*.mp4 --output-dir data/output

# Clear cache for a specific episode
python -m motd_analyzer clear-cache --episode-id motd_2024_08_17
```

### Example Workflow

```bash
# Step 1: Process first video
python -m motd_analyzer process data/videos/motd_2024_08_17.mp4

# Step 2: Manual validation (edit manual_labels.json)
# ...

# Step 3: Re-run with manual corrections
python -m motd_analyzer process data/videos/motd_2024_08_17.mp4 \
  --manual-labels data/cache/motd_2024_08_17/manual_labels.json

# Step 4: Validate accuracy
python -m motd_analyzer validate \
  --auto data/cache/motd_2024_08_17/analysis.json \
  --manual data/cache/motd_2024_08_17/manual_labels.json

# Step 5: If accuracy >90%, batch process remaining episodes
python -m motd_analyzer batch data/videos/*.mp4 --output-dir data/output
```

---

## 11. Future Architecture Considerations

### For Podcast Analysis Extension
- **Remove**: scene_detection, ocr modules
- **Keep**: transcription, analysis (team mention detection)
- **Add**: speaker diarization (identify who's speaking)
- **Adapt**: Segment classification (intro, main discussion, conclusion)

### For Lower League Extension
- **Change**: Team names list only
- **Keep**: Everything else identical
- **Consider**: Different graphic styles (might need OCR retraining)

### For Dashboard/API
- **Add**: REST API layer on top of pipeline
- **Add**: Database for storing results (SQLite or PostgreSQL)
- **Add**: Real-time processing status endpoint
- **Frontend**: React dashboard consuming JSON output

---

## Summary

This architecture prioritizes:
1. **Modularity**: Easy to swap components or extend to new use cases
2. **Validation**: Manual override at every stage
3. **Performance**: Aggressive caching, GPU acceleration
4. **Reliability**: Fail gracefully, high confidence thresholds
5. **Extensibility**: Clear interfaces for future enhancements

Next: See [roadmap.md](roadmap.md) for phased implementation plan.
