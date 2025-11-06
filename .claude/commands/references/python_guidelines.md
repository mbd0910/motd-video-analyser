# Python Coding Guidelines

Guidelines for writing Python code in the MOTD Analyser project.

---

## Style & Conventions

### PEP 8 Compliance

Follow [PEP 8](https://peps.python.org/pep-0008/) with these project-specific overrides:

- **Line length**: 100 characters (not 79)
- **Spelling**: British English in comments, docstrings, and prose
- **Code identifiers**: US spelling acceptable (e.g., `motd_analyzer` package name)

### Naming Conventions

- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal: leading underscore (`_load_cache_version`)
- Boolean variables: `is_`/`has_`/`can_`/`should_` prefix

---

## Type Hints

### Enforcement

**Type hints are required** for all public functions and class methods.

### Type Hint Best Practices

- Use `Optional[T]` or `T | None` for nullable values
- Avoid bare `Any` - be specific with `dict[str, str | int]` instead of `dict[str, Any]`
- Use `Path` for file paths (more explicit than `str`)
- Use union types: `str | int | float` (Python 3.10+)
- Use `TypedDict` for structured dictionaries with known keys

---

## Docstrings

### Required For

- All public functions
- All public classes
- All public methods
- Complex private functions (discretion)

### Format: Google Style

```python
def extract_teams(
    ocr_text: str,
    team_list: list[str],
    confidence_threshold: float = 0.7
) -> dict[str, Any]:
    """Extract team names from OCR text using fuzzy matching.

    Matches raw OCR output against a list of known team names, using
    fuzzy string matching to handle OCR errors. Returns teams with
    confidence scores above the threshold.

    Args:
        ocr_text: Raw text extracted from video frame via OCR.
        team_list: List of valid Premier League team names.
        confidence_threshold: Minimum confidence score (0.0-1.0) for
            accepting a match. Defaults to 0.7.

    Returns:
        Dictionary containing:
            - 'teams': List of matched team names
            - 'confidence': Overall confidence score (float)
            - 'raw_text': Original OCR text

    Raises:
        ValueError: If confidence_threshold not in range [0.0, 1.0].

    Example:
        >>> extract_teams("ARSENAL 2-1 CHELSEA", premier_league_teams)
        {'teams': ['Arsenal', 'Chelsea'], 'confidence': 0.92, 'raw_text': '...'}
    """
    pass
```

### Docstring for Classes

```python
class CacheManager:
    """Manages pipeline stage caching with version-based invalidation.

    Handles reading/writing intermediate results (scenes, OCR, transcripts)
    with automatic cache invalidation when config changes. Uses SHA-256
    hashing of config snapshots to detect stale cache files.

    Attributes:
        cache_dir: Path to cache storage directory.
        config: Current pipeline configuration dict.
        cache_version: SHA-256 hash of current config.

    Example:
        >>> cache = CacheManager(Path("data/cache"), config)
        >>> cache.get("episode_001", "scenes")  # Returns cached data or None
    """

    def __init__(self, cache_dir: Path, config: dict):
        """Initialise cache manager with directory and config.

        Args:
            cache_dir: Path where cache files are stored.
            config: Pipeline configuration dictionary.
        """
        pass
```

---

## Pythonic Patterns

### List Comprehensions

Prefer list comprehensions over verbose `for` loops with `.append()`:
- Simple: `[team['name'] for team in teams]`
- With filter: `[t['name'] for t in teams if t['confidence'] > 0.7]`

### Context Managers

Use context managers (`with` statements) for resource management. For custom resources, implement `__enter__` and `__exit__`:

```python
class WhisperModel:
    def __enter__(self):
        self.model = load_model("large-v3")
        return self.model

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.model  # Free GPU memory
```

### Pathlib Over os.path

Use `pathlib.Path` instead of `os.path`:
- Path concatenation: `Path('data') / 'videos'`
- Create directories: `path.parent.mkdir(parents=True, exist_ok=True)`
- Check existence: `path.exists()`, `path.is_file()`, `path.is_dir()`
- List files: `list(path.iterdir())` or `path.glob('*.mp4')`

### F-Strings for Formatting

Use f-strings (not `.format()` or `+` concatenation):
- Basic: `f"Team: {team}, Score: {score}"`
- With expressions: `f"Team: {team.upper()}, Score: {score * 2}"`

---

## Error Handling

### Specific Exceptions

Catch specific exceptions, not bare `except:` or broad `Exception`:
- Use `FileNotFoundError`, `ValueError`, `KeyError` instead of `Exception`
- Log errors with context (video path, episode ID, etc.)
- Re-raise if you can't handle: `raise`

### Logging with Context

```python
import logging

logger = logging.getLogger(__name__)

# BAD: Generic error message
logger.error("Failed to process video")

# GOOD: Context included
logger.error(
    f"Failed to process video: {video_path}",
    extra={
        'video_path': str(video_path),
        'episode_id': episode_id,
        'stage': 'scene_detection'
    }
)

# GOOD: Exception logging
try:
    scenes = detect_scenes(video_path)
except Exception as e:
    logger.exception(
        f"Scene detection failed for {episode_id}",
        exc_info=True  # Includes stack trace
    )
    raise
```

### Custom Exceptions

```python
# GOOD: Project-specific exceptions
class CacheInvalidError(Exception):
    """Raised when cache version doesn't match config."""
    pass

class TeamNotFoundError(ValueError):
    """Raised when OCR text doesn't match any known team."""
    pass

# Usage
def match_team(ocr_text: str, teams: list[str]) -> str:
    """Match OCR text to team name."""
    matches = fuzzy_match(ocr_text, teams)
    if not matches:
        raise TeamNotFoundError(
            f"No team match found for OCR text: '{ocr_text}'"
        )
    return matches[0]
```

---

## Module Structure

### Import Order

```python
# 1. Standard library imports
import json
import logging
from pathlib import Path
from typing import Any, Optional

# 2. Third-party imports
import cv2
import numpy as np
import yaml
from scenedetect import detect, ContentDetector

# 3. Local/project imports
from motd_analyzer.utils import json_utils
from motd_analyzer.pipeline import cache_manager
```

### `__all__` for Public API

Define `__all__` in `__init__.py` to explicitly control public exports.

### Main Guard

Use `if __name__ == '__main__':` to protect module-level code execution.

---

## Performance

### Generators Over Lists (When Appropriate)

```python
# BAD: Loads entire list into memory
def read_frames(video_path: Path) -> list[np.ndarray]:
    frames = []
    cap = cv2.VideoCapture(str(video_path))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    return frames

# GOOD: Generator for large data
def read_frames(video_path: Path) -> Iterator[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame
```

### Avoid Premature Optimisation


---

## Project-Specific Guidelines

### faster-whisper Over openai-whisper

```python
# BAD: Standard whisper (4x slower)
import whisper
model = whisper.load_model("large-v3")

# GOOD: faster-whisper (same accuracy, 4x faster)
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="auto", compute_type="float16")
```

### EasyOCR GPU Configuration

```python
# GOOD: Enable GPU if available
import easyocr

reader = easyocr.Reader(['en'], gpu=True)  # Auto-detects GPU

# GOOD: Check GPU availability
import torch

gpu_available = torch.cuda.is_available() or torch.backends.mps.is_available()
reader = easyocr.Reader(['en'], gpu=gpu_available)
```

### Caching Patterns

```python
# GOOD: Check cache before expensive operation
def transcribe_video(video_path: Path, cache_dir: Path) -> dict:
    """Transcribe video audio using Whisper."""
    cache_file = cache_dir / f"{video_path.stem}_transcript.json"

    # Check cache first
    if cache_file.exists():
        logger.info(f"Loading cached transcript for {video_path.name}")
        with cache_file.open('r') as f:
            return json.load(f)

    # Run expensive operation
    logger.info(f"Transcribing {video_path.name} (this may take 3-4 minutes)")
    transcript = model.transcribe(str(video_path))

    # Save to cache
    with cache_file.open('w') as f:
        json.dump(transcript, f, indent=2)

    return transcript
```

---

## Common Anti-Patterns to Avoid

### Mutable Default Arguments

```python
# BAD: Mutable default
def add_team(team: str, team_list: list = []) -> list:
    team_list.append(team)
    return team_list

# GOOD: None with runtime creation
def add_team(team: str, team_list: list | None = None) -> list:
    if team_list is None:
        team_list = []
    team_list.append(team)
    return team_list
```

### Dictionary Key Access Without Checking

Use `.get()` with defaults or check keys before access to avoid `KeyError`:
- `dict.get('key', default_value)`
- `if 'key' in dict: ...`

---

## Testing Considerations

See `.claude/commands/references/testing_guidelines.md` for detailed testing practices.

**Key principle**: Write testable code
- Avoid hardcoded paths
- Use dependency injection
- Keep functions pure when possible
- Separate I/O from logic

---

## Resources

- [PEP 8](https://peps.python.org/pep-0008/) - Style Guide
- [PEP 484](https://peps.python.org/pep-0484/) - Type Hints
- [PEP 257](https://peps.python.org/pep-0257/) - Docstring Conventions
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
