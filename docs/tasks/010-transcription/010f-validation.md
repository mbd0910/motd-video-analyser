# Task 010f: Validate Transcription Accuracy

## Status
⏳ Not Started

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
- [ ] Open transcript.json from Task 010e
- [ ] Open video file in player (VLC, QuickTime, etc.)
- [ ] Create validation spreadsheet or document template
- [ ] Note total segment count from transcript

### 2. Select Validation Sample
- [ ] Choose 15-20 segments strategically:
  - 3-5 from intro/outro (studio segments)
  - 3-5 from match highlights (commentary)
  - 3-5 from post-match analysis (pundit discussion)
  - 3-5 from random timestamps (ensure variety)
- [ ] Record segment IDs and timestamps for each sample
- [ ] Aim for coverage across entire video duration

### 3. Validate Each Sample Segment

For each selected segment:

#### 3.1 Navigate to Timestamp
- [ ] Use segment `start` time to seek in video player
- [ ] Play from start to end time
- [ ] Listen carefully to actual audio

#### 3.2 Compare Transcript to Audio
- [ ] Read transcript text while listening
- [ ] Note any differences:
  - Incorrect words
  - Missing words
  - Extra words (hallucinations)
  - Garbled text
- [ ] Rate accuracy: Perfect / Good (1-2 errors) / Poor (3+ errors)

#### 3.3 Check Critical Elements
- [ ] Team names (if mentioned): Correct? Y/N
- [ ] Pundit names (if mentioned): Correct? Y/N
- [ ] Player names (if mentioned): Correct? Y/N
- [ ] Timestamp alignment: Within ±1 second? Y/N

#### 3.4 Check Word-Level Timestamps (Sample)
- [ ] Pick 1-2 segments with word timestamps
- [ ] Verify individual word start times align with speech
- [ ] Note if word boundaries are reasonable

### 4. Calculate Accuracy Metrics

- [ ] Count segments by accuracy rating:
  - Perfect: ___ / 15-20
  - Good: ___ / 15-20
  - Poor: ___ / 15-20
- [ ] Calculate overall accuracy: (Perfect + Good) / Total × 100%
- [ ] Count critical element errors:
  - Team name errors: ___ / opportunities
  - Pundit name errors: ___ / opportunities
  - Timestamp errors (>1s off): ___ / samples

### 5. Document Systematic Errors

Look for patterns in errors:
- [ ] Specific team names consistently wrong?
- [ ] Specific pundit names consistently wrong?
- [ ] Accents causing issues? (e.g., Scottish, Irish commentators)
- [ ] Technical terms wrong? (football terminology)
- [ ] Low-quality audio sections (crowd noise, overlapping speech)?

### 6. Test Edge Cases

If test video includes these, validate:
- [ ] Team names with similar sounds (e.g., "City" vs "United")
- [ ] Player names (often non-English surnames)
- [ ] Fast-paced commentary (exciting moments)
- [ ] Multiple speakers overlapping
- [ ] Background crowd noise during play

### 7. Create Validation Report
- [ ] Create `docs/validation/010f_accuracy_validation.md`
- [ ] Include:
  - Validation methodology (sample size, selection strategy)
  - Overall accuracy metrics
  - Critical element accuracy (team names, pundit names, timestamps)
  - Examples of errors found
  - Systematic error patterns
  - Recommendation (meets >95% target? proceed or tune?)

### 8. Decision Point: Pass or Tune?

**If accuracy ≥95% on critical elements:**
- [ ] Mark task complete
- [ ] Document as passing validation
- [ ] Proceed to Task 011

**If accuracy <95% on critical elements:**
- [ ] Document specific issues
- [ ] Consider tuning options:
  - Try different model size (large-v3 vs large-v2)
  - Adjust VAD (Voice Activity Detection) parameters
  - Pre-process audio (noise reduction)
  - Add custom vocabulary (team/player names)
- [ ] Consult user on next steps (tune vs accept current accuracy)

## Validation Checklist

Before marking this task complete, verify:

- ✅ 15-20 segments validated across video duration
- ✅ Coverage includes intro, highlights, analysis, random samples
- ✅ Each segment compared to actual audio
- ✅ Team names accuracy checked
- ✅ Pundit names accuracy checked
- ✅ Timestamp accuracy checked (±1 second)
- ✅ Overall accuracy calculated
- ✅ Systematic errors documented
- ✅ Validation report created
- ✅ Decision made: pass (≥95%) or tune (<95%)

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
