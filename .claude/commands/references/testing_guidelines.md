# Testing Guidelines

Testing conventions and coverage expectations for the MOTD Analyser project.

---

## Testing Framework

**Use pytest** for all testing.

Installation: `pip install pytest pytest-cov pytest-mock`

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
- Pipeline should run scene detection → OCR → transcription → analysis
- Pipeline should skip stages if cached results exist
- If OCR fails for one scene, pipeline should continue

**Cache invalidation**:
- Changing config should invalidate cached results
- Cache version hash should change when config changes

**Team matching**:
- Should match exact team names
- Should match 'ARSEN4L' to 'Arsenal' (OCR mistake)
- Should raise TeamNotFoundError when no match found

---

### High Priority (Should Have Tests)

**Scene detection configuration**:
- Should use threshold from config.yaml
- Should filter out scenes shorter than min_scene_duration

**Transcription caching**:
- Should cache transcript.json and reuse on subsequent calls
- Should NOT call Whisper if cached transcript exists with matching config

---

### Medium Priority (Nice to Have)

**Utility functions**:
- Should extract correct duration from video file metadata
- Should handle numpy.float32 when writing JSON

---

### Low Priority (Optional)

**Logging**:
- Logs should include episode_id for debugging

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

- Test files: `test_*.py` (e.g., `test_scene_detection.py`)
- Test functions: `test_*` (e.g., `test_scene_detector_returns_list_of_dicts()`)
- Test classes (group related tests): `Test*` (e.g., `TestTeamMatcher`)

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

## TDD for Pipeline Stage Features

**Pattern**: RED → GREEN → REFACTOR

**When to use**: Implementing new detection logic or algorithms in multi-stage pipelines (e.g., interlude detection, table review detection, match boundary detection).

### Workflow Steps

#### 1. RED Phase: Write Failing Tests

Write **5+ tests** covering:
- ✅ **Happy path** (real data from cached episodes)
- ✅ **Validation edge cases** (insufficient signals, threshold boundaries)
- ✅ **False positives** (keyword matches that should be rejected)
- ✅ **Variations** (multiple valid phrasings/patterns)
- ✅ **Integration** (method composition, end-to-end flow)

**Expected outcome**: All new tests fail (method doesn't exist or returns None)

```python
# Example: RED phase for table review detection
class TestTableReviewDetection:
    def test_detect_table_review_match7_dual_signal(self, detector, transcript):
        """Should detect table review at ~4977s with foreign team validation."""
        result = detector._detect_table_review(...)  # ❌ AttributeError (method doesn't exist)
        assert result is not None
        assert 4975 <= result <= 4980

    def test_table_review_insufficient_foreign_teams(self, detector):
        """Should reject if <2 foreign teams mentioned after keyword."""
        # Test implementation...

    # ... 3 more tests
```

#### 2. GREEN Phase: Minimal Implementation

- Implement **just enough code** to pass all tests
- Don't optimize yet (focus on correctness)
- Verify **100% test pass rate** (new + existing tests)

**Expected outcome**: All tests pass (e.g., 57/57 if you added 5 tests to 52 existing)

```python
# Example: GREEN phase implementation
def _detect_table_review(self, teams, highlights_end, episode_duration, segments, all_teams):
    """Detect league table review using keyword + foreign team validation."""
    # 1. Filter segments in post-match window
    gap_segments = [s for s in segments if highlights_end <= s.get('start', 0) < episode_duration]

    # 2. Extract sentences for keyword detection
    sentences = self._extract_sentences_from_segments(gap_segments)

    # 3. Search for table keyword
    for sentence in sentences:
        if "table" in sentence['text'].lower() and any(kw in sentence['text'].lower() for kw in ["look", "league"]):
            keyword_timestamp = sentence['start']

            # 4. Validate with foreign team mentions
            foreign_teams = {team for seg in segments for team in all_teams if team not in teams and self._fuzzy_team_match(seg['text'], team)}

            if len(foreign_teams) >= 2:
                return keyword_timestamp  # ✅ Tests pass

    return None
```

#### 3. REFACTOR Phase: Improve Code Quality

- Extract magic numbers to constants
- Remove duplication (DRY principle)
- Improve naming/documentation
- **Critical**: Re-run tests after each refactor to catch regressions

**Expected outcome**: Same test pass rate (57/57), cleaner code

```python
# Example: REFACTOR phase improvements
# - Extracted validation logic to separate section
# - Added detailed comments
# - Improved variable names (keyword_timestamp → table_keyword_timestamp)
# Tests still pass: 57/57 ✅
```

---

### Handling Test Failures

**If tests fail during GREEN phase:**
- ❌ **Don't modify tests** to match implementation (defeats purpose of TDD)
- ✅ **Fix implementation** to match test expectations
- ✅ **If test expectations are wrong**, restart RED phase with corrected tests

**If tests fail during REFACTOR phase:**
- ❌ **Don't commit refactor** (you broke functionality)
- ✅ **Revert changes**, identify which refactor broke tests
- ✅ **Fix refactor** or split into smaller steps

---

### Real Example: Task 012-02 (League Table Detection)

**RED Phase** ([commit 919ee7d](https://github.com/.../commit/919ee7d)):
```python
# 5 tests written, all failing (method doesn't exist)
def test_detect_table_review_match7_dual_signal(self, detector, transcript):
    result = detector._detect_table_review(...)  # ❌ AttributeError
    assert result is not None
    assert 4970 <= result <= 4975

# Run: pytest → 5 new failures, 52 existing pass
# Status: ❌ 52/57 tests passing
```

**GREEN Phase** ([commit b2c7e7e](https://github.com/.../commit/b2c7e7e)):
```python
# Method implemented, all 57 tests passing
def _detect_table_review(self, teams, highlights_end, episode_duration, segments, all_teams):
    # Keyword detection logic...
    # Foreign team validation logic...
    return table_keyword_timestamp  # ✅ Tests pass

# Run: pytest → All tests pass
# Status: ✅ 57/57 tests passing
```

**REFACTOR Phase** ([commit 4fc786c](https://github.com/.../commit/4fc786c)):
```python
# Removed INTERLUDE_BUFFER_SECONDS constant (simplified)
# Updated docstrings for clarity
# Tests updated to match new expectations (still passing)

# Run: pytest → All tests pass
# Status: ✅ 57/57 tests passing (cleaner code, same functionality)
```

**Outcome**: 5 new tests added, 0 regressions, 100% pass rate maintained throughout.

---

### Benefits of TDD for Pipeline Features

- ✅ **Prevents scope creep** (only implement what tests require)
- ✅ **Documents behavior** (tests = specification)
- ✅ **Catches regressions** (refactors can't break existing functionality)
- ✅ **Builds confidence** (always working code, never stuck in broken state)
- ✅ **Faster debugging** (failing test pinpoints exact issue)

**See also**:
- [Code Quality Checklist - Testing Section](code_quality_checklist.md#testing)
- [Task 012-02 Phase 6](../../docs/tasks/012-classifier-integration/012-02-match-end-detection.md#phase-6-implementation-results-2025-11-20) (real TDD example)

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
