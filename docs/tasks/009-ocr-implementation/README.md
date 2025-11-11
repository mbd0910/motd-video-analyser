# Task 009: OCR & Team Detection with Fixture Matching (Epic)

## Objective
Implement fixture-aware OCR to extract team names from video frames and validate them against expected fixtures.

## Prerequisites
- Task 008 completed (scene detection + 810 frames extracted from test video)
- Test data: `data/cache/motd_2025-26_2025-11-01/scenes.json` and frames
- Fixtures: `data/fixtures/premier_league_2025_26.json` (7 matches for 2025-11-01)
- Teams: `data/teams/premier_league_2025_26.json` (20 PL teams)

## Epic Subtasks

This epic is split into 7 subtasks:

- [ ] **[009a: Visual Pattern Reconnaissance](009a-visual-pattern-reconnaissance.md)** (1-1.5 hours)
  - Document MOTD visual patterns by browsing test video and frames
  - Create episode manifest linking episode to expected fixtures
  - Identify formation graphics, scoreboards, intro/outro timecodes
  - Output: `docs/motd_visual_patterns.md` + `data/episodes/episode_manifest.json`

- [ ] **[009b: Implement OCR Reader](009b-implement-ocr-reader.md)** (1-1.5 hours)
  - Create OCR reader module with EasyOCR
  - Extract text from scoreboard and formation graphic regions
  - Test on sample frames from 009a
  - Output: `src/motd/ocr/reader.py`

- [ ] **[009c: Implement Team Matcher](009c-implement-team-matcher.md)** (1-1.5 hours)
  - Create fuzzy matching for team names (handles abbreviations, OCR errors)
  - Support fixture-aware matching (candidate teams from fixtures)
  - Handle multiple teams in text ("Brighton 2-0 Leeds")
  - Output: `src/motd/ocr/team_matcher.py`

- [ ] **[009d: Implement Fixture Matcher](009d-implement-fixture-matcher.md)** (1 hour)
  - Load fixtures and episode manifest
  - Validate OCR results against expected fixtures
  - Boost confidence when fixture validates OCR
  - Flag unexpected teams
  - Output: `src/motd/ocr/fixture_matcher.py`

- [ ] **[009e: Create OCR CLI Command](009e-create-ocr-cli.md)** (1 hour)
  - Add `extract-teams` command to CLI
  - Implement smart scene filtering (skip intro, transitions, studio)
  - Wire up OCR → team matcher → fixture matcher pipeline
  - Output structured JSON with results
  - Output: Updated `src/motd/__main__.py`

- [ ] **[009f: Run OCR on Test Video](009f-run-ocr-on-test-video.md)** (30-45 min + processing)
  - Execute CLI command on test video
  - Process filtered scenes (~100-300 of 810)
  - Collect OCR results
  - Output: `data/cache/motd_2025-26_2025-11-01/ocr_results.json`

- [ ] **[009g: Validate and Tune](009g-validate-and-tune.md)** (1-1.5 hours + tuning if needed)
  - Manual validation against 7 expected fixtures
  - Calculate accuracy metrics (target: >95%)
  - Analyze failure patterns
  - Tune if needed: regions, thresholds, multi-frame extraction
  - Output: Validation documentation with final accuracy

## Key Deliverables

### OCR Reader (`src/motd_analyzer/ocr/reader.py`)
- Integrate EasyOCR
- Define regions of interest (top-left scoreboard, bottom-right formation graphic)
- Extract text from cropped frame regions

### Team Matcher (`src/motd_analyzer/ocr/team_matcher.py`)
- Load team names from JSON
- Fuzzy match OCR text against team variations
- Accept optional candidate_teams list (from fixtures) to limit search space
- Return matched teams with confidence scores

### Fixture Matcher (`src/motd_analyzer/ocr/fixture_matcher.py`)
- Load fixture and episode manifest data
- Get expected fixtures for given episode
- Match OCR-detected teams to expected fixtures
- Boost confidence when fixture validates OCR results
- Flag unexpected teams

### CLI Command
```bash
python -m motd_analyzer extract-teams \
  --scenes data/cache/test/scenes.json \
  --teams data/teams/premier_league_2025_26.json \
  --fixtures data/fixtures/premier_league_2025_26.json \
  --manifest data/episodes/episode_manifest.json \
  --episode-id motd-2025-08-17 \
  --output data/cache/test/ocr_results.json
```

## Success Criteria
- [ ] OCR runs on all frames without errors
- [ ] Team detection accuracy >95% on frames with visible scoreboards (fixture-aware matching)
- [ ] If accuracy is 90-95%: Document whether multi-frame extraction was considered (see Notes below)
- [ ] If accuracy is <90%: Multi-frame extraction evaluated and decision documented
- [ ] Fixture matching correctly identifies expected matches
- [ ] No unexpected teams detected (all teams from expected fixtures)
- [ ] False positives are minimal
- [ ] Team name variations matched correctly

## Estimated Time
7-9 hours total (revised from original 4-5 hours):
- 009a: 1-1.5 hours (reconnaissance + episode manifest)
- 009b: 1-1.5 hours (OCR reader)
- 009c: 1-1.5 hours (team matcher)
- 009d: 1 hour (fixture matcher)
- 009e: 1 hour (CLI command)
- 009f: 30-45 min + 10-30 min processing
- 009g: 1-1.5 hours + tuning if needed

**Key learnings from Task 008:**
- 810 scenes detected (vs expected 40-80) due to low threshold for capturing walkouts
- Smart filtering needed to reduce processing load
- Formation graphics during walkouts are high-priority OCR targets

## Notes

### Fixture-Aware Matching Benefits
- **Fixture-aware matching reduces search space**: Instead of searching all 20 PL teams, OCR searches only ~12-16 teams from expected fixtures (6-8 matches)
- **Accuracy boost**: Fixture context provides 5-10% accuracy improvement over OCR-only approach

### Multi-Frame Extraction Strategy
**When to use**: If OCR accuracy is <90% after fixture-aware matching is implemented.

**How it works**: The frame extractor (Task 007) supports extracting 1-3 frames per scene via the `num_frames` parameter. This helps when:
- Scoreboard appears mid-scene rather than at scene start
- OCR fails on one frame due to motion blur but succeeds on another
- You want higher confidence through consensus across multiple frames

**Decision framework**:
- **Accuracy >95%**: Stay with single frame (default)
- **Accuracy 90-95%**: Evaluate cost/benefit - multi-frame adds 2-3x processing time
- **Accuracy <90%**: Try `num_frames=2` or `num_frames=3` before considering alternative OCR engines

**Implementation**: If enabling multi-frame, you'll need to:
1. Update CLI to pass `num_frames` parameter to frame extractor
2. Modify OCR reader to handle multiple frames per scene (consensus logic)
3. Update caching to handle multiple frame files per scene

**Reference**: See Task 007 lines 107-146 for `extract_multiple_frames_per_scene()` implementation.

### Other Tuning Options
- EasyOCR will download models (~100MB) on first run
- If accuracy remains poor after multi-frame evaluation:
  - Adjust OCR regions in config.yaml
  - Add more team name alternates
  - Verify fixture data matches episode date
  - Consider PaddleOCR (see [tech-tradeoffs.md](../tech-tradeoffs.md))

## Reference
See [roadmap.md Phase 2](../roadmap.md#phase-2-ocr--team-detection-est-6-8-hours) for detailed code examples.

## Next Task
[010-transcription-epic.md](010-transcription-epic.md)
