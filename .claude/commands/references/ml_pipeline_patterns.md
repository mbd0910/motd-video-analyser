# ML Pipeline Patterns

MOTD-specific patterns for video processing, ML operations, and pipeline management.

---

## Caching Strategy (CRITICAL)

### Never Re-Run Whisper

**Whisper transcription takes 3-4 minutes per 90-minute video** - caching is essential.

```python
# ✅ GOOD: Check cache first
def transcribe_video(video_path: Path, episode_id: str, config: dict) -> dict:
    """Transcribe video with caching."""
    cache_file = Path(f"data/cache/{episode_id}/transcript.json")

    # Check if cache exists and is valid
    if cache_file.exists():
        cached_data = json.loads(cache_file.read_text())
        if is_cache_valid(cached_data, config):
            logger.info(f"Using cached transcript for {episode_id}")
            return cached_data

    # Run expensive operation
    logger.info(f"Transcribing {video_path.name} (3-4 mins)")
    transcript = run_whisper(video_path, config)

    # Save to cache
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({
        'cache_version': compute_config_hash(config),
        'processed_at': datetime.now().isoformat(),
        'config_snapshot': config['transcription'],
        'data': transcript
    }, indent=2))

    return transcript
```

### Cache Invalidation Rules

**Cache is invalid if**:
- Config changed (threshold, model size, etc.)
- Input file modified (check mtime or hash)
- Cache file corrupt/incomplete

```python
def is_cache_valid(cached_data: dict, current_config: dict) -> bool:
    """Check if cache is still valid given current config."""
    cached_version = cached_data.get('cache_version')
    current_version = compute_config_hash(current_config)

    if cached_version != current_version:
        logger.info("Cache invalid: config changed")
        return False

    if 'data' not in cached_data:
        logger.warning("Cache invalid: missing data")
        return False

    return True

def compute_config_hash(config: dict) -> str:
    """Generate SHA-256 hash of config for cache versioning."""
    import hashlib
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]
```

### Cache File Structure

Include in cached JSON:
- `cache_version`: Hash of relevant config parameters
- `processed_at`: Timestamp
- `config_snapshot`: Snapshot of parameters used (model, language, device)
- `data`: Actual cached results

---

## Graceful Degradation

### One Failure Shouldn't Block the Pipeline

**If OCR fails for one scene, continue processing other scenes.**

```python
# ❌ BAD: One failure stops everything
def process_scenes(scenes: list[dict]) -> list[dict]:
    results = []
    for scene in scenes:
        teams = extract_teams(scene['frame'])  # Raises exception on failure
        results.append({'scene_id': scene['id'], 'teams': teams})
    return results

# ✅ GOOD: Graceful degradation
def process_scenes(scenes: list[dict]) -> list[dict]:
    results = []
    failed_scenes = []

    for scene in scenes:
        try:
            teams = extract_teams(scene['frame'])
            results.append({'scene_id': scene['id'], 'teams': teams})
        except Exception as e:
            logger.error(
                f"Team extraction failed for scene {scene['id']}: {e}",
                extra={'scene_id': scene['id'], 'frame_path': scene['frame']}
            )
            failed_scenes.append(scene['id'])
            # Add partial result with error flag
            results.append({
                'scene_id': scene['id'],
                'teams': None,
                'error': str(e),
                'requires_manual_review': True
            })

    if failed_scenes:
        logger.warning(
            f"{len(failed_scenes)}/{len(scenes)} scenes failed team extraction",
            extra={'failed_scene_ids': failed_scenes}
        )

    return results
```

### Log Failures with Context

**Always include**:
- Episode ID
- Stage name (scene_detection, ocr, transcription)
- File paths involved
- Input data that caused failure

```python
logger.error(
    f"OCR failed for scene {scene_id}",
    extra={
        'episode_id': episode_id,
        'stage': 'ocr',
        'scene_id': scene_id,
        'frame_path': str(frame_path),
        'ocr_region': region_coords
    },
    exc_info=True  # Include stack trace
)
```

---

## Confidence Thresholds

### Standard Thresholds (from Architecture)

```python
CONFIDENCE_THRESHOLDS = {
    'HIGH': 0.9,     # Auto-accept
    'MEDIUM': 0.7,   # Accept but log for spot-check
    'LOW': 0.5,      # Flag for manual review
}

def classify_result(confidence: float) -> str:
    """Classify result based on confidence score."""
    if confidence >= CONFIDENCE_THRESHOLDS['HIGH']:
        return 'auto_accept'
    elif confidence >= CONFIDENCE_THRESHOLDS['MEDIUM']:
        logger.info(f"Medium confidence result: {confidence:.2f}")
        return 'accept_with_logging'
    else:
        logger.warning(f"Low confidence result: {confidence:.2f} - flag for review")
        return 'requires_manual_review'
```

### Apply Thresholds Consistently

```python
# ✅ GOOD: Consistent confidence handling
def extract_teams(frame_path: Path, config: dict) -> dict:
    """Extract teams from frame with confidence scoring."""
    ocr_results = run_ocr(frame_path)
    teams = match_teams(ocr_results['text'], team_list)

    confidence = teams['confidence']
    threshold = config['ocr']['confidence_threshold']

    result = {
        'teams': teams['matched'],
        'confidence': confidence,
        'raw_ocr_text': ocr_results['text']
    }

    if confidence < threshold:
        result['requires_manual_review'] = True
        logger.warning(
            f"Team matching confidence {confidence:.2f} below threshold {threshold}",
            extra={'frame_path': str(frame_path), 'ocr_text': ocr_results['text']}
        )

    return result
```

---

## Config-Driven Behaviour

### Load Config Once, Pass Down

```python
# ❌ BAD: Config loaded everywhere
class SceneDetector:
    def detect(self, video_path: Path) -> list[dict]:
        config = yaml.safe_load(open('config.yaml'))  # Loaded here
        threshold = config['scene_detection']['threshold']
        ...

class OCRProcessor:
    def process(self, frame: Path) -> dict:
        config = yaml.safe_load(open('config.yaml'))  # Loaded again!
        regions = config['ocr']['regions']
        ...

# ✅ GOOD: Load once at app startup, inject into components
def main():
    config = load_config('config/config.yaml')

    # Inject config values into components
    scene_detector = SceneDetector(
        threshold=config['scene_detection']['threshold'],
        min_duration=config['scene_detection']['min_scene_duration']
    )

    ocr_processor = OCRProcessor(
        regions=config['ocr']['regions'],
        confidence_threshold=config['ocr']['confidence_threshold']
    )

    pipeline = PipelineOrchestrator(scene_detector, ocr_processor, config)
    pipeline.process(video_path)
```

### Validate Config at Load Time

```python
def load_config(config_path: Path) -> dict:
    """Load and validate config.yaml."""
    with config_path.open() as f:
        config = yaml.safe_load(f)

    # Validate required keys
    required_sections = ['scene_detection', 'ocr', 'transcription', 'cache']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Validate value ranges
    threshold = config['scene_detection']['threshold']
    if not (0 < threshold < 100):
        raise ValueError(f"Invalid threshold: {threshold} (must be 0-100)")

    confidence = config['ocr']['confidence_threshold']
    if not (0 <= confidence <= 1):
        raise ValueError(f"Invalid confidence: {confidence} (must be 0.0-1.0)")

    logger.info(f"Loaded config from {config_path}")
    return config
```

---

## GPU Resource Management

### Auto-Detect GPU Availability

```python
import torch

def get_device() -> str:
    """Detect best available device for ML operations."""
    if torch.cuda.is_available():
        return 'cuda'
    elif torch.backends.mps.is_available():  # Apple Silicon
        return 'mps'
    else:
        return 'cpu'

# Usage
device = get_device()
logger.info(f"Using device: {device}")

# EasyOCR
reader = easyocr.Reader(['en'], gpu=(device != 'cpu'))

# faster-whisper
model = WhisperModel("large-v3", device=device, compute_type="float16")
```

### Free GPU Memory After Use

```python
# ✅ GOOD: Free GPU memory when done
class Transcriber:
    def __init__(self, model_size: str = "large-v3"):
        self.model = WhisperModel(model_size, device="auto")

    def transcribe(self, video_path: Path) -> dict:
        result = self.model.transcribe(str(video_path))
        return result

    def __del__(self):
        """Free GPU memory on cleanup."""
        del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
```

### Apple Silicon (M1/M2/M3/M4) Considerations

**MPS (Metal Performance Shaders) backend** provides GPU acceleration on Apple Silicon.

#### Library Compatibility

| Library | MPS Support | Recommendation |
|---------|-------------|----------------|
| **faster-whisper** | Limited (CPU fallback reliable) | Use `device="auto"` - will use CPU if MPS unavailable |
| **EasyOCR** | Via PyTorch MPS | Set `gpu=True` - auto-detects MPS |
| **PyTorch** | Full support (1.12+) | Use `device="mps"` when available |

#### Device Detection for Apple Silicon

```python
import torch

def get_optimal_device() -> str:
    """Get best device with Apple Silicon fallback handling."""
    if torch.cuda.is_available():
        return 'cuda'
    elif torch.backends.mps.is_available():
        try:
            # Test MPS availability (sometimes reported but not functional)
            torch.zeros(1).to('mps')
            return 'mps'
        except Exception:
            logger.warning("MPS reported available but failed test, falling back to CPU")
            return 'cpu'
    else:
        return 'cpu'
```

#### Performance Expectations (M3 Pro, 36GB RAM)

- **EasyOCR**: ~200-300ms per frame (GPU) vs ~500-800ms (CPU) - **2-3x speedup**
- **faster-whisper**: Often CPU-optimised, MPS may not provide speedup - **test both**
- **PySceneDetect**: CPU-only (no GPU acceleration needed)

#### Memory Management on Unified Memory

Apple Silicon uses **unified memory** (shared between CPU/GPU). Be aware:

```python
# ⚠️ Apple Silicon: No separate GPU memory to clear
def cleanup_model(device: str):
    """Free resources appropriately for device type."""
    del model

    if device == 'cuda':
        torch.cuda.empty_cache()
    elif device == 'mps':
        # MPS uses unified memory - Python GC handles cleanup
        import gc
        gc.collect()
    # CPU: no special cleanup needed
```

#### Debugging MPS Issues

```python
# Enable MPS fallback to CPU on error
import os
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

# Disable MPS entirely if problematic
os.environ['PYTORCH_MPS_DISABLE'] = '1'
```

**Recommendation**: Use `device="auto"` for faster-whisper and `gpu=True` for EasyOCR. Both handle Apple Silicon gracefully with CPU fallback.

---

## JSON Schema Validation (Data Contracts)

### Validate Pipeline Stage Outputs

```python
from typing import TypedDict

class Scene(TypedDict):
    scene_id: int
    start_time: str
    end_time: str
    duration_seconds: float
    key_frame_path: str

def detect_scenes(video_path: Path) -> list[Scene]:
    """Detect scenes with validated output schema."""
    raw_scenes = run_pyscenedetect(video_path)

    # Validate each scene matches schema
    validated_scenes = []
    for scene in raw_scenes:
        try:
            validated = Scene(
                scene_id=scene['id'],
                start_time=scene['start'],
                end_time=scene['end'],
                duration_seconds=scene['duration'],
                key_frame_path=scene['frame']
            )
            validated_scenes.append(validated)
        except (KeyError, TypeError) as e:
            logger.error(f"Scene validation failed: {e}")
            raise

    return validated_scenes
```

### Use Pydantic for Runtime Validation

```python
from pydantic import BaseModel, validator

class TeamMatchResult(BaseModel):
    """Validated team matching output."""
    teams: list[str]
    confidence: float
    raw_ocr_text: str
    requires_manual_review: bool = False

    @validator('confidence')
    def confidence_in_range(cls, v):
        if not (0 <= v <= 1):
            raise ValueError('Confidence must be between 0 and 1')
        return v

    @validator('teams')
    def teams_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError('Teams list cannot be empty')
        return v

# Usage
def extract_teams(frame: Path) -> TeamMatchResult:
    raw_result = run_ocr_and_match(frame)
    return TeamMatchResult(**raw_result)  # Validates on creation
```

---

## Technology Alignment (Critical)

### faster-whisper NOT openai-whisper

```python
# ❌ BAD: Standard Whisper (4x slower)
import whisper
model = whisper.load_model("large-v3")
result = model.transcribe("video.mp4")

# ✅ GOOD: faster-whisper (same accuracy, 4x faster)
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="auto", compute_type="float16")
segments, info = model.transcribe("video.mp4", language="en", word_timestamps=True)
```

**Why**: 3-4 minutes vs 12-15 minutes for 90-min video.

### PySceneDetect NOT Raw OpenCV

```python
# ❌ BAD: Raw OpenCV (misses subtle transitions)
import cv2
cap = cv2.VideoCapture("video.mp4")
# ... manual frame difference calculation

# ✅ GOOD: PySceneDetect (purpose-built, handles fades/dissolves)
from scenedetect import detect, ContentDetector

scenes = detect("video.mp4", ContentDetector(threshold=30))
```

**Why**: Better transition detection, handles complex cuts.

### EasyOCR with GPU

```python
# ❌ BAD: Tesseract (poor accuracy on sports graphics)
import pytesseract
text = pytesseract.image_to_string("frame.jpg")

# ✅ GOOD: EasyOCR with GPU (90%+ accuracy on stylized text)
import easyocr
reader = easyocr.Reader(['en'], gpu=True)
results = reader.readtext("frame.jpg")
```

**Why**: 90%+ accuracy vs 60-70% for sports graphics.

---

## Error Recovery Patterns

### Retry with Exponential Backoff (for transient failures)

```python
import time

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s"
            )
            time.sleep(delay)

# Usage
result = retry_with_backoff(
    lambda: ocr_reader.readtext("frame.jpg"),
    max_retries=3
)
```

### Fallback to Manual Review

```python
def process_match(match_data: dict) -> dict:
    """Process match with fallback to manual review."""
    result = {
        'match_id': match_data['id'],
        'status': 'automated'
    }

    try:
        # Attempt automated processing
        teams = extract_teams_automated(match_data['frames'])
        result['teams'] = teams
        result['confidence'] = teams['confidence']

        if teams['confidence'] < 0.7:
            result['status'] = 'requires_manual_review'
            result['reason'] = 'low_confidence'

    except TeamNotFoundError:
        # Fallback to manual review
        result['status'] = 'requires_manual_review'
        result['reason'] = 'team_extraction_failed'
        result['teams'] = None

    return result
```

---

## Performance Patterns

### Use Generators for Large Data

```python
# ❌ BAD: Loads all frames into memory
def extract_frames(video_path: Path) -> list[np.ndarray]:
    frames = []
    cap = cv2.VideoCapture(str(video_path))
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    return frames

# ✅ GOOD: Generator (processes one frame at a time)
def extract_frames(video_path: Path) -> Iterator[np.ndarray]:
    """Generate frames one at a time (memory efficient)."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            yield frame
    finally:
        cap.release()

# Usage
for frame in extract_frames(video_path):
    process_frame(frame)  # Process one at a time
```

### Batch OCR Operations

```python
# ⚠️ ACCEPTABLE: Process frames one-by-one
for scene in scenes:
    teams = ocr_reader.readtext(scene['frame'])

# ✅ BETTER: Batch OCR for efficiency
frame_paths = [scene['frame'] for scene in scenes]
all_results = []

# Process in batches of 10
for i in range(0, len(frame_paths), 10):
    batch = frame_paths[i:i+10]
    batch_results = [ocr_reader.readtext(f) for f in batch]
    all_results.extend(batch_results)
```

---

## Summary

**Critical patterns**:
1. **Never re-run Whisper** - cache with config versioning
2. **Graceful degradation** - one failure doesn't block pipeline
3. **Confidence thresholds** - >0.9 accept, 0.7-0.9 log, <0.7 flag
4. **Config-driven** - load once, validate early, inject everywhere
5. **GPU management** - auto-detect, free memory after use
6. **Technology alignment** - faster-whisper, PySceneDetect, EasyOCR
7. **Error context** - log with episode_id, stage, file paths

**Performance**:
- Use generators for large data
- Batch OCR operations
- Free GPU memory when done
- Cache everything expensive
