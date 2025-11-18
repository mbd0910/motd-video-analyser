# Task 011c-3: Segment Classifier Implementation

## Quick Context

**Parent Task:** [011c-segment-classifier](011c-segment-classifier.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Scene](../../domain/README.md#scene), [Confidence Scoring](../../domain/business_rules.md#rule-6-confidence-scoring)
**Business Rules:** [Segment Classification Hierarchy](../../domain/business_rules.md#rule-5-segment-classification-hierarchy)

**Why This Matters:** Segment classification enables answering the core research question: "Do some teams get more analysis than others?" We need to distinguish between highlights (match footage) and studio analysis (pundit discussion) to measure quality of coverage, not just quantity. This classifier uses only validated rules from 011c-2, preventing wasted effort on ineffective heuristics.

**Key Insight:** We're building a rule-based classifier (not ML) using validated signals: FT graphic detection, OCR presence, duration ranges, transcript keywords, and sequencing patterns. The validation-driven approach (011c-1 → 011c-2 → 011c-3) ensures we only implement rules that actually work.

**Critical Requirement:** >85% accuracy on ground truth dataset (from 011c-1) before running on full 1,229-scene dataset.

See [Segment Types](../../domain/README.md#segment-types) for definitions and [Business Rules](../../domain/business_rules.md#rule-5-segment-classification-hierarchy) for classification logic hierarchy.

---

## Objective

Implement a multi-signal segment classifier using only validated rules from 011c-2, achieving >85% accuracy on the ground truth dataset before classifying the full episode (1,229 scenes).

## Prerequisites

- [x] Task 011c-1 complete (ground truth dataset with 39 labeled scenes)
- [x] Task 011c-2 complete (at least 2-3 rules validated)
- [ ] Validation report shows which rules to implement and their priority order
- [ ] Config file updated: `config/config.yaml` with validated thresholds
- [ ] Understanding of [Confidence Scoring](../../domain/business_rules.md#rule-6-confidence-scoring)

## Estimated Time

90 minutes

## Target Accuracy

- >85% on ground truth dataset (39 scenes)
- >80% on full dataset (spot-check validation)

## Deliverables

1. **`src/motd/analysis/segment_classifier.py`** - SegmentClassifier implementation
2. **`tests/unit/analysis/test_segment_classifier.py`** - Unit tests with >80% coverage
3. **Classification results** - Full dataset classified with confidence scores
4. **Accuracy report** - Performance metrics on ground truth and full dataset

## Implementation Steps

### 1. Create Module Structure (5 mins)

- [ ] Create directory: `src/motd/analysis/`
- [ ] Create `src/motd/analysis/__init__.py`
- [ ] Create `src/motd/analysis/segment_classifier.py`
- [ ] Create `tests/unit/analysis/` directory
- [ ] Create `tests/unit/analysis/__init__.py`
- [ ] **Commit:** `feat(analysis): Create segment classifier module structure`

---

### 2. Implement SegmentClassifier Class (TDD Approach) (40 mins)

**Use Test-Driven Development:** Write tests first, then implementation

#### 2a. Create Test Structure (10 mins)

- [ ] Create `tests/unit/analysis/test_segment_classifier.py`
- [ ] Define test fixtures:
  ```python
  @pytest.fixture
  def sample_scenes():
      """Sample scenes from ground truth dataset."""
      return [
          {"scene_id": 220, "start_seconds": 610.5, "end_seconds": 613.0, "duration": 2.5},
          # Add 5-10 representative scenes from ground truth
      ]

  @pytest.fixture
  def sample_ocr_results():
      """OCR results with FT graphic and scoreboard examples."""
      return [
          {"scene_id": 220, "ft_graphic": True, "detected_teams": ["Liverpool", "Aston Villa"]},
          # Add corresponding OCR results
      ]

  @pytest.fixture
  def sample_transcript():
      """Transcript segments overlapping scenes."""
      return {
          "segments": [
              {"start": 610.0, "end": 615.0, "text": "Full time at Anfield..."},
              # Add transcript examples
          ]
      }

  @pytest.fixture
  def classifier(sample_scenes, sample_ocr_results, sample_transcript):
      """Initialized SegmentClassifier."""
      return SegmentClassifier(
          scenes=sample_scenes,
          ocr_results=sample_ocr_results,
          transcript=sample_transcript,
          config=load_test_config()
      )
  ```
- [ ] Write initial tests (failing):
  ```python
  def test_ft_graphic_marks_highlights_end(classifier):
      """Scene with FT graphic should be classified as highlights."""
      result = classifier.classify_scene(scene_id=220)
      assert result["segment_type"] == "highlights"
      assert result["confidence"] > 0.9
      assert "ft_graphic" in result["classification_signals"]

  def test_scoreboard_ocr_indicates_highlights(classifier):
      """Scene with scoreboard OCR should be highlights."""
      result = classifier.classify_scene(scene_id=154)
      assert result["segment_type"] == "highlights"
      assert "scoreboard_ocr" in result["classification_signals"]

  def test_duration_range_validation(classifier):
      """Scene duration should match segment type expectations."""
      result = classifier.classify_scene(scene_id=125)  # Studio intro
      assert result["segment_type"] == "studio_intro"
      assert 5 <= result["scene_duration"] <= 20  # From config

  def test_confidence_scoring_multiple_signals(classifier):
      """Confidence increases with multiple agreeing signals."""
      result = classifier.classify_scene(scene_id=220)
      # FT graphic + duration + transcript = multiple signals
      assert result["confidence"] > 0.9
      assert len(result["classification_signals"]) >= 2
  ```
- [ ] **Commit:** `test(analysis): Create segment classifier test structure (TDD)`

#### 2b. Implement Core Classifier (30 mins)

- [ ] Implement `SegmentClassifier` class in `src/motd/analysis/segment_classifier.py`:

```python
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SegmentClassifier:
    """
    Classifies video scenes into segment types using multi-signal approach.

    Implements validated rules from Task 011c-2 in priority order.
    Uses confidence scoring to indicate classification certainty.
    """

    def __init__(
        self,
        scenes: List[Dict],
        ocr_results: List[Dict],
        transcript: Dict,
        config: Optional[Dict] = None
    ):
        """
        Args:
            scenes: Scene detection results (from PySceneDetect + interval sampling)
            ocr_results: OCR detection results (FT graphics, scoreboards)
            transcript: Transcription results (word-level timing)
            config: Classification thresholds (from config.yaml)
        """
        self.scenes = {s["scene_id"]: s for s in scenes}
        self.ocr_by_scene = {ocr["scene_id"]: ocr for ocr in ocr_results}
        self.transcript = transcript
        self.config = config or self._load_default_config()

        # Build scene→transcript index for fast lookup
        self._build_transcript_index()

    def classify_scenes(self) -> List[Dict]:
        """
        Classify all scenes with segment types.

        Returns:
            List of scenes with added fields:
            - segment_type: str (studio_intro/highlights/interviews/studio_analysis/intro/interlude/outro)
            - confidence: float (0-1)
            - classification_signals: List[str] (which rules triggered)
        """
        classified = []
        for scene_id in sorted(self.scenes.keys()):
            result = self.classify_scene(scene_id)
            classified.append(result)

        return classified

    def classify_scene(self, scene_id: int) -> Dict:
        """
        Classify a single scene.

        Applies rules in priority order (from 011c-2 validation):
        1. FT graphic detection (highest confidence)
        2. Scoreboard OCR presence
        3. Duration + position heuristics
        4. Transcript keyword matching
        5. Sequencing validation

        Returns:
            Dict with segment_type, confidence, signals, scene metadata
        """
        scene = self.scenes[scene_id]
        signals = []
        confidence = 0.5  # Base confidence
        segment_type = None

        # Rule 1: FT Graphic Detection (Priority 1)
        if self._has_ft_graphic(scene_id):
            segment_type = "highlights"
            confidence = 0.95
            signals.append("ft_graphic")
            logger.debug(f"Scene {scene_id}: FT graphic detected → highlights")

        # Rule 2: Scoreboard OCR (Priority 2)
        elif self._has_scoreboard_ocr(scene_id):
            segment_type = "highlights"
            confidence = 0.90
            signals.append("scoreboard_ocr")
            logger.debug(f"Scene {scene_id}: Scoreboard OCR → highlights")

        # Rule 3: Duration + Position Heuristics (Priority 3)
        # [Implement based on validated rules from 011c-2]

        # Rule 4: Transcript Keyword Matching (Priority 4)
        # [Implement if validated in 011c-2]

        # Rule 5: Sequencing Validation (Boost confidence)
        # [Implement to boost confidence if scene follows expected pattern]

        # Confidence boosting: Multiple agreeing signals
        if len(signals) > 1:
            confidence = min(0.95, confidence + (len(signals) - 1) * 0.05)

        # Log low-confidence classifications
        if confidence < 0.6:
            logger.warning(f"Scene {scene_id}: Low confidence classification ({confidence:.2f})")

        return {
            "scene_id": scene_id,
            "segment_type": segment_type or "unknown",
            "confidence": confidence,
            "classification_signals": signals,
            "scene_duration": scene["duration"],
            "timestamp": scene["start_seconds"]
        }

    def _has_ft_graphic(self, scene_id: int) -> bool:
        """Check if scene has FT graphic detection."""
        ocr = self.ocr_by_scene.get(scene_id)
        return ocr is not None and ocr.get("ft_graphic", False)

    def _has_scoreboard_ocr(self, scene_id: int) -> bool:
        """Check if scene has scoreboard OCR detection."""
        ocr = self.ocr_by_scene.get(scene_id)
        return ocr is not None and ocr.get("ocr_source") == "scoreboard"

    def _get_transcript_for_scene(self, scene: Dict) -> List[Dict]:
        """Get transcript segments overlapping with scene timespan."""
        # [Implement using pre-built index]
        pass

    def _build_transcript_index(self):
        """Build scene→transcript index for fast lookup."""
        # [Implement during initialization]
        pass

    def _load_default_config(self) -> Dict:
        """Load default configuration from config.yaml."""
        # [Implement config loading]
        pass
```

- [ ] Implement only validated rules from 011c-2 report
- [ ] Add logging at INFO (decisions), WARNING (low confidence), DEBUG (rule applications)
- [ ] Ensure tests pass incrementally as rules are added
- [ ] **Commit:** `feat(analysis): Implement SegmentClassifier with validated rules`

---

### 3. Test on Ground Truth Dataset (15 mins)

- [ ] Create test script: `scripts/test_classifier_ground_truth.py`
- [ ] Load ground truth labels from `docs/ground_truth/labeling_template.md`
- [ ] Run classifier on 39 ground truth scenes
- [ ] Calculate accuracy metrics:
  ```python
  # Overall accuracy
  correct = sum(1 for gt, pred in zip(ground_truth, predictions) if gt == pred)
  accuracy = correct / len(ground_truth)

  # Per-segment-type accuracy
  for segment_type in ["studio_intro", "highlights", "interviews", "studio_analysis"]:
      # Calculate precision, recall, F1

  # Confusion matrix
  # Which segment types are confused with each other?
  ```
- [ ] Generate accuracy report:
  ```markdown
  # Ground Truth Validation Results

  **Overall Accuracy:** XX% (target: >85%)

  ## Per-Segment-Type Performance
  | Segment Type | Precision | Recall | F1 | Samples |
  |--------------|-----------|--------|-----|---------|
  | Studio intro | XX% | XX% | XX | 7 |
  | Highlights | XX% | XX% | XX | 8 |
  | Interviews | XX% | XX% | XX | 5 |
  | Studio analysis | XX% | XX% | XX | 7 |

  ## Confusion Matrix
  [Show which types are confused]

  ## Errors
  [List scenes where classifier failed, with analysis]
  ```
- [ ] **Commit:** `test: Validate classifier on ground truth dataset (XX% accuracy)`

**Success criteria:** >85% overall accuracy

**If <85%:**
- Analyze failure patterns
- Adjust rules or thresholds
- Re-run validation

---

### 4. Iterate on Failures (15 mins - if needed)

- [ ] If accuracy <85%, analyze errors:
  - Which segment types have most errors?
  - Are rules too strict or too loose?
  - Do we need additional signals?
  - Should we add visual recognition?
- [ ] Adjust implementation:
  - Tune confidence thresholds
  - Adjust duration ranges
  - Add/remove rules
  - Improve sequencing logic
- [ ] Re-test on ground truth
- [ ] **Commit:** `fix(analysis): Improve classifier accuracy based on ground truth failures`

**Iterate until >85% accuracy**

---

### 5. Run on Full Dataset (10 mins)

- [ ] Create CLI command: `python -m motd classify-segments`
  ```python
  # src/motd/__main__.py
  @click.command()
  @click.argument('scenes_file')
  @click.argument('ocr_file')
  @click.argument('transcript_file')
  @click.option('--output', '-o', help='Output file path')
  def classify_segments(scenes_file, ocr_file, transcript_file, output):
      """Classify all scenes into segment types."""
      # Load data
      # Run classifier
      # Save results
  ```
- [ ] Run on full dataset (1,229 scenes):
  ```bash
  python -m motd classify-segments \
    data/cache/motd_2025-26_2025-11-01/scenes.json \
    data/cache/motd_2025-26_2025-11-01/ocr_results.json \
    data/cache/motd_2025-26_2025-11-01/transcript.json \
    --output data/cache/motd_2025-26_2025-11-01/classified_scenes.json
  ```
- [ ] Log summary statistics:
  - Total scenes: 1,229
  - Classified by type: {studio_intro: X, highlights: Y, ...}
  - Average confidence per type
  - Low-confidence scenes (<0.6): Count and list
- [ ] **Commit:** `feat(analysis): Classify full dataset (1,229 scenes)`

---

### 6. Spot-Check Validation (10 mins)

- [ ] User validates 10-20 scenes from full dataset:
  - Pick 2-3 scenes per segment type
  - View frames to verify classification
  - Note any systematic errors
- [ ] Document spot-check results:
  ```markdown
  ## Spot-Check Validation

  **Scenes checked:** 15
  **Correct:** XX/15 (XX%)
  **Errors:** X scenes

  ### Errors Found:
  - Scene XXX: Classified as [type] but actually [type] - [reason]

  ### Systematic Issues:
  - [Any patterns in errors?]
  ```
- [ ] **Decision:** Is accuracy sufficient to proceed to 011d?
- [ ] **Commit:** `test: Spot-check classifier on full dataset (XX/15 correct)`

---

## Success Criteria

- [ ] SegmentClassifier class implemented with validated rules
- [ ] Unit tests passing with >80% coverage
- [ ] Ground truth accuracy >85%
- [ ] Full dataset classified (1,229 scenes)
- [ ] Spot-check validation >80% correct
- [ ] Logging provides useful debugging info
- [ ] Code follows Python style guidelines
- [ ] Ready for Task 011d (match boundary detection)

## Edge Cases to Handle

- [ ] **Intro sequence (00:00-00:50)**: Classify as `intro` type
- [ ] **MOTD 2 interlude (52:01-52:47)**: Classify as `interlude` type
- [ ] **Outro/league table (82:57+)**: Classify as `outro` type
- [ ] **Transition scenes (<2s)**: May be classified as highlights or skipped
- [ ] **Missing OCR**: Fallback to duration + transcript + sequencing
- [ ] **Missing transcript**: Fallback to OCR + duration
- [ ] **Ambiguous scenes**: Return low confidence (<0.6), flag for manual review

## Configuration

Update `config/config.yaml` with segment classification settings:

```yaml
segment_classification:
  studio_intro:
    min_duration_seconds: X  # From 011c-2 validation
    max_duration_seconds: X
    keywords: ["let's look at", "coming up", "now", "next"]

  highlights:
    min_duration_seconds: X
    max_duration_seconds: X

  interviews:
    min_duration_seconds: X
    max_duration_seconds: X
    keywords: ["speak to", "join us", "after the game", "thoughts on"]

  studio_analysis:
    min_duration_seconds: X
    max_duration_seconds: X
    transition_keywords: ["alright", "right", "moving on", "what did you make"]

  confidence_thresholds:
    high: 0.85  # Multiple signals agree
    medium: 0.70  # Single strong signal
    low: 0.50  # Weak signals or conflicts
```

## Testing Commands

```bash
# Run unit tests
pytest tests/unit/analysis/test_segment_classifier.py -v

# Run with coverage
pytest tests/unit/analysis/test_segment_classifier.py --cov=src/motd/analysis

# Test on ground truth
python scripts/test_classifier_ground_truth.py

# Classify full dataset
python -m motd classify-segments \
  data/cache/motd_2025-26_2025-11-01/scenes.json \
  data/cache/motd_2025-26_2025-11-01/ocr_results.json \
  data/cache/motd_2025-26_2025-11-01/transcript.json \
  --output data/cache/motd_2025-26_2025-11-01/classified_scenes.json
```

## Next Task

**If accuracy >85% on ground truth + spot-check:**
→ Proceed to Task 011d: Match Boundary Detection

**If accuracy 70-85%:**
→ Document limitations and proceed with caveat (may need refinement)

**If accuracy <70%:**
→ Pause and consider:
  - Add visual recognition (studio vs pitch detection)
  - Defer to Task 013 (ML approach)
  - Redefine segment types

## Notes

- **Start simple, iterate:** Implement 2-3 validated rules first, test, then add more
- **Prioritize precision over recall:** Better to be unsure than wrong (low confidence OK)
- **Log everything:** INFO (decisions), WARNING (low confidence), DEBUG (rule applications)
- **Config-driven:** All thresholds in config.yaml for easy tuning
- **User validation crucial:** 011f will reveal if rules need adjustment

## Related Tasks

- [011c-1: Ground Truth Dataset](011c-1-ground-truth-dataset.md) - Created labeled test set
- [011c-2: Assumption Validation](011c-2-assumption-validation.md) - Validated which rules to implement
- [011d: Match Boundary Detection](011d-match-boundary-detector.md) - Next task (uses classified scenes)
