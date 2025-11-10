# Task 008c: Validate and Tune Scene Detection

## Objective
Manually validate scene detection results and tune parameters for optimal accuracy.

## Prerequisites
- [008b-test-on-video.md](008b-test-on-video.md) completed
- scenes.json and extracted frames available

## Steps

### 1. Manual Validation
Open the video alongside the scenes.json file and verify:
- Do detected scene transitions align with actual transitions?
- Are major segments captured (studio intro, each match highlights, analysis)?
- Are there obvious missed transitions?
- Are there false positives (scenes detected mid-highlight)?

Sample 10-15 scenes across the video timeline:
- Start (studio intro)
- Middle (various matches)
- End (final analysis/credits)

### 2. Calculate Accuracy Metrics
Count:
- True positives: Correct scene transitions detected
- False positives: Transitions detected that aren't real
- False negatives: Real transitions missed

Target accuracy: >85% of major transitions detected with <15% false positives

### 3. Tune Threshold If Needed

**If too few scenes (<20) or missing transitions:**
- Lower threshold: Try 25.0 or 20.0
- Re-run: `python -m motd_analyzer detect-scenes ... --threshold 25.0`

**If too many scenes (>200) or excessive false positives:**
- Raise threshold: Try 35.0 or 40.0
- Re-run: `python -m motd_analyzer detect-scenes ... --threshold 35.0`

**Iterate until optimal:**
- Find threshold that captures major transitions
- Minimizes false positives
- Typical sweet spot: 27.0-32.0 for MOTD videos

### 4. Update Default Config
Once you find the optimal threshold, update `config/config.yaml`:
```yaml
scene_detection:
  threshold: 30.0  # Update to your optimal value
  method: "ContentDetector"
```

### 5. Document Findings
In the task file, note:
- Final threshold value used
- Scene count for test video
- Estimated accuracy percentage
- Any edge cases or issues discovered

## Validation Checklist
- [ ] Manual validation completed on 10-15 scenes
- [ ] Scene count is reasonable (40-80 for 90-min video)
- [ ] Major transitions (studio/highlights/analysis) captured
- [ ] False positive rate is acceptable (<15%)
- [ ] Optimal threshold determined and documented
- [ ] config.yaml updated with best threshold
- [ ] Single-frame extraction confirmed working

## Success Criteria
- Scene detection captures >85% of major segment transitions
- False positive rate <15%
- Results are reproducible and consistent

## Notes
- **Multi-frame extraction**: Currently using single frame per scene (num_frames=1). Multi-frame support (2-3 frames per scene) is available in the frame extractor if OCR accuracy in Task 009 is <90%. See [../completed/007-implement-frame-extractor/README.md](../completed/007-implement-frame-extractor/README.md) for implementation details.
- Some minor transitions within highlights are acceptable misses
- Studio-to-highlights and highlights-to-studio transitions are most critical
- Interview segments may be harder to detect if visually similar to analysis

## Estimated Time
30-45 minutes

## Next Task
Once validated, Task 008 is complete. Mark the epic as done and proceed to:
[009-ocr-implementation](../009-ocr-implementation/README.md)
