# Code Quality Checklist

## Readability

### Naming
- [ ] Variables and functions have clear, descriptive names
- [ ] Names follow Python conventions (snake_case for functions/variables, PascalCase for classes)
- [ ] Boolean variables start with is/has/can/should
- [ ] No single-letter variables (except loop counters: i, j, k)
- [ ] Constants use UPPER_SNAKE_CASE

### Code Organization
- [ ] Functions are focused (single responsibility)
- [ ] Functions are reasonably sized (< 50 lines ideal, < 200 maximum)
- [ ] Related code is grouped together
- [ ] Imports are organized (stdlib, third-party, local)

### Comments & Docstrings
- [ ] Public functions/classes have docstrings (Google style)
- [ ] Complex logic has explanatory comments
- [ ] Comments explain "why", not "what"
- [ ] No commented-out code (use git history instead)
- [ ] TODOs include context and owner
- [ ] British spelling in prose/comments, US spelling in code identifiers acceptable

## Code Quality

### DRY (Don't Repeat Yourself)
- [ ] No duplicated logic (extract to functions/utilities)
- [ ] Repeated patterns extracted to reusable components
- [ ] Constants defined once and reused

### Error Handling
- [ ] Specific exceptions used (not bare `except:`)
- [ ] Errors logged with context (episode_id, file paths, stage name)
- [ ] User-facing errors have helpful messages
- [ ] Edge cases are handled
- [ ] Validation happens before operations
- [ ] Critical failures don't silently pass

### Python Type Hints
- [ ] Type hints present for all public functions
- [ ] No bare `Any` types (use specific types)
- [ ] Optional used for nullable values
- [ ] Return types specified
- [ ] Complex data structures use TypedDict or Pydantic models

## Security

### Input Validation
- [ ] File paths validated before use (Path.exists(), absolute vs relative)
- [ ] Config values validated at load time
- [ ] Episode IDs/identifiers sanitized (no command injection risk)

### Data Handling
- [ ] Sensitive data not logged (if any)
- [ ] Environment variables used for secrets (if needed)
- [ ] No hardcoded credentials or API keys

## Performance

### Python Performance
- [ ] List comprehensions used over verbose loops (where appropriate)
- [ ] Generators used for large data streams (not loading everything into memory)
- [ ] pathlib.Path used instead of os.path
- [ ] f-strings used for string formatting (not .format() or %)
- [ ] No premature optimisation (keep code readable first)

### Caching & I/O
- [ ] Expensive operations cached (Whisper transcription, scene detection)
- [ ] Cache invalidation logic correct (config changes trigger re-run)
- [ ] File I/O minimized (don't reload config in every function)
- [ ] Batch operations used where appropriate
- [ ] Context managers (with) used for file/resource handling

## Git Practices

### Commits
- [ ] Commits are focused and atomic
- [ ] Commit messages are descriptive
- [ ] No unnecessary files committed
- [ ] No large binary files

### Code Changes
- [ ] Changes align with feature requirements
- [ ] No unrelated changes included
- [ ] Debugging code removed
- [ ] print() statements removed (or replaced with proper logging)

## ML Pipeline Specific

### Resource Management
- [ ] ML models loaded once and reused (not reloaded in loops)
- [ ] GPU configuration appropriate (check torch.cuda.is_available() or mps)
- [ ] faster-whisper used instead of openai-whisper (4x speed improvement)
- [ ] Memory-intensive operations use generators when possible

### Pipeline Patterns
- [ ] Pipeline stages independent (orchestrator coordinates, stages don't call each other)
- [ ] Graceful degradation (one match failing doesn't block entire episode)
- [ ] Confidence thresholds applied (>0.9 accept, 0.7-0.9 log, <0.7 flag)
- [ ] Config-driven behaviour (thresholds, paths, models from config.yaml)

### Caching Strategy (Critical)
- [ ] Never re-run Whisper if cached transcript exists with matching config
- [ ] Cache version includes config hash (invalidates on config change)
- [ ] Expensive operations (scene detection, OCR, transcription) cached
- [ ] Cache files include metadata (processed_at, config snapshot)
