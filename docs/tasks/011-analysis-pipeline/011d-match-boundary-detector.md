# Task 011d: Match Boundary Detector Implementation

## Quick Context

**Parent Task:** [011-analysis-pipeline](README.md)
**Domain Concepts:** [Running Order](../../domain/README.md#running-order), [Ground Truth](../../domain/README.md#ground-truth), [FT Graphic](../../domain/README.md#ft-graphic), [Episode Manifest](../../domain/README.md#episode-manifest)
**Business Rules:** [100% Running Order Accuracy Requirement](../../domain/business_rules.md#rule-4-100-running-order-accuracy-requirement)

**Why This Matters:** Running order is the **editorial sequence** MOTD chose to broadcast matches - NOT chronological by kickoff time. This is a key bias indicator ("Are certain teams always shown first?"). 100% accuracy is required because ALL downstream analysis depends on correct match assignment:
- Airtime calculations (wrong match = wrong team gets credit)
- Analysis timing (which team discussed first/last)
- Episode-to-episode patterns (running order trends over season)

**Critical Requirement:** If running order accuracy < 100%, **DO NOT proceed to Task 011e**. One wrong boundary corrupts 2+ matches (boundary error affects neighboring matches).

**Key Data:** Episode manifest (`data/episodes/episode_manifest.json`) defines expected matches for this episode. We know there are exactly 7 matches to detect - not 6, not 8. This constraint helps validate boundary detection.

See [Visual Patterns](../../domain/visual_patterns.md) for ground truth running order of reference episode.

---

## Objective
Identify where each match starts and ends, determine running order, and assign scenes to matches. This is **critical** for accuracy - if running order is wrong, everything downstream is useless.

## Prerequisites
- [x] Task 011b complete (segment classifier)
- [x] Have classified scenes with segment types

## Estimated Time
1.5-2 hours

## Target Accuracy
**100% running order accuracy** (7/7 matches correct order)

## What This Component Does

### Input
- Classified scenes (with segment types from 011b)
- OCR results (with fixture matches from Task 009)
- Transcript (with team mentions)

### Output
```json
{
  "matches": [
    {
      "running_order": 1,
      "match_id": "2025-11-01-liverpool-astonvilla",
      "teams": ["Liverpool", "Aston Villa"],
      "intro_scene_ids": [125],
      "highlights_scene_ids": [130, 131, ..., 220],
      "interview_scene_ids": [228, 229, 233],
      "analysis_scene_ids": [234, 235, ...],
      "first_team_mentioned_in_analysis": "Liverpool",
      "start_timestamp": 50.0,
      "end_timestamp": 865.0
    },
    ...
  ]
}
```

## Implementation Steps

### 1. Create Module
- [ ] Create `src/motd/analysis/match_boundary_detector.py`

### 2. Implement MatchBoundaryDetector Class

```python
class MatchBoundaryDetector:
    """Detects match boundaries and assigns running order."""

    def __init__(
        self,
        classified_scenes: List[Dict],
        ocr_results: List[Dict],
        transcript: Dict,
        team_data: Dict
    ):
        """
        Args:
            classified_scenes: Scenes with segment_type classification
            ocr_results: OCR results with fixture matches
            transcript: Transcription data
            team_data: Team names and alternates
        """
        pass

    def detect_matches(self) -> List[Dict]:
        """
        Detect all matches and assign running order.

        Returns:
            List of match dictionaries with scene assignments
        """
        pass

    def _find_match_starts(self) -> List[int]:
        """Find scene IDs where new matches start."""
        pass

    def _identify_match_teams(self, match_scenes: List[Dict]) -> Tuple[str, List[str]]:
        """
        Identify which match these scenes belong to.

        Returns:
            (match_id, [team1, team2])
        """
        pass

    def _assign_scenes_to_match(self, start_scene_id: int, end_scene_id: int) -> Dict:
        """Group scenes by segment type for a single match."""
        pass

    def _find_first_team_mentioned(self, analysis_scene_ids: List[int]) -> Optional[str]:
        """Find first team mentioned in studio analysis transcript."""
        pass
```

### 3. Implement Match Boundary Detection Algorithm

```python
def detect_matches(self) -> List[Dict]:
    matches = []
    current_match = None

    for scene in sorted_scenes:
        # Match start signals (in priority order)
        if self._is_match_start(scene):
            if current_match:
                matches.append(current_match)

            current_match = {
                "running_order": len(matches) + 1,
                "match_id": None,  # Will be determined
                "teams": None,
                "intro_scene_ids": [],
                "highlights_scene_ids": [],
                "interview_scene_ids": [],
                "analysis_scene_ids": [],
                "start_timestamp": scene["start_time"]
            }

        # Assign scene to current match
        if current_match:
            segment_type = scene["segment_type"]
            if segment_type == "studio_intro":
                current_match["intro_scene_ids"].append(scene["id"])
            elif segment_type == "highlights":
                current_match["highlights_scene_ids"].append(scene["id"])
            elif segment_type == "interviews":
                current_match["interview_scene_ids"].append(scene["id"])
            elif segment_type == "studio_analysis":
                current_match["analysis_scene_ids"].append(scene["id"])

    # Don't forget last match
    if current_match:
        matches.append(current_match)

    return matches
```

### 4. Implement Match Start Detection

- [ ] **Signal 1: Studio intro with team mentions**
  - Short scene (7-11 sec)
  - Classified as `studio_intro`
  - Transcript mentions 2 team names
  - → New match starting

- [ ] **Signal 2: OCR fixture match in highlights**
  - Highlights scene with OCR fixture detection
  - Different fixture from previous match
  - → Confirms match identity

- [ ] **Signal 3: Transition from previous analysis**
  - Previous scene has transition keywords ("Alright", "Right")
  - Current scene is short with team mention
  - → New match starting

```python
def _is_match_start(self, scene: Dict, previous_scene: Optional[Dict]) -> bool:
    """
    Determine if scene marks start of new match.

    Signals (in priority order):
    1. Studio intro + team mentions
    2. New fixture detected in OCR (different from previous)
    3. Transition from analysis + team mention
    """
    # Signal 1: Studio intro
    if scene["segment_type"] == "studio_intro":
        transcript = self._get_transcript_for_scene(scene)
        if self._count_team_mentions(transcript) >= 2:
            return True

    # Signal 2: New fixture in highlights
    if scene["segment_type"] == "highlights":
        ocr_fixture = self._get_ocr_fixture(scene["id"])
        if ocr_fixture and ocr_fixture != self.current_fixture:
            self.current_fixture = ocr_fixture
            return True

    # Signal 3: Transition + team mention
    if previous_scene and previous_scene["segment_type"] == "studio_analysis":
        prev_transcript = self._get_transcript_for_scene(previous_scene)
        if self._has_transition_words(prev_transcript):
            curr_transcript = self._get_transcript_for_scene(scene)
            if self._count_team_mentions(curr_transcript) >= 2:
                return True

    return False
```

### 5. Implement Match Identity Resolution

- [ ] **Primary: OCR fixture matches** (from Task 009)
  - Look for `matched_fixture` in OCR results for highlights scenes
  - Extract match_id and team names
  - Confidence: 0.95

- [ ] **Secondary: Team mentions in intro**
  - Extract team names from studio intro transcript
  - Match against fixture list (same gameweek)
  - Confidence: 0.85

- [ ] **Validation: Cross-check both signals**
  - If OCR fixture matches intro transcript → High confidence (0.95)
  - If mismatch → Log warning, prefer OCR

```python
def _identify_match_teams(self, match_scenes: List[Dict]) -> Tuple[str, List[str]]:
    """Identify which match these scenes belong to."""

    # Try OCR first (most reliable)
    for scene in match_scenes:
        if scene["segment_type"] == "highlights":
            ocr_fixture = self._get_ocr_fixture(scene["id"])
            if ocr_fixture:
                match_id = ocr_fixture["fixture_id"]
                teams = ocr_fixture["teams"]
                logger.info(f"Match identified via OCR: {match_id} ({teams})")
                return match_id, teams

    # Fallback: Team mentions in intro
    for scene in match_scenes:
        if scene["segment_type"] == "studio_intro":
            transcript = self._get_transcript_for_scene(scene)
            teams = self._extract_team_names(transcript)
            if len(teams) == 2:
                match_id = self._find_fixture_for_teams(teams)
                if match_id:
                    logger.warning(f"Match identified via transcript (no OCR): {match_id}")
                    return match_id, teams

    logger.error(f"Could not identify match for scenes {[s['id'] for s in match_scenes]}")
    return None, []
```

### 6. Implement Team Mention Detection for Analysis

- [ ] Extract transcript for analysis scenes
- [ ] Search for team names (with alternates)
- [ ] Return first chronological mention
- [ ] Handle edge cases:
  - No team mentioned (return None)
  - Both teams mentioned in same sentence (return first)
  - Only one team mentioned (return that team)

```python
def _find_first_team_mentioned(self, analysis_scene_ids: List[int]) -> Optional[str]:
    """Find first team mentioned in studio analysis."""

    for scene_id in sorted(analysis_scene_ids):
        scene = self._get_scene_by_id(scene_id)
        transcript_segments = self._get_transcript_for_scene(scene)

        for segment in transcript_segments:
            # Check each word against team names
            text = segment["text"].lower()
            for team in self.team_data["teams"]:
                for variant in team["alternates"]:
                    if variant.lower() in text:
                        logger.info(f"First team mentioned in analysis: {team['name']} (scene {scene_id})")
                        return team["name"]

    logger.warning(f"No team mention found in analysis scenes {analysis_scene_ids}")
    return None
```

### 7. Implement Scene Assignment

- [ ] Group scenes by match based on boundaries
- [ ] Separate by segment type (intro/highlights/interviews/analysis)
- [ ] Calculate start/end timestamps per match
- [ ] Handle edge cases:
  - Missing segment types (e.g., no interviews)
  - Scenes between matches (attribute to previous match)

### 8. Add Validation Against Ground Truth

- [ ] Load ground truth from `docs/motd_visual_patterns.md`
- [ ] Compare detected running order vs expected:
  ```python
  expected_order = [
      ("Liverpool", "Aston Villa", 50),
      ("Burnley", "Arsenal", 865),
      ("Forest", "Manchester United", 1587),
      ("Fulham", "Wolves", 2509),
      ("Spurs", "Chelsea", 3167),
      ("Brighton", "Leeds", 3894),
      ("Palace", "Brentford", 4480)
  ]
  ```
- [ ] Assert 7/7 matches detected
- [ ] Assert correct chronological order
- [ ] Assert start timestamps within ±10 seconds

### 9. Implement Unit Tests

- [ ] Create `tests/unit/analysis/test_match_boundary_detector.py`
- [ ] Test match start detection
- [ ] Test match identity resolution
- [ ] Test scene assignment
- [ ] Test team mention detection
- [ ] Test running order accuracy
- [ ] Test edge cases (missing segments, etc.)

### 10. Add Logging & Debugging

- [ ] Log each detected match boundary
- [ ] Log match identification (OCR vs transcript)
- [ ] Log scene assignments per match
- [ ] Log validation results vs ground truth
- [ ] WARNING for low confidence matches
- [ ] ERROR for unidentified matches

## Deliverables

### 1. Source Code
- `src/motd/analysis/match_boundary_detector.py`

### 2. Tests
- `tests/unit/analysis/test_match_boundary_detector.py`

### 3. Validation Script
- Script to compare detected order vs ground truth
- Output accuracy report

## Success Criteria
- [ ] MatchBoundaryDetector class implemented
- [ ] Match boundary detection algorithm working
- [ ] Match identity resolution (OCR + transcript)
- [ ] Scene assignment by segment type
- [ ] Team mention detection for analysis
- [ ] Running order: **100% accuracy** (7/7 matches)
- [ ] Start timestamps within ±10 seconds of ground truth
- [ ] All matches have valid match_id and teams
- [ ] Unit tests passing
- [ ] Code follows Python style guidelines
- [ ] Ready for 011d (airtime calculator)

## Testing Commands

```bash
# Run unit tests
pytest tests/unit/analysis/test_match_boundary_detector.py -v

# Test on real data
python -m motd detect-matches data/cache/motd_2025-26_2025-11-01/classified_scenes.json \
  --ocr data/cache/motd_2025-26_2025-11-01/ocr_results.json \
  --transcript data/cache/motd_2025-26_2025-11-01/transcript.json \
  --output data/cache/motd_2025-26_2025-11-01/matches.json

# Validate against ground truth
python -m motd validate-matches data/cache/motd_2025-26_2025-11-01/matches.json \
  --ground-truth docs/motd_visual_patterns.md
```

## Edge Cases to Handle

1. **Missing studio intro**: Match starts directly with highlights
2. **Missing interviews**: Highlights → Studio analysis directly
3. **Multiple interviews**: Group all interviews together
4. **Interlude between matches**: MOTD 2 promo (exclude from any match)
5. **Outro after last match**: League table review (separate from Match 7)
6. **OCR miss**: Highlights without OCR detection (use transcript fallback)
7. **Ambiguous team mentions**: "United" could be multiple teams (use fixture context)

## Notes
- **Running order is CRITICAL** - 100% accuracy required
- Ground truth is already documented (motd_visual_patterns.md)
- OCR fixture matches are most reliable signal
- Team mentions provide validation/fallback
- FT graphics mark end of highlights (useful boundary)
- User will manually validate in 011f
- If accuracy < 100%, iterate before moving to 011d

## Next Task
[011d-airtime-calculator.md](011d-airtime-calculator.md)
