# Task 014: Batch Processing All Episodes (Epic)

## Objective
Process all 10 MOTD episodes from the 2025/26 season.

## Prerequisites
- [013-refinement-tuning.md](013-refinement-tuning.md) completed
- Pipeline validated and tuned on test video
- All 10 MOTD videos downloaded to `data/videos/`

## Epic Overview
Split into sub-tasks:
1. Implement batch processing CLI command
2. Run batch process (overnight)
3. Spot-check results
4. Aggregate data for analysis

## Key Deliverables

### Batch CLI Command
```bash
python -m motd_analyzer batch \
  data/videos/*.mp4 \
  --output-dir data/output
```

Should process all videos sequentially, using cached results where available.

### Progress Monitoring
Add progress indicators:
- Current video being processed
- Current stage (scene detection, OCR, transcription, analysis)
- Estimated time remaining

## Execution Plan

### Night Before
1. Ensure all 10 videos are downloaded
2. Verify pipeline config is finalized
3. Start batch process before bed:
   ```bash
   python -m motd_analyzer batch data/videos/*.mp4 --output-dir data/output
   ```

### Next Morning
1. Check logs for any errors
2. Spot-check 2-3 random output files
3. If all looks good, proceed to analysis

## Success Criteria
- [ ] All 10 episodes processed successfully
- [ ] No major errors in logs
- [ ] Spot-checked outputs look reasonable
- [ ] All JSON files are well-formed

## Estimated Time
- Setup: 1-2 hours
- Processing: 8-12 hours (overnight)
- Validation: 30-60 minutes

## Troubleshooting
If batch processing fails:
- Check logs/pipeline.log for errors
- Re-run failed videos individually
- Adjust config if systematic issues found

## Reference
See [roadmap.md Phase 7](../roadmap.md#phase-7-batch-processing-est-2-4-hours)

## Next Task
[015-documentation-blog-prep.md](015-documentation-blog-prep.md)
