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

### 4.5 Running Order Detection

**Purpose**: Determine which teams appear in which order using OCR detections

**Status**: ✅ Task 011 Complete (100% accuracy: 7/7 matches)

**Input**:
- Processed scenes with OCR detections (from Section 4.2)
- Episode manifest (expected matches)
- Fixtures data (home/away teams)

**Process**:
1. **Collect all valid OCR detections**:
   - FT graphics (PRIMARY - 90-95% accuracy)
   - Scoreboards (BACKUP - 75-85% accuracy)
   - Opponent-inferred detections (Rule 3 - 70% recovery rate)

2. **Order by first detection**:
   - Group detections by fixture_id
   - Find earliest timestamp for each match
   - Sort matches by earliest detection timestamp
   - Assign running order position (1, 2, 3...)

3. **Validate against episode manifest**:
   - Verify all expected matches detected
   - Flag unexpected matches (replays, promos)
   - Calculate confidence based on detection count

**Output** (`cache/{episode_id}/running_order.json`):
```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "running_order": [
    {
      "position": 1,
      "fixture_id": "2025-11-01-liverpool-astonvilla",
      "home_team": "Liverpool",
      "away_team": "Aston Villa",
      "first_detection_timestamp": 125.4,
      "detection_count": 3,
      "detection_sources": ["ft_score", "scoreboard"],
      "confidence": 1.0
    }
  ]
}
```

**Results** (motd_2025-26_2025-11-01):
- **Accuracy**: 7/7 matches detected (100%)
- **Detection rate**: 100% (all expected matches found)
- **False positives**: 0 (episode manifest constraint)

---

### 4.6 Match Boundary Detection

**Purpose**: Detect precise timestamps for match segment boundaries (intro → highlights → post-match)

**Status**: ✅ Task 012-01 Complete (100% accuracy: 7/7 matches, ±1.27s avg error)

**Input**:
- Running order results (Section 4.5)
- OCR detections (FT graphics + scoreboards)
- Transcript with word-level timestamps
- Venue data (`data/venues/premier_league_2025_26.json`)
- Fixtures data (match pairings)

**Three-Strategy Detection Framework**:

#### Strategy 1: Venue Detection (PRIMARY)
**Purpose**: Find match intro by detecting stadium mentions in transcript

**Process**:
1. Search backward from `highlights_start` (scoreboard detection)
2. Extract sentences from transcript (combine Whisper segments)
3. Fuzzy match sentences against venue names (stadium only, no aliases)
4. Validate venue matches expected fixture (home team's stadium)
5. Search for team mentions within ±20s proximity window
6. Return timestamp of **earliest team-containing sentence**

**Implementation**: `src/motd/analysis/venue_matcher.py`

**Results**:
- **Accuracy**: 7/7 matches
- **Average error**: ±1.27 seconds
- **All matches within**: ±5s tolerance

#### Strategy 2: Temporal Clustering (VALIDATOR)
**Purpose**: Cross-validate venue detection using team co-mention density

**Process**:
1. Extract all team mentions from transcript (fuzzy matching)
2. Create sliding 20-second windows
3. Count co-mentions of both teams within each window
4. Calculate density (mentions per second) for each window
5. Filter valid clusters (density ≥ 0.1, size ≥ 2, before `highlights_start`)
6. **Hybrid selection**: Prefer earliest cluster UNLESS later cluster is 2x denser
7. Return timestamp of **earliest mention** in selected cluster

**Implementation**: `src/motd/analysis/running_order_detector.py:720-1055`

**Configuration**:
```python
CLUSTERING_WINDOW_SECONDS = 20.0  # Co-mention window
CLUSTERING_MIN_DENSITY = 0.1      # Minimum mentions/sec
CLUSTERING_MIN_SIZE = 2           # Minimum co-mentions
```

**Results**:
- **Accuracy**: 7/7 matches
- **Agreement with venue**: 100% (0.0s difference across all matches)
- **Validation**: All matches "validated" status (≤10s difference threshold)

#### Strategy 3: Team Mention (FALLBACK)
**Purpose**: Backup strategy if venue or clustering fails

**Process**:
1. Search backward from `highlights_start`
2. Find both teams mentioned within 10 seconds of each other
3. Return **earliest mention** timestamp

**Usage**: Fallback only (venue + clustering have 100% success rate)

**Cross-Validation Framework**:

All three strategies run independently, then cross-validate:

| Difference | Status | Confidence | Action |
|------------|--------|------------|--------|
| ≤10s | `validated` | 1.0 | Auto-accept ✅ |
| ≤30s | `minor_discrepancy` | 0.8 | Flag for review ⚠️ |
| >30s | `major_discrepancy` | 0.5 | Manual review required ❌ |
| Clustering failed | `clustering_failed` | 0.7 | Use venue only |

**Pydantic Model** (`BoundaryValidation`):
```python
class BoundaryValidation(BaseModel):
    venue_timestamp: float
    clustering_timestamp: Optional[float]
    difference_seconds: float
    status: Literal["validated", "minor_discrepancy", "major_discrepancy", "clustering_failed"]
    confidence: float
```

**Output** (`cache/{episode_id}/match_boundaries.json`):
```json
{
  "matches": [
    {
      "position": 1,
      "home_team": "Liverpool",
      "away_team": "Aston Villa",
      "match_start": 125.4,
      "highlights_start": 186.8,
      "highlights_end": 523.2,
      "strategies": {
        "venue": {"timestamp": 125.4, "venue": "Anfield", "confidence": 0.95},
        "clustering": {"timestamp": 125.4, "density": 0.25, "cluster_size": 5},
        "team_mention": {"timestamp": 126.1, "confidence": 0.85}
      },
      "validation": {
        "status": "validated",
        "venue_clustering_diff": 0.0,
        "confidence": 1.0
      }
    }
  ]
}
```

**Results** (motd_2025-26_2025-11-01):

| Match | Venue Error | Clustering Agreement | Validation Status |
|-------|-------------|---------------------|-------------------|
| Match 1 | +0.1s | 0.0s diff | ✅ Validated |
| Match 2 | +1.3s | 0.0s diff | ✅ Validated |
| Match 3 | +0.2s | 0.0s diff | ✅ Validated |
| Match 4 | +0.1s | 0.0s diff | ✅ Validated |
| Match 5 | +1.3s | 0.0s diff | ✅ Validated |
| Match 6 | +1.6s | 0.0s diff | ✅ Validated |
| Match 7 | +4.4s | 0.0s diff | ✅ Validated |

**Average error**: 1.27 seconds across all 7 matches
**Cross-validation**: 100% agreement (0.0s difference between venue and clustering)

---

### 4.7 Segment Classification

**Purpose**: Classify each scene as studio intro, highlights, interview, or post-match analysis

**Status**: 🔄 Task 012 In Progress

**Planned Approach**:
1. Use match boundaries as anchors (from Section 4.6)
2. Classify segments between boundaries:
   - `match_start` → `highlights_start`: Studio intro + team lineups
   - `highlights_start` → `highlights_end`: Match highlights (scoreboard visible)
   - `highlights_end` → next `match_start`: Post-match interviews + studio analysis
3. Detect interludes (Sunday MOTD promos, intro/outro segments)
4. Calculate airtime by segment type

**Output Schema** (planned):
```json
{
  "matches": [
    {
      "match_id": 1,
      "segments": [
        {"type": "studio_intro", "start": 125.4, "end": 186.8, "duration": 61.4},
        {"type": "highlights", "start": 186.8, "end": 523.2, "duration": 336.4},
        {"type": "post_match", "start": 523.2, "end": 687.5, "duration": 164.3}
      ],
      "total_airtime": 562.1
    }
  ]
}
```

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
| Scene Detection + Frame Extraction | 18-20 minutes | CPU-bound | Hybrid strategy: scene changes + 2s intervals |
| OCR Processing | 10-12 minutes | GPU-bound (EasyOCR) | ~2,600 frames, 3 ROIs per frame |
| Transcription | 15-20 minutes | **CPU-bound** | faster-whisper (CTranslate2 no MPS support yet) |
| Running Order Detection | <30 seconds | CPU-bound | OCR result aggregation |
| Match Boundary Detection | 1-2 minutes | CPU-bound | Venue + clustering + validation |
| **Total** | **45-55 minutes** | | Per episode, first run (no cache) |

**Key Insight**: faster-whisper on Apple Silicon (M3 Pro) runs on **CPU** because CTranslate2 doesn't support MPS (Metal Performance Shaders) yet. GPU acceleration requires CUDA (NVIDIA only).

**Caching Impact**:
- **Second run** (cache hit): <1 minute (loads cached JSON files only)
- **Partial cache invalidation** (e.g., analysis rules changed): 1-2 minutes (skips scene detection, OCR, transcription)

**Hybrid Frame Extraction Impact**:
- **Scene changes**: ~450 frames (variable, depends on episode)
- **2s intervals**: ~2,700 frames (fixed for 90-min video)
- **After deduplication**: ~2,600 frames (78% increase vs 5s intervals)
- **Benefit**: Better coverage of FT graphics and scoreboards (+15% detection rate)

### Optimisation Opportunities (if needed)

1. **Parallel Processing**: Process multiple episodes in parallel (8-core M3 Pro can handle 2-3 episodes)
2. **Smaller Whisper Model**: Use medium or small model (5-10 min faster, 2-3% accuracy drop)
3. **Interval Tuning**: Increase interval from 2.0s to 3.0s (20% fewer frames, minimal accuracy impact)
4. **GPU Transcription**: Use NVIDIA GPU with CUDA for 3-4x speedup (5-7 mins vs 15-20 mins)

### Resource Usage

- **RAM**: ~12-16GB peak (Whisper large-v3 loaded + EasyOCR + frame cache)
- **GPU**: M3 Pro handles EasyOCR well (MPS support), but Whisper falls back to CPU
- **Disk**: ~800MB-1GB per episode (cache + ~2,600 frames)

**Bottleneck Analysis**:
- **Slowest stage**: Transcription (15-20 mins) - waiting for CTranslate2 MPS support
- **Most expensive stage**: Frame extraction + OCR (28-32 mins combined)
- **Fastest stage**: Running order + boundary detection (1.5-2.5 mins)

**Recommendation**: Run overnight batch processing for 10 episodes (~8-10 hours total)

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
