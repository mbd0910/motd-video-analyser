# Task 009: OCR & Team Detection with Fixture Matching (Epic)

## Objective
Implement fixture-aware OCR to extract team names from video frames and validate them against expected fixtures.

## Prerequisites
- [008-scene-detection-testing.md](008-scene-detection-testing.md) completed
- Key frames extracted from test video

## Epic Overview
This is a larger epic that you should consider splitting into sub-tasks:
1. Implement OCR reader module (EasyOCR integration)
2. Implement team matcher (fuzzy matching against team list, fixture-aware)
3. Implement fixture matcher (validate OCR against expected fixtures)
4. Create OCR CLI command with fixture support
5. Run on test video frames
6. Validate team detection accuracy (target: >95% with fixtures)
7. **If accuracy <90%**: Evaluate multi-frame extraction strategy (see Notes below)
8. Tune OCR regions if needed

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
4-5 hours (includes fixture matcher implementation)

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
