# Task 011: Analysis & Classification Pipeline (Epic)

## Objective
Combine all components (scenes, OCR, transcription) to classify segments, detect team mentions, and calculate airtime.

## Prerequisites
- Task 010 (Transcription Epic) completed ✅
- Have scene, OCR, and transcription data for test video ✅

## Epic Overview
This is the most complex epic - split into 7 focused subtasks:

1. **[011a-reconnaissance.md](011a-reconnaissance.md)** ✅ - Analysis reconnaissance & pattern discovery (45-60 min)
   - Map data relationships between scenes, OCR, and transcript
   - Validate against ground truth (motd_visual_patterns.md)
   - Propose classification heuristics

2. **[011b-scene-detection-tuning.md](011b-scene-detection-tuning.md)** - Scene detection tuning (30-60 min)
   - Test lower PySceneDetect thresholds
   - Attempt to capture FT graphics (0/7 currently detected)
   - Decide: keep improved scenes OR proceed with current approach

3. **[011c-segment-classifier.md](011c-segment-classifier.md)** - Segment classifier implementation (2-2.5 hours)
   - Classify scenes: studio_intro / highlights / interviews / studio_analysis
   - Multi-signal approach (OCR + transcript + timing)
   - Target: >85% accuracy

4. **[011d-match-boundary-detector.md](011d-match-boundary-detector.md)** - Match boundary detection (1.5-2 hours)
   - Detect match boundaries and determine running order
   - Use OCR fixtures + team mentions + timing
   - Target: 100% running order accuracy (CRITICAL)

5. **[011e-airtime-calculator.md](011e-airtime-calculator.md)** - Airtime calculator (1-1.5 hours)
   - Calculate durations per segment type per match
   - Sum totals and validate ranges

6. **[011f-pipeline-orchestrator.md](011f-pipeline-orchestrator.md)** - Pipeline orchestrator & CLI (2-2.5 hours)
   - Wire all components together
   - Implement caching strategy
   - Create `process` CLI command

7. **[011g-validation.md](011g-validation.md)** - Execution & validation (2-3 hours)
   - Run full pipeline on test video
   - Validate running order (100% required)
   - Validate segment classification (>85% target)
   - Document final accuracy metrics

**Total Estimated Time**: 8.5-12 hours

### Future Enhancement: Theme Song Detection
Consider adding MOTD theme song detection as part of segment classification:
- Theme song occurs at predictable boundaries (start, between matches, end)
- Can use audio fingerprinting (dejavu, auditok) or simpler heuristics
- Helps identify transition points between segments
- Alternative: Detect silence periods (20+ seconds without speech)
- Output: `{"theme_song_timestamps": [0, 352, 1847, ...]}`

This can be added during subtask breakdown or deferred to Task 013 (Tuning).

## Key Deliverables

### Segment Classifier (`src/motd_analyzer/analysis/segment_classifier.py`)
- Classify each scene based on:
  - OCR results (teams present = likely highlights)
  - Transcript content (pundit names = likely analysis)
  - Visual patterns (could add face detection for interviews)
- Return classified scenes with confidence scores

### Team Mention Detector (`src/motd_analyzer/analysis/team_mention_detector.py`)
- Search transcript for team names
- Find first chronological mention in analysis segments
- Return team + timestamp + context snippet

### Airtime Calculator (`src/motd_analyzer/analysis/airtime_calculator.py`)
- Group scenes by match (using OCR team detection)
- Sum durations by segment type
- Calculate total airtime per match

### Pipeline Orchestrator (`src/motd_analyzer/pipeline/orchestrator.py`)
- Coordinate all stages
- Handle caching (don't re-run expensive steps)
- Merge results into final JSON output

## Full Pipeline Command
```bash
python -m motd_analyzer process data/videos/your_video.mp4 \
  --output data/output/analysis.json
```

## Success Criteria
- [x] 011a: Reconnaissance report complete with classification heuristics
- [ ] 011b: Scene detection tuning complete (FT graphics investigation)
- [ ] 011c: Segment classifier implemented and tested
- [ ] 011d: Match boundary detector implemented with 100% running order accuracy
- [ ] 011e: Airtime calculator implemented and validated
- [ ] 011f: Pipeline orchestrator working with CLI command
- [ ] 011g: Full validation complete with report
- [ ] Running order: 100% accurate (7/7 matches) - **CRITICAL**
- [ ] Segment classification: >85% accurate
- [ ] Team mentions detected correctly
- [ ] Airtime calculations accurate
- [ ] Final JSON matches PRD schema (section 3.4)
- [ ] Caching works correctly (re-run is instant)

## Estimated Time
8.5-12 hours (updated with new 011b subtask)

## Notes
- Start with simple heuristic rules for classification
- Can enhance with ML later if needed
- Caching is critical - don't re-run Whisper unnecessarily!

## Reference
See [roadmap.md Phase 4](../roadmap.md#phase-4-analysis--classification-est-8-10-hours) for implementation details.

## Next Task
[012-validation-tools-epic.md](012-validation-tools-epic.md)
