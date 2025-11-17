# Task 010f: Validate Transcription Accuracy

## Status
✅ Complete (Conditional Pass - 2025-11-16)

## Objective
Manually validate transcription accuracy by comparing transcript segments to actual video audio, with focus on elements critical for downstream analysis: team names, pundit names, and timestamp accuracy.

## Prerequisites
- Task 010e (Execution) completed
- Transcript generated for full test video
- Video player available for playback

## Why This Phase Matters
**We're validating the inputs to downstream analysis**, not academic perfection.

The transcript will be used to:
1. Detect first team mentioned in studio analysis
2. Identify speaker changes (commentary vs pundit)
3. Extract team names from speech (backup for OCR)

Therefore, accuracy that matters:
- ✅ Team names correct ("Manchester United" not "Manchester You Knighted")
- ✅ Pundit names correct ("Gary Neville" not "Gary Nevel")
- ✅ Timestamps accurate (±1 second) for segment alignment
- ✅ Overall intelligibility (can understand what was said)

Less critical:
- ❌ Perfect filler words ("um", "uh", "you know")
- ❌ Exact pronunciation details
- ❌ Background crowd noise

**Target:** >95% accuracy on sampled segments for critical elements.

## Tasks

### 1. Preparation
- [x] Open transcript.json from Task 010e
- [x] Open video file in player (VLC, QuickTime, etc.)
- [x] Create validation spreadsheet or document template
- [x] Note total segment count from transcript (1,773 segments)

### 2. Select Validation Sample
- [x] Choose 15-20 segments strategically (selected 20):
  - 2 from intro (including "Match of the Dead")
  - 2 from outro (including lowest confidence "Goodnight")
  - 8 from studio analysis/commentary with team mentions
  - 3 from segments with pundit/commentator names
  - 3 from segments with player names
  - 2 from low confidence segments (<0.8 probability)
- [x] Record segment IDs and timestamps for each sample
- [x] Aim for coverage across entire video duration (0:00 → 1:23:34)

### 3. Validate Each Sample Segment

For each selected segment:

#### 3.1 Navigate to Timestamp
- [x] Use segment `start` time to seek in video player
- [x] Play from start to end time
- [x] Listen carefully to actual audio

#### 3.2 Compare Transcript to Audio
- [x] Read transcript text while listening
- [x] Note any differences:
  - Incorrect words
  - Missing words
  - Extra words (hallucinations)
  - Garbled text
- [x] Rate accuracy: Perfect / Good (1-2 errors) / Poor (3+ errors)

#### 3.3 Check Critical Elements
- [x] Team names (if mentioned): Correct? Y/N
- [x] Pundit names (if mentioned): Correct? Y/N
- [x] Player names (if mentioned): Correct? Y/N
- [x] Timestamp alignment: Within ±1 second? Y/N

#### 3.4 Check Word-Level Timestamps (Sample)
- [x] Pick 1-2 segments with word timestamps
- [x] Verify individual word start times align with speech
- [x] Note if word boundaries are reasonable

### 4. Calculate Accuracy Metrics

- [x] Count segments by accuracy rating:
  - Perfect: 12 / 20 (60%)
  - Good: 8 / 20 (40%)
  - Poor: 0 / 20 (0%)
- [x] Calculate overall accuracy: (Perfect + Good) / Total × 100% = 100%
- [x] Count critical element errors:
  - Team name errors: 0 / 8 (100% accuracy)
  - Pundit name errors: 0 / 2 (100% accuracy)
  - Player name errors: 3 / 4 (25% accuracy - non-critical)
  - Timestamp errors (>1s off): 0 / 20 (100% accuracy)

### 5. Document Systematic Errors

Look for patterns in errors:
- [x] Specific team names consistently wrong? NO - 100% accuracy
- [x] Specific pundit names consistently wrong? NO - 100% accuracy
- [x] Accents causing issues? NO - handled well
- [x] Technical terms wrong? Minimal (1 grammar error: dominant vs dominance)
- [x] Low-quality audio sections? Identified low confidence segments, validated
- [x] Player names: Phonetic spelling of foreign surnames (Gravenberch, Caicedo, Fernández)

### 6. Test Edge Cases

If test video includes these, validate:
- [x] Team names with similar sounds (e.g., "City" vs "United") - handled correctly
- [x] Player names (often non-English surnames) - phonetic spelling errors identified
- [x] Fast-paced commentary (exciting moments) - validated
- [x] Multiple speakers overlapping - validated
- [x] Background crowd noise during play - no issues

### 7. Create Validation Report
- [x] Create `docs/validation/010f_accuracy_validation.md`
- [x] Include:
  - Validation methodology (sample size, selection strategy)
  - Overall accuracy metrics
  - Critical element accuracy (team names, pundit names, timestamps)
  - Examples of errors found
  - Systematic error patterns
  - Recommendation (meets >95% target? proceed or tune?)

### 8. Decision Point: Pass or Tune?

**If accuracy ≥95% on critical elements:**
- [x] Mark task complete
- [x] Document as passing validation (CONDITIONAL PASS)
- [x] Proceed to Task 011

**Result:** CONDITIONAL PASS
- Team names: 100% ✅
- Pundit names: 100% ✅
- Timestamps: 100% ✅
- Player names: 25% (non-critical for use case)

## Validation Checklist

Before marking this task complete, verify:

- [x] 15-20 segments validated across video duration (20 segments)
- [x] Coverage includes intro, highlights, analysis, random samples
- [x] Each segment compared to actual audio
- [x] Team names accuracy checked (100% - 8/8 correct)
- [x] Pundit names accuracy checked (100% - 2/2 correct)
- [x] Timestamp accuracy checked (100% - 20/20 within ±1 second)
- [x] Overall accuracy calculated (100% Good or Perfect)
- [x] Systematic errors documented (player name phonetic spelling)
- [x] Validation report created (`docs/validation/010f_accuracy_validation.md`)
- [x] Decision made: CONDITIONAL PASS - proceed to Task 011
- [x] Future enhancement documented (`docs/future-enhancements.md`)

## Expected Output

**File created:**
- `docs/validation/010f_accuracy_validation.md`

**Example validation report:**
```markdown
# Transcription Accuracy Validation - Task 010f

**Date:** 2025-11-13
**Test Video:** data/videos/motd_2025-11-01.mp4
**Transcript:** data/cache/motd_2025-11-01/transcript.json
**Model:** faster-whisper large-v3

## Methodology

- **Sample Size:** 18 segments
- **Selection:** Stratified across intro (4), highlights (5), analysis (5), random (4)
- **Validation Method:** Manual comparison (listen + read)

## Overall Accuracy

| Rating | Count | Percentage |
|--------|-------|------------|
| Perfect (0 errors) | 14 | 77.8% |
| Good (1-2 errors) | 3 | 16.7% |
| Poor (3+ errors) | 1 | 5.6% |

**Overall Accuracy:** 94.4% (17/18 Good or Perfect)

## Critical Element Accuracy

| Element | Opportunities | Errors | Accuracy |
|---------|---------------|--------|----------|
| Team names | 12 | 0 | 100% ✅ |
| Pundit names | 8 | 1 | 87.5% ⚠️ |
| Player names | 5 | 1 | 80% ⚠️ |
| Timestamps (±1s) | 18 | 0 | 100% ✅ |

## Error Examples

### Segment 127 (Good - 1 error)
- **Timestamp:** 23:45 - 23:52
- **Expected:** "Alan Shearer thinks Newcastle were unlucky"
- **Transcribed:** "Alan Shearer thinks Newcastle were unlocked"
- **Error:** "unlucky" → "unlocked" (minor, context clear)

### Segment 243 (Poor - 3 errors)
- **Timestamp:** 54:12 - 54:20
- **Expected:** "Bukayo Saka with a brilliant run down the right wing"
- **Transcribed:** "Bakayo Sacker with a brilliant run down the right wing"
- **Errors:** Player name mispronounced (critical for analysis)

### Segment 301 (Good - 1 error)
- **Timestamp:** 67:30 - 67:35
- **Expected:** "Micah Richards agrees with that assessment"
- **Transcribed:** "Mika Richards agrees with that assessment"
- **Error:** Pundit name slightly wrong (critical but recognizable)

## Systematic Error Patterns

1. **Non-English player names:** Occasional errors on surnames (e.g., Saka → Sacker)
2. **Pundit "Micah":** Transcribed as "Mika" twice (systematic)
3. **Fast commentary:** 1 segment with multiple errors during exciting goal
4. **Overall:** No major systematic issues, mostly isolated errors

## Recommendations

### ✅ Pass Validation (Conditional)

**Meets target on most metrics:**
- Team names: 100% ✅
- Timestamps: 100% ✅
- Overall intelligibility: 94.4%

**Below target on:**
- Pundit names: 87.5% (target: >95%)
- Player names: 80% (target: >95%)

**Recommendation:**
1. **Proceed to Task 011** with current model
2. **Add post-processing** in Task 011 to normalize known pundit names:
   - "Mika Richards" → "Micah Richards"
3. **Consider custom vocabulary** if player name errors become problematic
4. Current accuracy is sufficient for "first team mentioned" detection (our primary use case)

### Alternative: Tune Now (If Required)
- Try large-v3 with custom vocabulary (team/pundit names)
- Adjust VAD parameters for better speech detection
- Pre-process audio with noise reduction

**Decision:** Recommend proceeding (conditional pass) unless user requires perfect pundit/player names.
```

## Time Estimate
45-60 minutes

## Dependencies
- **Blocks:** Task 011 (transcript ready for analysis pipeline)
- **Blocked by:** 010e (need transcript to validate)

## Notes
- **Subjective assessment:** This is manual validation, not automated WER
- **Sample size:** 15-20 segments = ~5-10% of total (representative)
- **Focus on critical elements:** Team names most important, filler words least important
- **Conditional pass:** Minor errors acceptable if core use case (team detection) works
- **Tuning later:** Can refine in Task 013 if needed after full pipeline testing

## Troubleshooting

### Accuracy Lower Than Expected (<90%)
- Check audio quality (is original video audio clear?)
- Try larger model: large-v3 (if using smaller)
- Check for systematic issues (specific accents, terms)
- Consider audio pre-processing

### Timestamps Consistently Off (>2 seconds)
- Check video/audio sync in original file
- Verify audio extraction didn't shift timing
- Re-extract audio with --force flag

### Many Player Name Errors
- Expected for non-English surnames
- Can add custom vocabulary in Whisper config
- May not be critical if OCR provides team names

### Pundit Name Errors
- Add post-processing step to normalize known pundits
- Create mapping: common_errors → correct_names
- Most pundits are regular (Shearer, Neville, Richards, Wright)

## Reference
- [Task 009g - Validation](../../tasks/completed/009-ocr-implementation/009g-validation.md) (similar validation approach)
- [docs/prd.md - Accuracy Targets](../../prd.md)

## Next Task
After Task 010 complete: [Task 011: Analysis Pipeline Epic](../011-analysis-pipeline/README.md)
