# Task 009f: Run OCR on Test Video

## Objective
Execute the OCR CLI command on test video and collect results for validation.

## Prerequisites
- Task 009e completed (CLI command implemented)
- Test data available:
  - Scenes: `data/cache/motd_2025-26_2025-11-01/scenes.json`
  - Frames: `data/cache/motd_2025-26_2025-11-01/frames/*.jpg`
  - Episode manifest and fixtures created

## Tasks

### 1. Verify Prerequisites (5-10 min)
- [ ] Confirm scenes JSON exists with 810 scenes
- [ ] Confirm frames directory has 810 images
- [ ] Confirm episode manifest exists and has correct episode_id
- [ ] Confirm fixtures data has 7 matches for 2025-11-01

### 2. Run OCR Command (30-45 min processing time)
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Run command:
  ```bash
  python -m motd extract-teams \
    --scenes data/cache/motd_2025-26_2025-11-01/scenes.json \
    --episode-id motd_2025-26_2025-11-01
  ```
- [ ] Monitor progress output
- [ ] Wait for completion
- [ ] Check for errors in logs

### 3. Review Output (10-15 min)
- [ ] Verify output file created: `data/cache/motd_2025-26_2025-11-01/ocr_results.json`
- [ ] Check JSON is valid (no syntax errors)
- [ ] Review summary statistics:
  - [ ] How many scenes processed after filtering?
  - [ ] How many unique teams detected?
  - [ ] How many validated vs unexpected detections?
- [ ] Spot-check a few OCR results

### 4. Initial Quality Check (10-15 min)
- [ ] Open a few frames mentioned in OCR results
- [ ] Visually verify teams were correctly detected
- [ ] Check if formation graphics were captured
- [ ] Check if scoreboard graphics were captured
- [ ] Note any obvious failures

### 5. Document Findings (10-15 min)
- [ ] Record processing time
- [ ] Record number of scenes processed
- [ ] Record summary statistics
- [ ] Note any errors or warnings
- [ ] List any obvious issues to investigate in 009g

## Expected Output Structure

The output JSON should look like:

```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "video_path": "data/videos/motd_2025-26_2025-11-01.mp4",
  "total_scenes": 810,
  "filtered_scenes": 243,
  "expected_fixtures": [
    {
      "match_id": "2025-11-01-brighton-leeds",
      "home_team": "Brighton & Hove Albion",
      "away_team": "Leeds United"
    }
    // ... 6 more
  ],
  "ocr_results": [
    {
      "scene_id": 45,
      "start_time": "00:05:32.120",
      "start_seconds": 332.12,
      "frame_path": "data/cache/.../frames/scene_045.jpg",
      "detected_teams": [
        {
          "team": "Brighton & Hove Albion",
          "confidence": 0.92,
          "region": "formation",
          "matched_text": "brighton"
        },
        {
          "team": "Leeds United",
          "confidence": 0.89,
          "region": "formation",
          "matched_text": "leeds"
        }
      ],
      "validation": {
        "expected_teams": [...],
        "validated_teams": ["Brighton & Hove Albion", "Leeds United"],
        "unexpected_teams": [],
        "confidence_boost": 1.1
      },
      "matched_fixture": "2025-11-01-brighton-leeds"
    }
    // ... more results
  ],
  "summary": {
    "total_scenes_processed": 243,
    "unique_teams_detected": 14,
    "expected_teams_found": 14,
    "validated_detections": 486,
    "unexpected_detections": 2
  }
}
```

## Success Criteria
- [ ] OCR command runs without crashing
- [ ] Output JSON file created successfully
- [ ] JSON is valid (no syntax errors)
- [ ] At least some teams detected (not all empty results)
- [ ] Scene filtering reduced 810 to reasonable number (100-400 scenes)
- [ ] Summary statistics look plausible
- [ ] Processing completed in reasonable time (<1 hour)

## Expected Performance

Based on setup:
- **GPU available**: 810 frames → 100-300 filtered → ~10-30 min processing
- **CPU only**: 810 frames → 100-300 filtered → ~30-60 min processing
- **Scene filtering**: Should reduce to ~20-50% of original scenes

## Estimated Time
45-75 min total:
- Setup verification: 5-10 min
- Processing time: 10-60 min (depends on GPU and filtering)
- Output review: 10-15 min
- Quality check: 10-15 min
- Documentation: 10-15 min

## Troubleshooting

### Error: "Episode not found in manifest"
- Check episode_id matches exactly what's in `data/episodes/episode_manifest.json`
- Ensure manifest file was created in 009a

### Error: "CUDA not available" or GPU warnings
- EasyOCR will fall back to CPU (slower but works)
- Update config: `ocr.gpu: false`

### Error: "Could not load frame"
- Check frame paths in scenes JSON are correct
- Verify frames directory has all images

### Processing takes >1 hour
- Check scene filtering is working (should reduce scenes significantly)
- Consider increasing `min_scene_duration` in config to filter more aggressively
- Check GPU is being used (look for CUDA messages in logs)

### No teams detected (all results empty)
- Check OCR regions in config match actual frame resolution
- Verify frame images show team graphics
- Test OCR reader manually on sample frame (from 009b)

## Output Files
- `data/cache/motd_2025-26_2025-11-01/ocr_results.json` (OCR output)
- Logs showing processing progress

## Notes to Capture for 009g

During this task, note:
- Which scenes had successful team detection
- Which scenes had no teams detected (why?)
- Any unexpected teams detected
- Confidence score distribution (mostly high? mostly low?)
- Which region (scoreboard vs formation) had better results
- Processing time per scene (for future optimization)

## Next Task
[009g-validate-and-tune.md](009g-validate-and-tune.md) - Manual validation and accuracy tuning
