# Match of the Day Analyser - Technical Architecture

> **Last reviewed:** 2025-12-18

## 1. System Overview

### Design Principles

1. **Modularity**: Each pipeline stage operates independently with clear input/output contracts
2. **Caching**: Intermediate results are cached to avoid expensive re-processing
3. **Reproducibility**: Same input + same config = same output, always
4. **Fail Gracefully**: Pipeline continues if one component fails; errors logged but don't block progress
5. **LLM-Based Analysis**: Final segment detection is performed by Claude using advisory hints from the pipeline

### High-Level Pipeline Flow

```
┌─────────────────┐
│   Video Input   │
│   (MP4 file)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Stage 1: Scene Detection      │
│   • Detect frame transitions    │
│   • Extract key frames          │
│   • Output: scenes.json         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Stage 2: OCR Processing       │
│   • Crop to regions of interest │
│   • Extract FT graphics/scores  │
│   • Output: ocr_results.json    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Stage 3: Audio Transcription  │
│   • Extract audio track         │
│   • Whisper transcription       │
│   • Output: transcript.json     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   generate-llm-prompt           │
│   • Deduplicate transcript      │
│   • Extract OCR hints           │
│   • Build LLM prompt            │
│   • Output: transcript_for_llm  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Claude Analysis (Manual)      │
│   • Copy prompt to Claude       │
│   • Claude returns JSON         │
│   • Save to data/analysis/      │
└─────────────────────────────────┘
```

**Note:** Stages 1-3 produce advisory hints. The actual segment analysis is performed by Claude via the LLM workflow.

---

## 2. Project Structure

```
motd-video-analyser/
├── src/
│   └── motd/
│       ├── __init__.py
│       ├── __main__.py              # CLI entry point
│       │
│       ├── scene_detection/         # Stage 1: PySceneDetect integration
│       ├── ocr/                     # Stage 2: EasyOCR + team matching
│       ├── transcription/           # Stage 3: faster-whisper integration
│       ├── llm/                     # LLM prompt generation
│       └── pipeline/                # Pydantic models, orchestrator
│
├── data/
│   ├── teams/                       # Team names + variations
│   ├── fixtures/                    # Match schedules
│   ├── episodes/                    # Episode manifests
│   ├── videos/                      # Input videos (gitignored)
│   ├── cache/                       # Pipeline cache (gitignored)
│   │   └── {episode_id}/
│   │       ├── scenes.json
│   │       ├── ocr_results.json
│   │       ├── transcript.json
│   │       ├── transcript_for_llm.txt
│   │       └── frames/
│   └── analysis/                    # LLM analysis results (committed)
│       └── {episode_id}/
│           └── analysis.json
│
├── config/
│   └── config.yaml                  # Pipeline configuration
│
├── tests/                           # pytest test suite
├── docs/                            # Documentation
├── requirements.txt
└── README.md
```

---

## 3. Technology Stack

For detailed comparisons of alternatives, see [tech-tradeoffs.md](tech-tradeoffs.md).

| Component | Library | Rationale |
|-----------|---------|-----------|
| **Scene Detection** | PySceneDetect | Purpose-built for scene transitions, handles fades/dissolves |
| **OCR** | EasyOCR | Better accuracy on stylized sports graphics, GPU support (MPS on Apple Silicon) |
| **Transcription** | **faster-whisper** (large-v3) | 4x faster than openai-whisper (CTranslate2 optimized), state-of-the-art accuracy |
| **Fuzzy Matching** | rapidfuzz | Team names, venue aliases, high-performance Levenshtein distance |
| **Type Safety** | Pydantic v2 | Runtime validation, clear data contracts, JSON serialization |
| **Video Processing** | ffmpeg + opencv-python | Industry standard, comprehensive functionality |
| **Configuration** | PyYAML | Simple, human-readable config files |
| **CLI** | argparse | Standard Python CLI framework |

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

**Purpose**: Extract team names from FT graphics and scoreboards, validate against known fixtures

**Input**:
- Frames from **hybrid extraction strategy** (scene changes + 2-second intervals)
- Config: ROI coordinates (720p), team names list, fixtures data
- Episode manifest (expected matches for this episode)

**Hybrid Frame Extraction Strategy** (Task 011b):
1. **Phase 1**: Extract frames at scene change timestamps (PySceneDetect ContentDetector)
2. **Phase 2**: Extract frames at 2.0-second intervals (regular sampling)
3. **Phase 3**: Deduplicate frames within 1.0 second of each other
4. **Result**: ~2,600 frames per 90-minute video (scene changes + intervals - duplicates)

**OCR Process**:
1. Load extracted frame
2. Crop to **three regions of interest** (720p coordinates):
   - **FT Score** (PRIMARY - 90-95% accuracy): `x:157, y:545, width:966, height:140` (lower-middle)
   - **Scoreboard** (BACKUP - 75-85% accuracy): `x:0, y:0, width:370, height:70` (top-left)
   - **Formation** (VALIDATION only): `x:533, y:400, width:747, height:320` (bottom-right)
3. Run EasyOCR (GPU-accelerated) on cropped regions
4. **FT Graphic Validation** (Business Rule 1):
   - Require ≥1 team detected (allows opponent inference)
   - Require score pattern: `\d+\s*[-–—|]?\s*\d+` (handles BBC's pipe separator)
   - Require FT text: One of [FT, FULL TIME, FULL-TIME, FULLTIME]
5. Match extracted text against team name list (fuzzy matching via rapidfuzz)
6. **Episode Manifest Constraint** (Business Rule 2):
   - Cross-reference with episode manifest (limits search to 14 teams in 7 expected matches)
   - +10% confidence boost for expected teams
   - Filter false positives (replays, promos, rival mentions)
7. **Opponent Inference** (Business Rule 3):
   - If only 1 team detected + FT validation passes → infer opponent from fixtures
   - Use home_team/away_team pairing from episode manifest
   - Assign confidence 0.75 (lower than OCR-detected team)
   - Mark as `inferred_from_fixture`
   - **Impact**: Recovers ~70% of single-team FT graphics

**Multi-Pass Strategy**:
- **Pass 1**: Prioritize FT graphics (mark match boundaries for segment classifier)
- **Pass 2**: Accept scoreboards if no FT found (fallback for running order)

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

### 4.3 Fixture Matching & Episode Manifest

**Purpose**: Validate OCR results against episode manifest to improve accuracy and reduce search space

**Input**:
- OCR results with detected teams
- **Episode manifest** (`data/episodes/episode_manifest.json`) - expected matches for this specific episode
- Full fixture data for season (`data/fixtures/premier_league_2025_26.json`)

**Episode Manifest Structure**:
```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "broadcast_date": "2025-11-01",
  "expected_matches": [
    "2025-11-01-liverpool-astonvilla",
    "2025-11-01-burnley-arsenal"
  ]
}
```

**Process**:
1. Load episode manifest to get expected matches (7 matches = 14 teams)
2. **Search space reduction**: Only search against expected teams (30% reduction vs full 20-team PL)
3. For each OCR team pair:
   - Calculate fuzzy similarity score against expected fixtures (rapidfuzz)
   - Find best matching fixture from manifest
   - If similarity > 0.7, consider it a match
4. **Apply fixture data to OCR results**:
   - Use canonical team names from fixtures (corrects OCR errors)
   - Add home/away designation
   - Add fixture_id for traceability
   - **Confidence boost**: +10% for teams in episode manifest
5. **Opponent inference** (if 1 team detected):
   - Match detected team to expected fixtures
   - Infer opponent from home_team/away_team pairing
   - Confidence: 0.75 (lower than OCR-detected)
6. Output enriched results with fixture metadata

**Benefits**:
- **Search space reduction**: 14 teams (7 matches) vs 20 teams (190 possible pairings)
- **Higher accuracy**: Manifest constraint filters false positives (replays, promos, rival mentions)
- **Opponent recovery**: Single-team FT graphics can be completed using fixture pairing
- **Canonical names**: OCR errors automatically corrected (e.g., "Arsen" → "Arsenal")

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

### 4.5 OCR Hint Extraction

**Purpose**: Extract FT graphics and scoreboard timestamps as advisory hints for LLM analysis

**Input**:
- Processed scenes with OCR detections (from Section 4.2)
- Episode manifest (expected matches)
- Fixtures data (home/away teams)

**Process**:
1. **Collect valid OCR detections**:
   - FT graphics (PRIMARY - 90-95% accuracy)
   - Scoreboards (BACKUP - 75-85% accuracy)
   - Opponent-inferred detections (70% recovery rate)

2. **Format as advisory hints**:
   - FT graphic timestamps (anchor for match end boundaries)
   - First scoreboard per match (anchor for highlights start)
   - Team names with confidence scores

**Output**: OCR hints are included in the LLM prompt via `generate-llm-prompt` command.

**Note**: Running order detection is now performed by the LLM using the transcript + OCR hints.

---

### 4.6 LLM Prompt Generation

**Purpose**: Generate a prompt for Claude to analyse episode segments

**Implementation**: `src/motd/llm/` module

**Components**:

1. **TranscriptFormatter** (`transcript_formatter.py`)
   - Loads `transcript.json`
   - Deduplicates Whisper "stutters" (consecutive identical segments)
   - Formats as timestamped text: `[MM:SS.ss] text`

2. **OCRHintsExtractor** (`ocr_hints.py`)
   - Extracts FT graphic timestamps from `ocr_results.json`
   - Extracts first scoreboard per match
   - Formats as markdown hints for prompt

3. **PromptBuilder** (`prompt_builder.py`)
   - Loads episode manifest and fixtures
   - Assembles prompt sections: header, fixtures, task, schema, hints, transcript
   - Outputs to `data/cache/{episode_id}/transcript_for_llm.txt`

**CLI Command**:
```bash
python -m motd generate-llm-prompt <episode_id>
python -m motd generate-llm-prompt <episode_id> --no-hints  # Without OCR hints
python -m motd generate-llm-prompt <episode_id> --force     # Overwrite existing
```

**Output**: ~22k token prompt file ready for Claude analysis

**Workflow**:
1. Copy prompt to Claude web UI
2. Claude returns structured JSON with segment timestamps
3. Save JSON to `data/analysis/{episode_id}/analysis.json`

See [analysis_schema.md](domain/analysis_schema.md) for the output JSON structure.

---

### 4.7 Segment Classification

**Purpose**: Classify each episode segment (studio intro, highlights, interviews, analysis)

**Approach**: LLM-based analysis via Claude

Segment classification is performed by Claude using the transcript and OCR hints. The LLM identifies:

**Episode-level segments:**
- `intro` - Opening with pundit introductions
- `league_table` - League standings review (if present)
- `next_motd_promo` - Promo for next episode (if present)
- `outro` - Closing credits

**Per-match segments:**
- `studio_intro` - Pundit discussion before highlights
- `lineups` - Formation graphics and team walkthrough
- `highlights` - Match footage with commentary
- `post_match_interviews` - Pitchside interviews
- `studio_analysis` - Post-match pundit discussion

**Output**: `data/analysis/{episode_id}/analysis.json`

See [analysis_schema.md](domain/analysis_schema.md) for the complete JSON schema.

---

### 4.8 Pydantic Data Models

**Purpose**: Type-safe data contracts throughout the pipeline with runtime validation

**Status**: ✅ Implemented (Phase 2 of Task 011b-2)

All pipeline stages use **Pydantic v2** models for type safety, validation, and clear data contracts.

**Core Models** (`src/motd/pipeline/models.py`):

#### Scene Model
```python
class Scene(BaseModel):
    scene_id: int
    start_seconds: float
    end_seconds: float
    duration: float
    frames: list[str]  # Paths to extracted frames

    @field_validator('end_seconds')
    def end_after_start(cls, v, info):
        if v <= info.data['start_seconds']:
            raise ValueError('end_seconds must be > start_seconds')
        return v
```

#### TeamMatch Model
```python
class TeamMatch(BaseModel):
    team: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal['ft_score', 'scoreboard', 'formation', 'inferred_from_fixture']
```

#### OCRResult Model
```python
class OCRResult(BaseModel):
    frame_path: str
    timestamp: float
    teams: list[TeamMatch]
    raw_text: str
    primary_source: Literal['ft_score', 'scoreboard', 'formation']
    ft_validated: bool  # Passed FT graphic validation (Rule 1)

    # Store ALL OCR results for debugging
    ft_score_result: Optional[dict] = None
    scoreboard_result: Optional[dict] = None
    formation_result: Optional[dict] = None
```

#### ProcessedScene Model
```python
class ProcessedScene(BaseModel):
    scene: Scene
    ocr_result: Optional[OCRResult]
    detected_teams: list[str]
    fixture_id: Optional[str]
    home_team: Optional[str]
    away_team: Optional[str]
    confidence: float = Field(ge=0.0, le=1.0)
```

#### MatchBoundary Model
```python
class MatchBoundary(BaseModel):
    position: int  # Running order position
    fixture_id: str
    home_team: str
    away_team: str
    match_start: float  # Timestamp (seconds)
    highlights_start: float
    highlights_end: float
    venue_detected: Optional[str] = None
    clustering_density: Optional[float] = None
```

#### BoundaryValidation Model
```python
class BoundaryValidation(BaseModel):
    venue_timestamp: float
    clustering_timestamp: Optional[float]
    difference_seconds: float
    status: Literal["validated", "minor_discrepancy", "major_discrepancy", "clustering_failed"]
    confidence: float = Field(ge=0.0, le=1.0)
```

#### RunningOrderResult Model
```python
class RunningOrderResult(BaseModel):
    episode_id: str
    total_matches: int
    matches: list[MatchBoundary]
    validation: dict[int, BoundaryValidation]  # position → validation

    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for file output
        return super().model_dump(mode='json', **kwargs)
```

**Benefits**:
- **Runtime validation**: Catch errors at model creation (e.g., confidence > 1.0, end_seconds < start_seconds)
- **Type safety**: IDE autocomplete, mypy static checking
- **Clear contracts**: Each pipeline stage has well-defined input/output types
- **JSON serialization**: Built-in `model_dump_json()` for cache files
- **Self-documenting**: Field descriptions serve as inline documentation

**Validation Examples**:
```python
# FAILS: Confidence out of bounds
TeamMatch(team="Arsenal", confidence=1.5, source="ft_score")
# ValidationError: Input should be less than or equal to 1.0

# FAILS: Invalid source
TeamMatch(team="Arsenal", confidence=0.9, source="unknown")
# ValidationError: Input should be 'ft_score', 'scoreboard', 'formation', or 'inferred_from_fixture'

# FAILS: end_seconds before start_seconds
Scene(scene_id=1, start_seconds=100.0, end_seconds=50.0, duration=50.0, frames=[])
# ValidationError: end_seconds must be > start_seconds
```

**Testing**: 16 unit tests covering serialization, validation, edge cases ([src/motd/pipeline/test_models.py:1-180](../src/motd/pipeline/test_models.py))

---

### 4.9 Validation & Manual Override

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

| Stage | Duration (90-min episode) | Bottleneck | Notes |
|-------|---------------------------|------------|-------|
| Scene Detection + Frame Extraction | 5-8 minutes | CPU-bound | Hybrid strategy: scene changes + 2s intervals |
| OCR Processing | 8-12 minutes | GPU-bound (EasyOCR) | ~2,600 frames, 3 ROIs per frame |
| Transcription | 15-20 minutes | **CPU-bound** | faster-whisper (CTranslate2 no MPS support yet) |
| LLM Prompt Generation | <30 seconds | CPU-bound | Transcript formatting + OCR hints |
| **Total (automated)** | **30-35 minutes** | | Per episode, first run (no cache) |

**LLM Analysis** (manual step):
- Copy prompt to Claude web UI
- Claude processing: ~30-60 seconds
- Save JSON response to `data/analysis/`

**Key Insight**: faster-whisper on Apple Silicon (M3 Pro) runs on **CPU** because CTranslate2 doesn't support MPS (Metal Performance Shaders) yet. GPU acceleration requires CUDA (NVIDIA only).

**Caching Impact**:
- **Second run** (cache hit): <1 minute (loads cached JSON files only)
- **Prompt regeneration only**: <30 seconds (skips scene detection, OCR, transcription)

### Resource Usage

- **RAM**: ~12-16GB peak (Whisper large-v3 loaded + EasyOCR + frame cache)
- **GPU**: M3 Pro handles EasyOCR well (MPS support), but Whisper falls back to CPU
- **Disk**: ~800MB-1GB per episode (cache + ~2,600 frames)

**Bottleneck Analysis**:
- **Slowest stage**: Transcription (15-20 mins) - waiting for CTranslate2 MPS support
- **Most expensive stage**: Frame extraction + OCR (13-20 mins combined)
- **Fastest stage**: LLM prompt generation (<30 seconds)

---

## 10. CLI Interface

### Commands

```bash
# Full pipeline (stages 1-3: scenes, OCR, transcription)
python -m motd run data/videos/motd_2025-26_2025-11-01.mp4

# Generate LLM prompt for Claude analysis
python -m motd generate-llm-prompt motd_2025-26_2025-11-01

# Individual stages (for debugging)
python -m motd detect-scenes data/videos/motd_2025-26_2025-11-01.mp4
python -m motd extract-teams --scenes data/cache/.../scenes.json --episode-id ...
python -m motd transcribe data/videos/motd_2025-26_2025-11-01.mp4
```

### Example Workflow

```bash
# Step 1: Run automated pipeline
python -m motd run data/videos/motd_2025-26_2025-11-01.mp4

# Step 2: Generate LLM prompt
python -m motd generate-llm-prompt motd_2025-26_2025-11-01

# Step 3: Copy prompt to Claude web UI
cat data/cache/motd_2025-26_2025-11-01/transcript_for_llm.txt | pbcopy
# Paste into https://claude.ai

# Step 4: Save Claude's JSON response
# Save to data/analysis/motd_2025-26_2025-11-01/analysis.json
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

See [GitHub Issues](https://github.com/mbd0910/motd-video-analyser/issues) for current work items.
