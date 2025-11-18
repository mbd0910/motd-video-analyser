# Task 011c: Segment Classifier Implementation

## Quick Context

**Parent Task:** [011-analysis-pipeline](README.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Scene](../../domain/README.md#scene), [OCR Scoreboard](../../domain/README.md#scoreboard)
**Business Rules:** [Segment Classification Hierarchy](../../domain/business_rules.md#rule-5-segment-classification-hierarchy)

**Why This Matters:** Segment classification enables answering the core research question: "Do some teams get more analysis than others?" Total airtime alone isn't sufficient - we need to distinguish between highlights (match footage) and studio analysis (pundit discussion) to measure quality of coverage, not just quantity.

**Key Insight:** Each match typically has all 4 segment types in sequence:
1. Studio intro (7-11s) - Preview
2. Highlights (5-10min) - Match footage
3. Interviews (45-90s) - Player/manager quotes
4. Studio analysis (2-5min) - Pundit discussion

Duration varies by match importance - "big six" matches get longer analysis, lower-table matches get minimal studio time.

See [Visual Patterns](../../domain/visual_patterns.md) for detailed episode structure and timing examples.

---

## Objective
Implement a robust multi-signal classifier to categorize each scene into one of 4 segment types: `studio_intro`, `highlights`, `interviews`, `studio_analysis`.

## Prerequisites
- [x] Task 011a complete (reconnaissance report with classification rules)
- [x] Have cached data and understand patterns

## Estimated Time
2-2.5 hours

## Target Accuracy
>85% segment classification accuracy (validated in 011f)

## Segment Types

### 1. `studio_intro`
Match introduction from studio before highlights
- **Duration**: 7-11 seconds typically
- **Signals**: Short duration + team mentions + before highlights

### 2. `highlights`
Match footage with goals and key moments
- **Duration**: 5-10 minutes typically
- **Signals**: Scoreboard OCR + FT graphic at end

### 3. `interviews`
Player/manager interviews after match
- **Duration**: 45-90 seconds typically
- **Signals**: After FT graphic + interview keywords + before studio analysis

### 4. `studio_analysis`
Post-match pundit discussion
- **Duration**: 2-5 minutes typically
- **Signals**: After interviews + transition keywords + team discussion

## Implementation Steps

### 1. Create Module Structure
- [ ] Create `src/motd/analysis/` directory
- [ ] Create `src/motd/analysis/__init__.py`
- [ ] Create `src/motd/analysis/segment_classifier.py`

### 2. Implement SegmentClassifier Class

```python
class SegmentClassifier:
    """Classifies video scenes into segment types using multi-signal approach."""

    def __init__(
        self,
        scenes: List[Dict],
        ocr_results: List[Dict],
        transcript: Dict,
        config: Optional[Dict] = None
    ):
        """
        Args:
            scenes: Scene detection results
            ocr_results: OCR detection results
            transcript: Transcription results
            config: Optional classification thresholds
        """
        pass

    def classify_scenes(self) -> List[Dict]:
        """
        Classify all scenes with segment types.

        Returns:
            List of scenes with added fields:
            - segment_type: str (studio_intro/highlights/interviews/studio_analysis)
            - confidence: float (0-1)
            - classification_signals: List[str] (which rules triggered)
        """
        pass

    def _has_scoreboard_ocr(self, scene_id: int) -> bool:
        """Check if scene has scoreboard OCR detection."""
        pass

    def _has_ft_graphic(self, scene_id: int) -> bool:
        """Check if scene has Full Time graphic."""
        pass

    def _get_transcript_for_scene(self, scene: Dict) -> List[Dict]:
        """Get transcript segments overlapping with scene timespan."""
        pass

    def _has_team_mention(self, transcript_segments: List[Dict]) -> bool:
        """Check if transcript mentions team names."""
        pass

    def _has_transition_words(self, transcript_segments: List[Dict]) -> bool:
        """Check for transition keywords (Alright, Right, Moving on)."""
        pass

    def _has_interview_keywords(self, transcript_segments: List[Dict]) -> bool:
        """Check for interview keywords (speak to, join us, after the game)."""
        pass
```

### 3. Implement Classification Rules (Priority Order)

- [ ] **Rule 1: FT Graphic Detection**
  - If scene has FT graphic in OCR → Mark as end of highlights
  - Next scene starts interviews
  - Confidence: 0.95

- [ ] **Rule 2: Scoreboard Detection**
  - If scene has scoreboard OCR + no FT → Highlights
  - Confidence: 0.90

- [ ] **Rule 3: Post-Highlights Pattern**
  - If scene follows FT graphic + before studio transition → Interviews
  - Check for interview keywords (boost confidence)
  - Confidence: 0.85

- [ ] **Rule 4: Short Scene with Team Mentions**
  - If scene duration 7-11 seconds + team mention + before highlights → Studio Intro
  - Confidence: 0.80

- [ ] **Rule 5: Post-Interview Analysis**
  - If scene after interviews + transition keywords → Studio Analysis
  - Check for team discussion
  - Confidence: 0.80

- [ ] **Rule 6: Default Classification**
  - Remaining scenes → Studio (generic)
  - Confidence: 0.50 (low confidence, needs refinement)

### 4. Implement Confidence Scoring

- [ ] Base confidence from rule match
- [ ] Boost confidence if multiple signals agree:
  - +0.05 for each additional signal
  - Cap at 0.95
- [ ] Reduce confidence for conflicting signals:
  - -0.10 for each contradiction
  - Floor at 0.30

### 5. Add Configuration Support

- [ ] Create default config in `config/config.yaml`:
  ```yaml
  segment_classification:
    studio_intro:
      min_duration_seconds: 5
      max_duration_seconds: 15
      keywords: ["let's look at", "coming up", "now", "next"]

    highlights:
      min_duration_seconds: 120  # 2 minutes
      max_duration_seconds: 900  # 15 minutes

    interviews:
      min_duration_seconds: 30
      max_duration_seconds: 180  # 3 minutes
      keywords: ["speak to", "join us", "after the game", "thoughts on"]

    studio_analysis:
      min_duration_seconds: 60
      max_duration_seconds: 600  # 10 minutes
      transition_keywords: ["alright", "right", "moving on", "what did you make"]
  ```

### 6. Implement Unit Tests

- [ ] Create `tests/unit/analysis/test_segment_classifier.py`
- [ ] Test FT graphic detection
- [ ] Test scoreboard detection
- [ ] Test team mention detection
- [ ] Test transition word detection
- [ ] Test interview keyword detection
- [ ] Test confidence scoring
- [ ] Test full classification on sample data

Sample test structure:
```python
def test_ft_graphic_ends_highlights():
    """Scene with FT graphic should be classified as end of highlights."""
    scenes = [{"id": 220, "duration": 2.5, ...}]
    ocr_results = [{"scene_id": 220, "ft_graphic": True, ...}]

    classifier = SegmentClassifier(scenes, ocr_results, {})
    classified = classifier.classify_scenes()

    assert classified[0]["segment_type"] == "highlights"
    assert classified[0]["confidence"] > 0.9
```

### 7. Add Logging

- [ ] Log classification decisions at INFO level
- [ ] Log low-confidence classifications (<0.6) at WARNING level
- [ ] Log rule applications at DEBUG level
- [ ] Example:
  ```python
  logger.info(f"Scene {scene_id}: Classified as {segment_type} (confidence: {confidence:.2f})")
  logger.warning(f"Scene {scene_id}: Low confidence classification ({confidence:.2f})")
  logger.debug(f"Scene {scene_id}: Applied rules: {classification_signals}")
  ```

### 8. Handle Edge Cases

- [ ] **Intro sequence (00:00-00:50)**: Skip or classify as special `intro` type?
- [ ] **MOTD 2 interlude**: Detect and skip (or classify as `interlude`)
- [ ] **Outro/league table**: Detect and classify as `outro`
- [ ] **VAR reviews**: Should remain part of highlights
- [ ] **Formation graphics**: Part of highlights or separate?
- [ ] **Missing OCR**: What if no scoreboard detected? (fallback to timing/transcript)

### 9. Integration Testing

- [ ] Test on full test video data
- [ ] Classify all 810 scenes
- [ ] Spot-check 10-20 scenes across different types
- [ ] Verify patterns make sense
- [ ] Document any surprising classifications

## Deliverables

### 1. Source Code
- `src/motd/analysis/__init__.py`
- `src/motd/analysis/segment_classifier.py`

### 2. Tests
- `tests/unit/analysis/test_segment_classifier.py`

### 3. Configuration
- Updated `config/config.yaml` with segment classification settings

### 4. Documentation
- Docstrings for all classes/methods
- Examples in docstrings
- README update if needed

## Success Criteria
- [ ] SegmentClassifier class implemented with all methods
- [ ] All 6 classification rules implemented
- [ ] Confidence scoring working
- [ ] Configuration support added
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration test on full video data
- [ ] Logging provides useful debugging info
- [ ] Edge cases handled gracefully
- [ ] Code follows Python style guidelines
- [ ] Ready for 011c (match boundary detector)

## Testing Commands

```bash
# Run unit tests
pytest tests/unit/analysis/test_segment_classifier.py -v

# Run with coverage
pytest tests/unit/analysis/test_segment_classifier.py --cov=src/motd/analysis

# Test on real data (integration)
python -m motd classify-segments data/cache/motd_2025-26_2025-11-01/scenes.json \
  --ocr data/cache/motd_2025-26_2025-11-01/ocr_results.json \
  --transcript data/cache/motd_2025-26_2025-11-01/transcript.json \
  --output data/cache/motd_2025-26_2025-11-01/classified_scenes.json
```

## Notes
- Start with simple heuristics, not ML (can enhance in Task 013)
- Prioritize precision over recall (better to be unsure than wrong)
- Low confidence (<0.6) = flag for manual review
- Document why rules work, not just what they do
- Keep rules configurable for easy tuning
- User validation in 011f will reveal if rules need adjustment

## Next Task
[011c-match-boundary-detector.md](011c-match-boundary-detector.md)
