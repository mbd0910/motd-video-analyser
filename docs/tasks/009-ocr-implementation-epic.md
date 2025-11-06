# Task 009: OCR & Team Detection (Epic)

## Objective
Implement OCR to extract team names from video frames and match them against your team list.

## Prerequisites
- [008-scene-detection-testing.md](008-scene-detection-testing.md) completed
- Key frames extracted from test video

## Epic Overview
This is a larger epic that you should consider splitting into sub-tasks:
1. Implement OCR reader module (EasyOCR integration)
2. Implement team matcher (fuzzy matching against team list)
3. Create OCR CLI command
4. Run on test video frames
5. Validate team detection accuracy
6. Tune OCR regions if needed

## Key Deliverables

### OCR Reader (`src/motd_analyzer/ocr/reader.py`)
- Integrate EasyOCR
- Define regions of interest (top-left scoreboard, bottom-right formation graphic)
- Extract text from cropped frame regions

### Team Matcher (`src/motd_analyzer/ocr/team_matcher.py`)
- Load team names from JSON
- Fuzzy match OCR text against team variations
- Return matched teams with confidence scores

### CLI Command
```bash
python -m motd_analyzer extract-teams \
  --scenes data/cache/test/scenes.json \
  --output data/cache/test/teams.json
```

## Success Criteria
- [ ] OCR runs on all frames without errors
- [ ] Team detection accuracy >90% on frames with visible scoreboards
- [ ] False positives are minimal
- [ ] Team name variations matched correctly

## Estimated Time
3-4 hours

## Notes
- EasyOCR will download models (~100MB) on first run
- If accuracy is poor, you may need to:
  - Adjust OCR regions in config.yaml
  - Add more team name alternates
  - Consider PaddleOCR (see [tech-tradeoffs.md](../tech-tradeoffs.md))

## Reference
See [roadmap.md Phase 2](../roadmap.md#phase-2-ocr--team-detection-est-6-8-hours) for detailed code examples.

## Next Task
[010-transcription-epic.md](010-transcription-epic.md)
