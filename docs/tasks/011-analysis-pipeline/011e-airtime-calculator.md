# Task 011d: Airtime Calculator Implementation

## Objective
Calculate total airtime per match broken down by segment type (studio intro, highlights, interviews, studio analysis).

## Prerequisites
- [x] Task 011c complete (match boundaries detected, scenes assigned to matches)

## Estimated Time
1-1.5 hours

## What This Component Does

### Input
- Matches with scene assignments (from 011c)
- Original scenes with durations

### Output
```json
{
  "match_id": "2025-11-01-liverpool-astonvilla",
  "running_order": 1,
  "teams": ["Liverpool", "Aston Villa"],
  "segments": [
    {
      "type": "studio_intro",
      "duration_seconds": 20,
      "scene_count": 1
    },
    {
      "type": "highlights",
      "duration_seconds": 518,
      "scene_count": 90
    },
    {
      "type": "interviews",
      "duration_seconds": 52,
      "scene_count": 5
    },
    {
      "type": "studio_analysis",
      "duration_seconds": 201,
      "scene_count": 9
    }
  ],
  "total_airtime_seconds": 791
}
```

## Implementation Steps

### 1. Create Module
- [ ] Create `src/motd/analysis/airtime_calculator.py`

### 2. Implement AirtimeCalculator Class

```python
class AirtimeCalculator:
    """Calculates airtime per match broken down by segment type."""

    def __init__(
        self,
        matches: List[Dict],
        scenes: List[Dict]
    ):
        """
        Args:
            matches: Match boundaries with scene assignments
            scenes: Original scenes with durations
        """
        self.matches = matches
        self.scenes_by_id = {s["id"]: s for s in scenes}

    def calculate_airtime(self) -> List[Dict]:
        """
        Calculate airtime for all matches.

        Returns:
            List of matches with airtime breakdown
        """
        pass

    def _calculate_match_airtime(self, match: Dict) -> Dict:
        """Calculate airtime for a single match."""
        pass

    def _sum_scene_durations(self, scene_ids: List[int]) -> float:
        """Sum durations for list of scene IDs."""
        pass

    def _get_scene_count(self, scene_ids: List[int]) -> int:
        """Count number of scenes."""
        pass
```

### 3. Implement Airtime Calculation Logic

```python
def calculate_airtime(self) -> List[Dict]:
    """Calculate airtime for all matches."""

    results = []

    for match in self.matches:
        # Calculate duration per segment type
        segments = []

        # Studio intro
        if match.get("intro_scene_ids"):
            intro_duration = self._sum_scene_durations(match["intro_scene_ids"])
            segments.append({
                "type": "studio_intro",
                "duration_seconds": round(intro_duration, 1),
                "scene_count": len(match["intro_scene_ids"])
            })

        # Highlights
        if match.get("highlights_scene_ids"):
            highlights_duration = self._sum_scene_durations(match["highlights_scene_ids"])
            segments.append({
                "type": "highlights",
                "duration_seconds": round(highlights_duration, 1),
                "scene_count": len(match["highlights_scene_ids"])
            })

        # Interviews
        if match.get("interview_scene_ids"):
            interview_duration = self._sum_scene_durations(match["interview_scene_ids"])
            segments.append({
                "type": "interviews",
                "duration_seconds": round(interview_duration, 1),
                "scene_count": len(match["interview_scene_ids"])
            })

        # Studio analysis
        if match.get("analysis_scene_ids"):
            analysis_duration = self._sum_scene_durations(match["analysis_scene_ids"])
            segments.append({
                "type": "studio_analysis",
                "duration_seconds": round(analysis_duration, 1),
                "scene_count": len(match["analysis_scene_ids"]),
                "first_team_mentioned": match.get("first_team_mentioned_in_analysis")
            })

        # Calculate total
        total_airtime = sum(seg["duration_seconds"] for seg in segments)

        # Build result
        result = {
            "match_id": match["match_id"],
            "running_order": match["running_order"],
            "teams": match["teams"],
            "segments": segments,
            "total_airtime_seconds": round(total_airtime, 1)
        }

        results.append(result)
        logger.info(f"Match {match['running_order']}: {total_airtime:.1f}s total airtime")

    return results
```

### 4. Implement Duration Summation

```python
def _sum_scene_durations(self, scene_ids: List[int]) -> float:
    """Sum durations for list of scene IDs."""

    total = 0.0
    missing_scenes = []

    for scene_id in scene_ids:
        scene = self.scenes_by_id.get(scene_id)
        if scene:
            # Duration could be in seconds or calculated from start/end
            if "duration" in scene:
                total += scene["duration"]
            elif "start_time" in scene and "end_time" in scene:
                total += scene["end_time"] - scene["start_time"]
            else:
                logger.warning(f"Scene {scene_id} has no duration information")
        else:
            missing_scenes.append(scene_id)

    if missing_scenes:
        logger.error(f"Missing scenes in lookup: {missing_scenes}")

    return total
```

### 5. Add Validation Checks

- [ ] Validate all scene IDs exist in scenes data
- [ ] Validate no negative durations
- [ ] Validate total airtime is reasonable (5-20 minutes per match typical)
- [ ] Warn if any segment type is missing
- [ ] Warn if durations are unexpectedly short/long

```python
def _validate_match_airtime(self, match_result: Dict) -> None:
    """Validate airtime calculation for a match."""

    total = match_result["total_airtime_seconds"]

    # Check reasonable range (5-20 minutes per match)
    if total < 300:  # 5 minutes
        logger.warning(f"Match {match_result['running_order']}: Very short airtime ({total}s)")
    elif total > 1200:  # 20 minutes
        logger.warning(f"Match {match_result['running_order']}: Very long airtime ({total}s)")

    # Check for missing segment types
    segment_types = {seg["type"] for seg in match_result["segments"]}
    expected_types = {"studio_intro", "highlights", "interviews", "studio_analysis"}
    missing_types = expected_types - segment_types

    if missing_types:
        logger.warning(f"Match {match_result['running_order']}: Missing segments: {missing_types}")

    # Check highlights are longest segment (typically)
    highlights_seg = next((s for s in match_result["segments"] if s["type"] == "highlights"), None)
    if highlights_seg:
        if highlights_seg["duration_seconds"] < total * 0.5:
            logger.warning(f"Match {match_result['running_order']}: Highlights unusually short ({highlights_seg['duration_seconds']}s)")
```

### 6. Add Summary Statistics

```python
def calculate_summary_stats(self, results: List[Dict]) -> Dict:
    """Calculate summary statistics across all matches."""

    total_matches = len(results)
    total_airtime = sum(m["total_airtime_seconds"] for m in results)
    avg_airtime = total_airtime / total_matches if total_matches > 0 else 0

    # Per segment type
    segment_stats = {}
    for segment_type in ["studio_intro", "highlights", "interviews", "studio_analysis"]:
        durations = [
            seg["duration_seconds"]
            for match in results
            for seg in match["segments"]
            if seg["type"] == segment_type
        ]
        if durations:
            segment_stats[segment_type] = {
                "total_seconds": sum(durations),
                "average_seconds": sum(durations) / len(durations),
                "min_seconds": min(durations),
                "max_seconds": max(durations),
                "count": len(durations)
            }

    return {
        "total_matches": total_matches,
        "total_airtime_seconds": round(total_airtime, 1),
        "average_airtime_per_match_seconds": round(avg_airtime, 1),
        "segment_statistics": segment_stats
    }
```

### 7. Implement Unit Tests

- [ ] Create `tests/unit/analysis/test_airtime_calculator.py`
- [ ] Test single match calculation
- [ ] Test multiple matches calculation
- [ ] Test missing segment types (partial data)
- [ ] Test missing scenes (error handling)
- [ ] Test duration summation accuracy
- [ ] Test validation warnings
- [ ] Test summary statistics

Sample test:
```python
def test_calculates_match_airtime():
    """Test airtime calculation for single match."""

    scenes = [
        {"id": 1, "duration": 10.0},
        {"id": 2, "duration": 300.0},
        {"id": 3, "duration": 50.0},
        {"id": 4, "duration": 200.0}
    ]

    matches = [{
        "running_order": 1,
        "match_id": "test-match",
        "teams": ["Team A", "Team B"],
        "intro_scene_ids": [1],
        "highlights_scene_ids": [2],
        "interview_scene_ids": [3],
        "analysis_scene_ids": [4]
    }]

    calculator = AirtimeCalculator(matches, scenes)
    results = calculator.calculate_airtime()

    assert len(results) == 1
    assert results[0]["total_airtime_seconds"] == 560.0
    assert len(results[0]["segments"]) == 4
```

### 8. Add Logging

- [ ] Log airtime per match at INFO level
- [ ] Log warnings for unusual durations
- [ ] Log summary statistics at INFO level
- [ ] DEBUG level for per-segment breakdowns

### 9. Handle Edge Cases

- [ ] **Missing segment types**: Match with no interviews (skip segment)
- [ ] **Zero duration scenes**: Scene with 0 duration (log warning, include as 0)
- [ ] **Missing scene IDs**: Scene not found in lookup (log error, skip)
- [ ] **Duplicate scene IDs**: Same scene in multiple segments (log warning)
- [ ] **Negative durations**: Invalid data (log error, skip)

### 10. Integration Testing

- [ ] Test on full test video data
- [ ] Calculate airtime for all 7 matches
- [ ] Verify totals are reasonable
- [ ] Check summary statistics
- [ ] Compare against manual timings from motd_visual_patterns.md

## Deliverables

### 1. Source Code
- `src/motd/analysis/airtime_calculator.py`

### 2. Tests
- `tests/unit/analysis/test_airtime_calculator.py`

### 3. Summary Report
- Airtime breakdown per match
- Summary statistics
- Validation of calculations

## Success Criteria
- [ ] AirtimeCalculator class implemented
- [ ] Airtime calculation working for all segment types
- [ ] Duration summation accurate
- [ ] Validation checks in place
- [ ] Summary statistics calculated
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration test on full video data
- [ ] Logging provides useful info
- [ ] Edge cases handled gracefully
- [ ] Code follows Python style guidelines
- [ ] Ready for 011e (pipeline orchestrator)

## Testing Commands

```bash
# Run unit tests
pytest tests/unit/analysis/test_airtime_calculator.py -v

# Test on real data
python -m motd calculate-airtime data/cache/motd_2025-26_2025-11-01/matches.json \
  --scenes data/cache/motd_2025-26_2025-11-01/scenes.json \
  --output data/cache/motd_2025-26_2025-11-01/airtime.json
```

## Expected Results (Approximate)

Based on motd_visual_patterns.md, expected durations:

| Match | Intro | Highlights | Interviews | Analysis | Total |
|-------|-------|------------|------------|----------|-------|
| 1 | 20s | 518s | 52s | 201s | 791s |
| 2 | 11s | 429s | 48s | 210s | 698s |
| 3 | 11s | 478s | 74s | 310s | 873s |
| 4 | 8s | 329s | 99s | 133s | 569s |
| 5 | 7s | 433s | 55s | 190s | 685s |
| 6 | 9s | 248s | 46s | 130s | 433s |
| 7 | 9s | 297s | 65s | 67s | 438s |

Use these as validation targets (±30 seconds acceptable due to scene boundaries).

## Notes
- This is mostly arithmetic - should be straightforward
- Main challenge is handling missing/partial data gracefully
- Validation checks are important for catching classification errors
- Summary statistics provide useful overview for analysis
- User can validate these numbers against video manually in 011f

## Next Task
[011e-pipeline-orchestrator.md](011e-pipeline-orchestrator.md)
