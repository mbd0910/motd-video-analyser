# Python Architecture Patterns

Architectural and design pattern guidelines for the MOTD Analyser project.

**Review Level**: These are **advisory** unless marked as "monumental smells" (blocking).

---

## Single Responsibility Principle

### Module/Function Responsibility

**Each module/function should have one clear purpose.**

```python
# ❌ BAD: Function does too much
def process_video(video_path: Path) -> dict:
    """Process video: detect scenes, run OCR, transcribe, analyse."""
    scenes = detect_scenes(video_path)  # Scene detection
    teams = extract_teams_from_frames(scenes)  # OCR
    transcript = transcribe_audio(video_path)  # Transcription
    analysis = classify_segments(scenes, teams, transcript)  # Analysis
    return analysis

# ✅ GOOD: Orchestrator delegates to focused modules
class PipelineOrchestrator:
    def __init__(self, scene_detector, ocr_processor, transcriber, analyser):
        self.scene_detector = scene_detector
        self.ocr_processor = ocr_processor
        self.transcriber = transcriber
        self.analyser = analyser

    def process(self, video_path: Path) -> dict:
        """Orchestrate pipeline stages."""
        scenes = self.scene_detector.detect(video_path)
        teams = self.ocr_processor.extract_teams(scenes)
        transcript = self.transcriber.transcribe(video_path)
        return self.analyser.classify(scenes, teams, transcript)
```

**Advisory Flag**: Functions >50 lines or modules with >3 responsibilities

**Monumental Smell** 🚨: Functions >200 lines doing multiple unrelated things

---

## Dependency Injection

### Avoid Hardcoded Dependencies

**Don't hardcode library/implementation choices - inject them.**

```python
# ❌ BAD: Hardcoded to EasyOCR
class TeamExtractor:
    def __init__(self):
        import easyocr
        self.reader = easyocr.Reader(['en'], gpu=True)  # Hardcoded

    def extract(self, image_path: Path) -> list[str]:
        results = self.reader.readtext(str(image_path))
        return [text for (bbox, text, conf) in results]

# ✅ GOOD: Dependency injection (easy to swap PaddleOCR later)
from typing import Protocol

class OCRReader(Protocol):
    """Interface for OCR readers."""
    def readtext(self, image_path: str) -> list[tuple]:
        ...

class TeamExtractor:
    def __init__(self, ocr_reader: OCRReader):
        self.ocr_reader = ocr_reader

    def extract(self, image_path: Path) -> list[str]:
        results = self.ocr_reader.readtext(str(image_path))
        return [text for (bbox, text, conf) in results]

# Usage
import easyocr
reader = easyocr.Reader(['en'], gpu=True)
extractor = TeamExtractor(ocr_reader=reader)
```

**Advisory Flag**: Direct instantiation of third-party libraries in business logic

**When to skip**: YAGNI - if you're 99% sure you won't swap libraries, hardcoding is fine initially

---

## Resource Management

### Load Expensive Resources Once

**Don't reload expensive resources (ML models, large files) repeatedly.**

```python
# ❌ BAD: Loads Whisper model on every call
def transcribe_video(video_path: Path) -> dict:
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3")  # 10GB model loaded every call!
    return model.transcribe(str(video_path))

# ✅ GOOD: Load once, reuse instance
class Transcriber:
    def __init__(self, model_size: str = "large-v3"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_size, device="auto")

    def transcribe(self, video_path: Path) -> dict:
        return self.model.transcribe(str(video_path))

# Usage
transcriber = Transcriber()  # Load once
for video in videos:
    result = transcriber.transcribe(video)  # Reuse model
```

**Advisory Flag**: ML models/large resources loaded inside loops or functions

**Monumental Smell** 🚨: Loading multi-GB models repeatedly in production code

---

## Pipeline Patterns

### Orchestrator Pattern (Decouple Stages)

**Pipeline stages shouldn't call each other directly - use an orchestrator.**

```python
# ❌ BAD: Tight coupling between stages
class SceneDetector:
    def detect(self, video_path: Path) -> list[dict]:
        scenes = self._detect_scenes(video_path)
        # Stage directly calls next stage - tight coupling!
        ocr_processor = OCRProcessor()
        teams = ocr_processor.extract_teams(scenes)
        return teams

# ✅ GOOD: Orchestrator coordinates stages
class PipelineOrchestrator:
    def __init__(
        self,
        scene_detector: SceneDetector,
        ocr_processor: OCRProcessor,
        cache_manager: CacheManager
    ):
        self.scene_detector = scene_detector
        self.ocr_processor = ocr_processor
        self.cache = cache_manager

    def process(self, video_path: Path, episode_id: str) -> dict:
        """Run full pipeline with caching."""
        # Each stage is independent
        scenes = self.cache.get_or_run(
            episode_id, "scenes",
            lambda: self.scene_detector.detect(video_path)
        )

        teams = self.cache.get_or_run(
            episode_id, "teams",
            lambda: self.ocr_processor.extract_teams(scenes)
        )

        return {"scenes": scenes, "teams": teams}
```

**Advisory Flag**: Pipeline stages calling each other directly

**Benefit**: Easy to test, cache, or skip individual stages

---

## Caching Patterns

### Centralized Cache Logic

**Don't scatter cache checks throughout code - centralize them.**

```python
# ❌ BAD: Cache logic repeated everywhere
def detect_scenes(video_path: Path, cache_dir: Path) -> list[dict]:
    cache_file = cache_dir / "scenes.json"
    if cache_file.exists():  # Cache logic here
        with cache_file.open('r') as f:
            return json.load(f)

    scenes = run_scene_detection(video_path)

    with cache_file.open('w') as f:  # Cache logic here
        json.dump(scenes, f)

    return scenes

# ✅ GOOD: Decorator pattern for caching
def cached(cache_key: str):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result

            result = func(self, *args, **kwargs)
            self.cache.set(cache_key, result)
            return result
        return wrapper
    return decorator

class SceneDetector:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    @cached("scenes")
    def detect(self, video_path: Path) -> list[dict]:
        return run_scene_detection(video_path)
```

**Alternative**: Cache Manager class with `get_or_run()` method (shown in orchestrator example)

**Advisory Flag**: Cache file I/O scattered across >3 functions

---

## Error Handling Patterns

### Specific Exceptions with Context

**Avoid silent failures - raise specific exceptions with context.**

```python
# ❌ BAD: Silent failure
def match_team(ocr_text: str, teams: list[str]) -> str | None:
    try:
        return fuzzy_match(ocr_text, teams)[0]
    except:
        return None  # What went wrong? Unknown.

# ❌ BAD: Generic exception
def match_team(ocr_text: str, teams: list[str]) -> str:
    try:
        return fuzzy_match(ocr_text, teams)[0]
    except Exception as e:
        raise Exception("Team matching failed")  # No context!

# ✅ GOOD: Specific exception with context
class TeamNotFoundError(ValueError):
    """Raised when OCR text doesn't match any known team."""
    pass

def match_team(ocr_text: str, teams: list[str]) -> str:
    try:
        matches = fuzzy_match(ocr_text, teams)
    except Exception as e:
        raise TeamNotFoundError(
            f"Fuzzy matching failed for '{ocr_text}': {e}"
        ) from e

    if not matches:
        raise TeamNotFoundError(
            f"No team match found for OCR text: '{ocr_text}'"
        )

    return matches[0]
```

**Monumental Smell** 🚨: Bare `except:` or `except Exception: pass` (silent failures)

---

## Configuration Management

### Single Source of Truth

**Load config once, pass to components - don't reload config everywhere.**

```python
# ❌ BAD: Config loaded in multiple places
class SceneDetector:
    def detect(self, video_path: Path) -> list[dict]:
        config = yaml.safe_load(open('config.yaml'))  # Loaded here
        threshold = config['scene_detection']['threshold']
        ...

class OCRProcessor:
    def extract_teams(self, scenes: list) -> dict:
        config = yaml.safe_load(open('config.yaml'))  # Loaded again
        regions = config['ocr']['regions']
        ...

# ✅ GOOD: Config loaded once, injected
class ConfigLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            with open('config.yaml') as f:
                cls._instance.config = yaml.safe_load(f)
        return cls._instance

# Or simpler: Just load at app startup
def main():
    config = load_config('config.yaml')

    scene_detector = SceneDetector(
        threshold=config['scene_detection']['threshold']
    )
    ocr_processor = OCRProcessor(
        regions=config['ocr']['regions']
    )
```

**Advisory Flag**: Config file opened in >2 places

---

## Type Safety (Strict Typing Preference)

### Pydantic for Data Validation

**Use Pydantic for type-safe data contracts between pipeline stages.**

```python
# ⚠️ ACCEPTABLE: Plain dict (if simple)
def detect_scenes(video_path: Path) -> list[dict]:
    return [{"scene_id": 1, "start_time": "00:00:00", "duration": 45.0}]

# ✅ BETTER: TypedDict for type hints
from typing import TypedDict

class Scene(TypedDict):
    scene_id: int
    start_time: str
    duration_seconds: float

def detect_scenes(video_path: Path) -> list[Scene]:
    return [{"scene_id": 1, "start_time": "00:00:00", "duration_seconds": 45.0}]

# ✅ BEST: Pydantic for runtime validation
from pydantic import BaseModel, validator

class Scene(BaseModel):
    scene_id: int
    start_time: str
    duration_seconds: float

    @validator('duration_seconds')
    def duration_positive(cls, v):
        if v <= 0:
            raise ValueError('Duration must be positive')
        return v

def detect_scenes(video_path: Path) -> list[Scene]:
    raw_scenes = run_detection(video_path)
    return [Scene(**s) for s in raw_scenes]  # Validates on creation
```

**When to use Pydantic**: Complex data structures, external input, API contracts

**When to skip**: Internal helper functions, simple data (YAGNI)

---

## YAGNI Violations (Don't Over-Engineer)

### Premature Abstraction

**Don't create abstractions until you need them.**

```python
# ❌ BAD: Over-engineered for single use case
class AbstractVideoProcessor(ABC):
    @abstractmethod
    def process(self, video: Path) -> dict:
        pass

class AbstractSceneDetector(ABC):
    @abstractmethod
    def detect(self, video: Path) -> list:
        pass

class PySceneDetectAdapter(AbstractSceneDetector):
    def detect(self, video: Path) -> list:
        # Only one implementation exists!
        ...

# ✅ GOOD: Start simple, refactor when needed
class SceneDetector:
    def detect(self, video_path: Path) -> list[dict]:
        return detect_scenes_with_pyscenedetect(video_path)

# If you later need to swap implementations, THEN add abstraction
```

**Advisory Flag**: Abstract base classes with only one implementation

**When abstractions make sense**: Multiple implementations exist or are planned (e.g., EasyOCR vs PaddleOCR)

---

## Monumental Smells (Blocking Issues)

These are **critical architectural problems** that should block merge:

### 1. 200+ Line Functions

```python
# 🚨 BLOCKING: Function with 250 lines doing scene detection + OCR + analysis
def process_everything(video_path: Path) -> dict:
    # ... 250 lines of mixed concerns ...
    pass
```

**Fix**: Split into focused functions/classes

### 2. Circular Dependencies

```python
# 🚨 BLOCKING: Module A imports Module B, Module B imports Module A
# src/motd_analyzer/scene_detection/detector.py
from motd_analyzer.ocr.reader import OCRReader  # Imports OCR

# src/motd_analyzer/ocr/reader.py
from motd_analyzer.scene_detection.detector import SceneDetector  # Imports scenes!
```

**Fix**: Extract shared code to new module or use dependency injection

### 3. Broken Caching (Data Loss Risk)

```python
# 🚨 BLOCKING: Cache invalidation never checks config changes
def get_cached_transcript(episode_id: str) -> dict:
    cache_file = f"cache/{episode_id}/transcript.json"
    if os.path.exists(cache_file):
        return json.load(open(cache_file))  # Never checks if config changed!

    # If Whisper model changed in config, we should re-run transcription
```

**Fix**: Implement cache versioning based on config hash

### 4. Security Issues

```python
# 🚨 BLOCKING: Command injection vulnerability
def extract_audio(video_path: str) -> None:
    os.system(f"ffmpeg -i {video_path} audio.wav")  # Vulnerable!

# ✅ FIX: Use subprocess with argument list
import subprocess
subprocess.run(['ffmpeg', '-i', video_path, 'audio.wav'], check=True)
```

### 5. Silent Data Loss

```python
# 🚨 BLOCKING: Errors swallowed, data silently lost
for match in matches:
    try:
        process_match(match)
    except:
        pass  # Match silently skipped, no logging!

# ✅ FIX: Log errors, track failures
failed_matches = []
for match in matches:
    try:
        process_match(match)
    except Exception as e:
        logger.error(f"Failed to process {match}: {e}")
        failed_matches.append(match)

if failed_matches:
    logger.warning(f"{len(failed_matches)} matches failed processing")
```

---

## When to Flag vs When to Block

### Advisory (Flag for Follow-Up)

- Functions >50 lines but <200 lines
- Repeated code in 2-3 places (suggest extraction)
- Missing dependency injection (but only one implementation exists)
- Inefficient pattern (but not performance-critical)

### Blocking (Must Fix Before Merge)

- Functions >200 lines
- Circular dependencies
- Broken caching (could cause hours of re-processing)
- Security vulnerabilities
- Silent data loss (bare `except: pass`)
- Missing error handling for critical operations (Whisper transcription, file I/O)

---

## Summary

**Good architecture prioritizes**:
1. Single responsibility (focused modules/functions)
2. Dependency injection (easy to test/swap)
3. Resource management (load expensive things once)
4. Graceful degradation (failures don't cascade)
5. YAGNI (don't over-engineer)

**Red flags** 🚨:
- Silent failures
- Tight coupling
- Scattered concerns
- Missing error context
- Repeated expensive operations
