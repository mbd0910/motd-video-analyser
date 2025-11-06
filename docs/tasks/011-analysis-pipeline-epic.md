# Task 011: Analysis & Classification Pipeline (Epic)

## Objective
Combine all components (scenes, OCR, transcription) to classify segments, detect team mentions, and calculate airtime.

## Prerequisites
- [010-transcription-epic.md](010-transcription-epic.md) completed
- Have scene, OCR, and transcription data for test video

## Epic Overview
This is the most complex epic - definitely split into sub-tasks:
1. Implement segment classifier (studio/highlights/interview/analysis)
2. Implement team mention detector (find first team in analysis segments)
3. Implement airtime calculator (sum durations by match)
4. Create pipeline orchestrator (ties everything together)
5. Run end-to-end on test video
6. Validate full pipeline output

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
- [ ] Full pipeline runs end-to-end
- [ ] Running order is correct
- [ ] Segment classification >85% accurate
- [ ] Team mentions detected correctly
- [ ] Airtime calculations accurate
- [ ] Final JSON matches expected schema

## Estimated Time
4-6 hours

## Notes
- Start with simple heuristic rules for classification
- Can enhance with ML later if needed
- Caching is critical - don't re-run Whisper unnecessarily!

## Reference
See [roadmap.md Phase 4](../roadmap.md#phase-4-analysis--classification-est-8-10-hours) for implementation details.

## Next Task
[012-validation-tools-epic.md](012-validation-tools-epic.md)
