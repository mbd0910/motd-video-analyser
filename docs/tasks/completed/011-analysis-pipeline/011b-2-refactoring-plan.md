# Task 011b-2 Refactoring Plan: Architecture-First Approach

## Context

During TDD implementation for FT graphic detection, we discovered critical architecture issues that make testing painful and violate SOLID principles. This document outlines the refactoring plan to fix the underlying design before implementing bug fixes.

## Current Architecture Issues

### 1. God Function: `process_scene()` (243 lines, 13 responsibilities)

**Location:** `src/motd/__main__.py` lines 325-568

**Violations:**
- **Single Responsibility Principle**: Does 13 distinct things (OCR, team matching, validation, fixture lookup, scoring, etc.)
- **Function too long**: 243 lines (borderline "monumental smell")
- **7 parameters**: Massive coupling, hard to test

**Responsibilities (should be separate):**
1. Extract frame path from scene dict
2. Validate frame exists
3. Run OCR with fallback strategy
4. Combine OCR text
5. Filter OCR noise
6. Match teams via fuzzy matching
7. Infer opponent from fixtures
8. Validate fixture pairs
9. Search for alternative valid pairs
10. Validate FT graphics
11. Apply confidence boosts
12. Identify fixtures
13. Re-order teams by fixture order

### 2. Hardcoded File Paths in CLI Layer

**Location:** `src/motd/__main__.py` lines 658-666

**Issues:**
```python
team_matcher = TeamMatcher(Path('data/teams/premier_league_2025_26.json'))  # ❌ HARDCODED
fixture_matcher = FixtureMatcher(
    Path('data/fixtures/premier_league_2025_26.json'),  # ❌ HARDCODED
    Path('data/episodes/episode_manifest.json')         # ❌ HARDCODED
)
```

**Problems:**
- No separation between "what to load" (config) and "how to load" (initialization)
- Can't test without real JSON files
- Paths not in `config.yaml`

### 3. No Type Safety (Raw Dicts Everywhere)

**Issues:**
- Scene is `dict[str, Any]` - no validation
- Detection result is `dict[str, Any]` - no contract
- Team matches are dicts - no type safety
- Runtime errors possible

### 4. Test Fixture Explosion

**Symptom:**
```python
def test_process_scene(scene, ocr_reader, team_matcher, fixture_matcher, expected_teams, episode_id, logger):
    # 7 fixtures needed to test ONE function - code smell!
```

**Root Cause:** Architecture is broken, not a testing problem.

---

## Target Architecture

### Design Principles

1. **Single Responsibility**: Each class/function does ONE thing
2. **Dependency Inversion**: Depend on abstractions (inject dependencies)
3. **Type Safety**: Use Pydantic models for all data structures
4. **Testability**: Easy to mock dependencies, no file I/O in tests
5. **Configuration**: All paths in `config.yaml`, not code

### New File Structure

```
src/motd/
├── ocr/
│   ├── reader.py                  # OCRReader (existing)
│   ├── team_matcher.py            # TeamMatcher (existing)
│   ├── fixture_matcher.py         # FixtureMatcher (existing)
│   └── scene_processor.py         # 🆕 SceneProcessor class
├── pipeline/
│   ├── __init__.py                # 🆕 Pipeline package
│   ├── models.py                  # 🆕 Pydantic models
│   └── factory.py                 # 🆕 ServiceFactory
└── __main__.py                    # Refactor to use SceneProcessor + Factory
```

### Key Classes

#### 1. Pydantic Models (`src/motd/pipeline/models.py`)

**Purpose:** Type-safe data structures with validation

```python
from pydantic import BaseModel, Field
from pathlib import Path

class Scene(BaseModel):
    """Scene from PySceneDetect."""
    scene_number: int
    start_time: str
    start_seconds: float
    end_seconds: float
    duration: float
    frames: list[str] = Field(default_factory=list)
    key_frame_path: str | None = None

class TeamMatch(BaseModel):
    """Single team match result from fuzzy matching."""
    team: str
    confidence: float
    matched_text: str
    source: str  # 'ocr' or 'inferred_from_fixture'

class OCRResult(BaseModel):
    """OCR extraction result."""
    primary_source: str  # 'ft_score', 'scoreboard', 'formation'
    results: list[dict]
    confidence: float

class ProcessedScene(BaseModel):
    """Scene after OCR + team matching + validation."""
    scene_number: int
    start_time: str
    start_seconds: float
    frame_path: str
    ocr_source: str
    team1: str
    team2: str
    match_confidence: float
    fixture_id: str | None = None
```

**Benefits:**
- Runtime validation
- Clear contracts between layers
- Easy serialization/deserialization
- IDE autocomplete

#### 2. EpisodeContext (`src/motd/ocr/scene_processor.py`)

**Purpose:** Encapsulate episode-level state

```python
from dataclasses import dataclass

@dataclass
class EpisodeContext:
    """Context for processing scenes from a single episode."""
    episode_id: str
    expected_teams: list[str]
    expected_fixtures: list[dict]
```

**Benefits:**
- Reduces parameter count (1 object instead of 3 parameters)
- Clear ownership of episode data
- Easy to extend with more context

#### 3. SceneProcessor (`src/motd/ocr/scene_processor.py`)

**Purpose:** Process individual scenes (OCR → team matching → validation)

```python
class SceneProcessor:
    """Processes individual scenes: OCR → team matching → validation."""

    def __init__(
        self,
        ocr_reader: OCRReader,
        team_matcher: TeamMatcher,
        fixture_matcher: FixtureMatcher,
        context: EpisodeContext
    ):
        """Initialize with dependencies."""
        self.ocr_reader = ocr_reader
        self.team_matcher = team_matcher
        self.fixture_matcher = fixture_matcher
        self.context = context
        self.logger = logging.getLogger(__name__)

    def process(self, scene: Scene) -> ProcessedScene | None:
        """
        Process single scene.

        Returns:
            ProcessedScene if teams detected and validated, None otherwise
        """
        # Orchestrate pipeline
        frame = self._extract_frame(scene)
        if not frame:
            return None

        ocr_result = self._run_ocr(frame)
        if not ocr_result:
            return None

        teams = self._match_teams(ocr_result)
        if not teams:
            return None

        validated = self._validate_fixture(teams, ocr_result)
        if not validated:
            return None

        return ProcessedScene(
            scene_number=scene.scene_number,
            start_time=scene.start_time,
            start_seconds=scene.start_seconds,
            frame_path=str(frame),
            ocr_source=ocr_result.primary_source,
            team1=validated['team1'],
            team2=validated['team2'],
            match_confidence=validated['confidence'],
            fixture_id=validated.get('fixture_id')
        )

    def _extract_frame(self, scene: Scene) -> Path | None:
        """Extract first valid frame path from scene."""
        # Single responsibility
        ...

    def _run_ocr(self, frame: Path) -> OCRResult | None:
        """Run OCR with fallback strategy (FT score → scoreboard)."""
        # Single responsibility
        ...

    def _match_teams(self, ocr_result: OCRResult) -> list[TeamMatch]:
        """Match teams from OCR text using fuzzy matching."""
        # Single responsibility
        ...

    def _infer_opponent(self, detected_team: TeamMatch) -> TeamMatch | None:
        """Infer opponent from fixtures if only 1 team detected."""
        # Single responsibility - contains bug fix
        ...

    def _validate_ft_graphic(self, ocr_result: OCRResult, teams: list[TeamMatch]) -> bool:
        """Validate that OCR result is from genuine FT graphic."""
        # Single responsibility
        ...

    def _validate_fixture(self, teams: list[TeamMatch], ocr_result: OCRResult) -> dict | None:
        """Validate team pair against fixtures."""
        # Single responsibility
        ...
```

**Benefits:**
- **Single Responsibility**: Each method does ONE thing
- **Dependency Injection**: All dependencies passed at init
- **Testability**: Easy to mock OCRReader, TeamMatcher, FixtureMatcher
- **Logging**: Class-level logger, not parameter
- **Clear Flow**: `process()` orchestrates private methods
- **Type Safety**: Uses Pydantic models

#### 4. ServiceFactory (`src/motd/pipeline/factory.py`)

**Purpose:** Centralized service initialization (paths in config, not code)

```python
class ServiceFactory:
    """Factory for creating pipeline services from configuration."""

    def __init__(self, config: dict):
        """Initialize with configuration dict."""
        self.config = config

    def create_ocr_reader(self) -> OCRReader:
        """Create OCRReader from config."""
        return OCRReader(self.config['ocr'])

    def create_team_matcher(self) -> TeamMatcher:
        """Create TeamMatcher from config."""
        teams_path = Path(self.config['teams']['path'])
        return TeamMatcher(teams_path)

    def create_fixture_matcher(self) -> FixtureMatcher:
        """Create FixtureMatcher from config."""
        fixtures_path = Path(self.config['fixtures']['path'])
        manifest_path = Path(self.config['episodes']['manifest_path'])
        return FixtureMatcher(fixtures_path, manifest_path)

    def create_scene_processor(self, episode_id: str) -> SceneProcessor:
        """Create fully-initialized SceneProcessor for episode."""
        fixture_matcher = self.create_fixture_matcher()

        context = EpisodeContext(
            episode_id=episode_id,
            expected_teams=fixture_matcher.get_expected_teams(episode_id),
            expected_fixtures=fixture_matcher.get_expected_fixtures(episode_id)
        )

        return SceneProcessor(
            ocr_reader=self.create_ocr_reader(),
            team_matcher=self.create_team_matcher(),
            fixture_matcher=fixture_matcher,
            context=context
        )
```

**Benefits:**
- **Configuration**: Paths in `config.yaml`, not hardcoded
- **Single Source of Truth**: One place to initialize services
- **Testability**: Easy to inject mock factory in tests
- **Separation of Concerns**: "What to load" (config) vs "how to load" (factory)

### Updated Config (`config/config.yaml`)

**Add new sections:**

```yaml
teams:
  path: data/teams/premier_league_2025_26.json

fixtures:
  path: data/fixtures/premier_league_2025_26.json

episodes:
  manifest_path: data/episodes/episode_manifest.json
```

### Updated CLI (`src/motd/__main__.py`)

**Before (lines 623-768):**
```python
@cli.command("extract-teams")
def extract_teams_command(scenes, episode_id, output, config):
    # 145 lines of orchestration logic
    # Hardcoded paths
    # Mixed concerns
    ...
```

**After:**
```python
@cli.command("extract-teams")
def extract_teams_command(scenes, episode_id, output, config):
    """Extract teams from scenes."""
    # Load config
    cfg = load_config(config)

    # Create factory
    factory = ServiceFactory(cfg)

    # Create scene processor
    processor = factory.create_scene_processor(episode_id)

    # Load scenes
    with open(scenes, 'r') as f:
        scenes_data = json.load(f)

    # Process scenes
    results = []
    for scene_dict in scenes_data['scenes']:
        scene = Scene(**scene_dict)  # Pydantic validation
        result = processor.process(scene)
        if result:
            results.append(result)

    # Save output
    output_dict = {
        'episode_id': episode_id,
        'ocr_results': [r.dict() for r in results],
        'summary': {...}
    }

    with open(output, 'w') as f:
        json.dump(output_dict, f, indent=2)
```

**Benefits:**
- **Thin CLI layer**: Just wiring, no business logic
- **Clear flow**: Load → Create → Process → Save
- **Type safety**: Pydantic validation on load
- **Testable**: Can test `SceneProcessor` without Click

---

## Refactoring Checklist

### Phase 1: Documentation ✅
- [x] Create this refactoring plan document
- [ ] Get user approval on target architecture

### Phase 2: Add Pydantic Models
- [ ] Create `src/motd/pipeline/__init__.py`
- [ ] Create `src/motd/pipeline/models.py`
- [ ] Define `Scene` model
- [ ] Define `TeamMatch` model
- [ ] Define `OCRResult` model
- [ ] Define `ProcessedScene` model
- [ ] Write model tests (`tests/unit/pipeline/test_models.py`)
- [ ] Commit: "feat(pipeline): Add Pydantic models for type safety"

### Phase 3: Extract SceneProcessor Class
- [ ] Create `src/motd/ocr/scene_processor.py`
- [ ] Define `EpisodeContext` dataclass
- [ ] Define `SceneProcessor` class
- [ ] Add `__init__()` method
- [ ] Add `process()` orchestration method
- [ ] Extract `_extract_frame()` method
- [ ] Extract `_run_ocr()` method
- [ ] Extract `_match_teams()` method
- [ ] Extract `_infer_opponent()` method (with bug fix)
- [ ] Extract `_validate_ft_graphic()` method
- [ ] Extract `_validate_fixture()` method
- [ ] Add comprehensive DEBUG logging
- [ ] Update `process_scene()` in `__main__.py` to delegate to `SceneProcessor`
- [ ] Run existing unit tests - ensure no regressions
- [ ] Commit: "refactor(ocr): Extract SceneProcessor class from process_scene()"

### Phase 4: Create ServiceFactory
- [ ] Add `teams.path` to `config/config.yaml`
- [ ] Add `fixtures.path` to `config/config.yaml`
- [ ] Add `episodes.manifest_path` to `config/config.yaml`
- [ ] Create `src/motd/pipeline/factory.py`
- [ ] Define `ServiceFactory` class
- [ ] Add `create_ocr_reader()` method
- [ ] Add `create_team_matcher()` method
- [ ] Add `create_fixture_matcher()` method
- [ ] Add `create_scene_processor()` method
- [ ] Update `extract_teams_command()` to use factory
- [ ] Remove hardcoded paths from `__main__.py`
- [ ] Run existing unit tests
- [ ] Commit: "refactor(pipeline): Add ServiceFactory for centralized initialization"

### Phase 5: Fix Known Bugs
- [ ] Fix opponent inference bug in `SceneProcessor._infer_opponent()`:
  - Change `episode_data.get('fixtures', [])` → `episode_data.get('expected_matches', [])`
- [ ] Fix validation timing:
  - Ensure opponent inference happens BEFORE FT validation
  - Reorder logic in `process()` method
- [ ] Add comprehensive DEBUG logging at every decision point
- [ ] Run existing unit tests
- [ ] Commit: "fix(ocr): Fix opponent inference bug and validation timing"

### Phase 6: Write Tests
- [ ] Create `tests/unit/ocr/test_scene_processor.py`
- [ ] Write unit tests with mocked dependencies:
  - `test_process_ft_graphic_with_both_teams_detected()`
  - `test_process_ft_graphic_with_opponent_inference()`
  - `test_process_ft_graphic_with_fixture_validation()`
  - `test_reject_invalid_ft_graphic()`
- [ ] Create `tests/integration/test_ft_graphic_detection_refactored.py`
- [ ] Write integration test for 8 ground truth FT frames:
  - Use `ServiceFactory` to create `SceneProcessor`
  - Parametrize test with 8 ground truth frames
  - Assert all 8 detected (not None)
  - Assert correct teams matched
- [ ] Commit: "test(ocr): Add unit/integration tests for FT graphic detection"

### Phase 7: Debug Failing Frames
- [ ] Run integration tests → identify failing frames
- [ ] For each failing frame:
  - [ ] Run test with DEBUG logging
  - [ ] Generate annotated image (OCR regions overlaid)
  - [ ] Show user for visual validation
  - [ ] Identify root cause
  - [ ] Implement targeted fix
  - [ ] Re-run ALL tests
  - [ ] Commit fix
- [ ] Achieve 100% FT detection rate (8/8 frames)
- [ ] Commit: "fix(ocr): Achieve 100% FT detection rate for ground truth frames"

### Phase 8: Final Validation
- [ ] Re-run full pipeline: `python -m motd extract-teams ...`
- [ ] Verify `ocr_results.json` contains 8 FT graphic detections
- [ ] User spot-check 3 random frames
- [ ] Update Task 011b-2 main file with completion status
- [ ] Commit: "docs: Update Task 011b-2 - 100% FT detection achieved"

---

## Acceptance Criteria

### Must Have (Non-Negotiable)
1. ✅ All 8 ground truth FT frames detected correctly
2. ✅ No regressions on existing unit tests
3. ✅ `SceneProcessor` class with <100 lines per method
4. ✅ Paths in `config.yaml`, not hardcoded
5. ✅ Pydantic models for type safety
6. ✅ Comprehensive DEBUG logging at all decision points
7. ✅ Integration tests for 8 FT frames

### Nice to Have (If Time Permits)
- Clean separation between CLI and business logic
- Further refactoring of `extract_teams_command()` orchestration
- Extract `TeamExtractionOrchestrator` class
- Add more unit tests for edge cases

---

## Success Metrics

- **FT Detection Rate**: 100% (8/8 ground truth frames)
- **Test Coverage**: >80% for `SceneProcessor` class
- **Code Quality**: All methods <100 lines, SRP followed
- **Maintainability**: Can add new validation rules without modifying `SceneProcessor.process()`
- **Testability**: Can mock all dependencies in tests

---

## Timeline

**Total Estimate: 10-13 hours**

- Phase 1: Documentation (30 mins) ✅
- Phase 2: Pydantic models (1 hour)
- Phase 3: SceneProcessor (2-3 hours)
- Phase 4: ServiceFactory (1 hour)
- Phase 5: Bug fixes (1-2 hours)
- Phase 6: Tests (2 hours)
- Phase 7: Debug frames (2-3 hours)
- Phase 8: Validation (30 mins)

---

## Notes

- **Not TDD**: We're refactoring first, tests after (pragmatic approach)
- **Incremental commits**: Small, focused commits after each phase
- **No breaking changes to CLI**: Commands stay the same, internals change
- **Backward compatibility**: Keep old `process_scene()` temporarily as wrapper
