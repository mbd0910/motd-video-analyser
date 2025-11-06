# Testing Guidelines

Testing conventions and coverage expectations for the MOTD Analyser project.

---

## Testing Framework

**Use pytest** for all testing.

```bash
# Install
pip install pytest pytest-cov pytest-mock

# Run tests
pytest

# Run with coverage
pytest --cov=src/motd_analyzer --cov-report=html

# Run specific test file
pytest tests/test_scene_detection.py

# Run with markers
pytest -m "not slow"  # Skip slow tests (integration)
```

---

## Coverage Expectations

### Target Coverage by Component

| Component | Minimum Coverage | Priority | Rationale |
|-----------|-----------------|----------|-----------|
| **Pipeline orchestration** | 100% | Critical | Core workflow - must be bulletproof |
| **Cache invalidation** | 100% | Critical | Bugs cause hours of re-processing |
| **Team matching (OCR)** | 90% | Critical | Core feature - must be accurate |
| **Scene detection** | 80% | High | Important but library-dependent |
| **Transcription** | 80% | High | Expensive operation - must cache correctly |
| **Config loading** | 80% | High | Invalid config breaks pipeline |
| **CLI argument parsing** | 60% | Medium | User-facing but straightforward |
| **Utility functions** | 70% | Medium | Helper code - important but simple |
| **Logging/debugging** | 30% | Low | Nice-to-have, not critical |

### Overall Target

**>80% code coverage** for `src/motd_analyzer/` package.

---

## What to Test (Priority Levels)

### Critical (Must Have Tests)

**Pipeline orchestration**:
```python
def test_pipeline_processes_all_stages():
    """Pipeline should run scene detection → OCR → transcription → analysis."""
    pass

def test_pipeline_uses_cache_when_available():
    """Pipeline should skip stages if cached results exist."""
    pass

def test_pipeline_continues_after_non_critical_failure():
    """If OCR fails for one scene, pipeline should continue."""
    pass
```

**Cache invalidation**:
```python
def test_cache_invalidated_when_config_changes():
    """Changing config should invalidate cached results."""
    pass

def test_cache_version_hash_updates_on_config_change():
    """Cache version hash should change when config changes."""
    pass
```

**Team matching**:
```python
def test_exact_team_name_match():
    """Should match exact team names."""
    pass

def test_fuzzy_team_name_match_with_ocr_errors():
    """Should match 'ARSEN4L' to 'Arsenal' (OCR mistake)."""
    pass

def test_no_match_raises_team_not_found_error():
    """Should raise TeamNotFoundError when no match found."""
    pass
```

---

### High Priority (Should Have Tests)

**Scene detection configuration**:
```python
def test_scene_detection_respects_threshold_config():
    """Should use threshold from config.yaml."""
    pass

def test_scene_detection_min_duration_filtering():
    """Should filter out scenes shorter than min_scene_duration."""
    pass
```

**Transcription caching**:
```python
def test_transcription_cached_after_first_run():
    """Should cache transcript.json and reuse on subsequent calls."""
    pass

def test_transcription_not_rerun_if_cache_valid():
    """Should NOT call Whisper if cached transcript exists with matching config."""
    pass
```

---

### Medium Priority (Nice to Have)

**Utility functions**:
```python
def test_video_duration_extraction():
    """Should extract correct duration from video file metadata."""
    pass

def test_json_serialization_with_numpy_types():
    """Should handle numpy.float32 when writing JSON."""
    pass
```

---

### Low Priority (Optional)

**Logging**:
```python
def test_logger_includes_episode_id_in_context():
    """Logs should include episode_id for debugging."""
    pass
```

---

## Test Organisation

### Directory Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── test_scene_detection.py      # Scene detection tests
├── test_ocr.py                  # OCR + team matching tests
├── test_transcription.py        # Whisper transcription tests
├── test_analysis.py             # Segment classification tests
├── test_pipeline.py             # Integration tests
├── test_cache_manager.py        # Caching logic tests
├── fixtures/                    # Test data
│   ├── sample_video_30s.mp4     # Short video for testing
│   ├── sample_scenes.json
│   └── sample_config.yaml
└── integration/                 # Slow integration tests
    └── test_full_pipeline.py
```

### Naming Conventions

```python
# Test files: test_*.py
# test_scene_detection.py

# Test functions: test_*
def test_scene_detector_returns_list_of_dicts():
    pass

# Test classes (group related tests): Test*
class TestTeamMatcher:
    def test_exact_match(self):
        pass

    def test_fuzzy_match_with_typo(self):
        pass
```

---

## Fixtures (conftest.py)

Use pytest fixtures for reusable test data and mocks.

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_config():
    """Load sample config for testing."""
    return {
        'scene_detection': {'threshold': 30.0, 'min_scene_duration': 3.0},
        'ocr': {'confidence_threshold': 0.7},
        'transcription': {'model': 'large-v3'}
    }

@pytest.fixture
def sample_video_path(tmp_path):
    """Path to sample 30-second test video."""
    return Path("tests/fixtures/sample_video_30s.mp4")

@pytest.fixture
def premier_league_teams():
    """Load Premier League team names."""
    return [
        "Arsenal", "Chelsea", "Liverpool", "Manchester United",
        "Manchester City", "Tottenham Hotspur", # ... etc
    ]

@pytest.fixture
def mock_whisper_model(mocker):
    """Mock Whisper model to avoid loading 10GB model in tests."""
    mock_model = mocker.Mock()
    mock_model.transcribe.return_value = {
        'text': 'Sample transcript',
        'segments': []
    }
    return mock_model
```

---

## Mocking Strategies

### When to Mock

✅ **Mock these**:
- Expensive operations (Whisper model loading, video processing)
- External dependencies (file I/O, network calls)
- Time-consuming operations (scene detection on long videos)

❌ **Don't mock these**:
- Business logic you're testing
- Simple utility functions
- Library APIs you want to integration-test

### Mocking Examples

**Mock Whisper model**:
```python
def test_transcription_with_mock_whisper(mocker, sample_video_path):
    """Test transcription without loading actual Whisper model."""
    mock_model = mocker.Mock()
    mock_model.transcribe.return_value = {
        'text': 'Welcome to Match of the Day',
        'segments': [{'start': 0.0, 'end': 3.0, 'text': 'Welcome to Match of the Day'}]
    }

    mocker.patch('faster_whisper.WhisperModel', return_value=mock_model)

    transcriber = Transcriber()
    result = transcriber.transcribe(sample_video_path)

    assert result['text'] == 'Welcome to Match of the Day'
    mock_model.transcribe.assert_called_once()
```

**Mock file I/O**:
```python
def test_cache_manager_loads_from_file(mocker, tmp_path):
    """Test cache loading without actual file I/O."""
    cache_file = tmp_path / "scenes.json"
    cache_data = {'scenes': [{'scene_id': 1, 'duration': 45.0}]}

    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('json.load', return_value=cache_data)

    cache_manager = CacheManager(cache_dir=tmp_path)
    result = cache_manager.get("episode_001", "scenes")

    assert result == cache_data
```

---

## Integration Tests

**Test full pipeline on small sample video (30 seconds).**

```python
# tests/integration/test_full_pipeline.py
import pytest

@pytest.mark.slow  # Mark slow tests
def test_full_pipeline_on_sample_video(sample_video_path, sample_config, tmp_path):
    """Run full pipeline on 30-second test video."""
    pipeline = PipelineOrchestrator(
        scene_detector=SceneDetector(threshold=sample_config['scene_detection']['threshold']),
        ocr_processor=OCRProcessor(),
        transcriber=Transcriber(),
        cache_manager=CacheManager(cache_dir=tmp_path)
    )

    result = pipeline.process(sample_video_path, episode_id="test_001")

    # Validate output structure
    assert 'scenes' in result
    assert 'teams' in result
    assert 'transcript' in result
    assert len(result['scenes']) > 0  # Should detect at least one scene
```

**Run integration tests separately**:
```bash
# Run only fast unit tests (default)
pytest -m "not slow"

# Run integration tests explicitly
pytest -m "slow"
```

---

## Parametrized Tests

Use `@pytest.mark.parametrize` to test multiple inputs.

```python
@pytest.mark.parametrize("ocr_text,expected_team", [
    ("ARSENAL 2-1 CHELSEA", "Arsenal"),
    ("Manch3st3r Unit3d", "Manchester United"),  # OCR errors
    ("LIVERPOOL FC", "Liverpool"),
    ("Spurs", "Tottenham Hotspur"),  # Nickname
])
def test_team_extraction_from_ocr_text(ocr_text, expected_team, premier_league_teams):
    """Test team extraction handles various OCR outputs."""
    matcher = TeamMatcher(team_list=premier_league_teams)
    result = matcher.match(ocr_text)
    assert expected_team in result['teams']
```

---

## Validation Tests (Manual Labels vs Automated)

**Compare automated analysis against manually labeled ground truth.**

```python
def test_automated_classification_matches_manual_labels():
    """Compare automated segment classification against manual labels."""
    # Load manual ground truth (created by human reviewer)
    manual_labels = load_json("tests/fixtures/episode_001_manual_labels.json")

    # Run automated pipeline
    automated_result = pipeline.process("tests/fixtures/sample_video_30s.mp4")

    # Compare classifications
    correct = 0
    total = len(manual_labels['scenes'])

    for scene_id, manual_label in manual_labels['scenes'].items():
        auto_label = automated_result['scenes'][int(scene_id)]
        if auto_label['type'] == manual_label['type']:
            correct += 1

    accuracy = correct / total
    assert accuracy > 0.85, f"Classification accuracy {accuracy:.2%} below 85% threshold"
```

---

## What NOT to Test

❌ **Don't test library internals**:
```python
# ❌ BAD: Testing PySceneDetect library (not your code)
def test_pyscenedetect_detects_scenes():
    from scenedetect import detect, ContentDetector
    scenes = detect('video.mp4', ContentDetector())
    assert len(scenes) > 0  # This tests the library, not your code!

# ✅ GOOD: Test your wrapper/integration
def test_scene_detector_returns_correct_format():
    detector = SceneDetector(threshold=30.0)
    scenes = detector.detect('tests/fixtures/sample_video_30s.mp4')

    assert isinstance(scenes, list)
    assert all('scene_id' in s for s in scenes)
    assert all('duration_seconds' in s for s in scenes)
```

❌ **Don't test obvious getters/setters**:
```python
# ❌ BAD: Testing trivial property
def test_config_loader_sets_threshold():
    config = ConfigLoader()
    config.threshold = 30.0
    assert config.threshold == 30.0  # Pointless test
```

---

## Test Data Management

### Use Small Test Files

- **Video**: 30-second sample (not 90-minute full episode)
- **Images**: Low resolution (480p, not 1080p)
- **Audio**: Short clips (10 seconds)

### Commit Test Fixtures to Repo

```
tests/fixtures/
├── sample_video_30s.mp4          # ~5MB (acceptable)
├── sample_frame_scoreboard.jpg   # ~50KB
├── sample_scenes.json
├── sample_transcript.json
└── premier_league_teams_test.json
```

---

## Running Tests in CI/CD

```yaml
# .github/workflows/test.yml (example)
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock

      - name: Run tests
        run: pytest --cov=src/motd_analyzer --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Summary

**Test priorities**:
1. **Critical**: Pipeline orchestration, caching, team matching (100% coverage)
2. **High**: Scene detection, transcription, config (80% coverage)
3. **Medium**: Utilities, CLI (60-70% coverage)
4. **Low**: Logging, debugging (30% coverage)

**Testing philosophy**:
- Mock expensive operations (Whisper, video processing)
- Integration test on small sample video
- Validate against manual labels for accuracy
- Don't test library internals
- Use parametrized tests for multiple inputs

**Coverage target**: >80% overall
