# Issue #9: CI/CD with GitHub Actions + OCR Module Refactoring

**GitHub Issue:** [#9 - CI/CD run unit tests via GitHub actions](https://github.com/mbd0910/motd-video-analyser/issues/9)

## Overview

Set up GitHub Actions CI to run tests on PRs and pushes to main. Includes refactoring OCR module to separate pure business logic from ML dependencies for cleaner architecture.

**Key deliverables:**
1. GitHub Actions workflow running all tests
2. `GraphicValidator` class extracted from `OCRReader` (no ML dependencies)
3. Unit tests refactored to use `GraphicValidator` directly

---

## Critical Thinking Phase

### Problem Analysis
The original issue requested CI/CD for unit tests. During planning, we identified:
- Tests currently load heavy ML dependencies (torch ~2GB, easyocr) even for pure logic tests
- `OCRReader` mixes business logic (validation) with ML inference (EasyOCR)
- This violates separation of concerns and makes tests slower than necessary

### Decision: Refactor as Part of CI Setup
Rather than just setting up CI with heavy dependencies, we chose to:
1. Extract validation logic into `GraphicValidator` (no ML deps)
2. Keep `OCRReader` as ML inference wrapper
3. Refactor unit tests to use `GraphicValidator` directly

**Benefits:**
- Cleaner architecture (single responsibility)
- Option for fast local unit tests (~10s vs ~80s)
- CI runs all tests with full coverage

### Alternatives Considered
1. **Just install everything in CI** - Simpler but doesn't fix architectural issue
2. **Two separate CI jobs** - More complex to maintain
3. **Unit tests only in CI** - Misses integration test coverage

**Chosen:** Single CI job with all tests + refactored architecture

---

## Phase 0: Setup

- [x] Create feature branch `feature/issue-009-ci-cd`
- [x] Create task file
- [x] Link task file to GitHub issue

---

## Phase 1: Extract Validation Logic

### Create `src/motd/ocr/validators.py`

- [x] Create `GraphicValidator` class with:
  - `__init__(self, team_codes: Set[str])`
  - `from_teams_file(cls, teams_path: Path)` factory method
  - `validate_ft_graphic()`
  - `validate_scoreboard()`
  - `looks_like_ft_content()`
  - `_load_team_codes()` static method

### Update `src/motd/ocr/reader.py`

- [x] Accept optional `validator: GraphicValidator` in `__init__`
- [x] Delegate validation methods to validator
- [x] Maintain backward compatibility

### Update supporting files

- [x] `src/motd/pipeline/factory.py` - add `create_graphic_validator()`
- [x] `src/motd/ocr/__init__.py` - export `GraphicValidator`

---

## Phase 2: Refactor Unit Tests

- [x] Create `tests/conftest.py` with pytest markers
- [x] Update `tests/unit/ocr/test_ft_validation.py`
- [x] Update `tests/unit/ocr/test_scoreboard_validation.py`
- [x] Update `tests/unit/ocr/test_ft_content_detection.py`
- [x] Verify integration tests still work unchanged

---

## Phase 3: Dependencies

- [x] Add `pydantic==2.10.3` to `pyproject.toml`
- [x] Add `rapidfuzz==3.11.0` to `pyproject.toml`
- [x] Add `[tool.pytest.ini_options]` section

---

## Phase 4: GitHub Actions

- [x] Create `.github/workflows/ci.yml`
- [x] Trigger on: push to main, PRs targeting main
- [x] Python 3.12, pip caching, run all tests

---

## Phase 5: Verification

- [x] All 206 tests pass (2 xfailed as expected)
- [ ] CI workflow passes on GitHub (will test with PR)
- [x] `validators.py` has zero ML imports

---

## Notes & Decisions

*Architectural decisions recorded during implementation*
