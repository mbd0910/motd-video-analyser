# Task 009a: MOTD Visual Pattern Reconnaissance

## Objective
Document recurring visual patterns in Match of the Day to guide OCR implementation with human domain knowledge.

## Prerequisites
- Task 008 completed (810 frames extracted from test video)
- Test video: `data/videos/motd_2025-26_2025-11-01.mp4`
- Auto-extracted frames: `data/cache/motd_2025-26_2025-11-01/frames/scene_*.jpg`

## Why This Task Matters
MOTD has a predictable, repeating structure week-to-week. By documenting these patterns once, we can:
- Optimize OCR to focus on high-quality frames (formation graphics)
- Skip irrelevant segments (intro, studio, transitions)
- Reduce 810 frames to ~100-200 relevant frames for processing
- Improve accuracy by targeting the right visual elements

## Tasks

### 1. Browse Test Video (10-15 min)
- [ ] Seek through `data/videos/motd_2025-26_2025-11-01.mp4`
- [ ] Note rough timecodes for:
  - [ ] Intro sequence end
  - [ ] Each match start time
  - [ ] Studio segments
  - [ ] Outro/credits start
- [ ] Fill in "Episode Timeline" section of template

### 2. Browse Auto-Extracted Frames (30-45 min)
- [ ] Open folder: `data/cache/motd_2025-26_2025-11-01/frames/`
- [ ] Browse through the 810 scene images
- [ ] Identify and note scene numbers showing:
  - [ ] Formation graphics (team lineups during walkouts)
  - [ ] Scoreboard graphics (top-left during match play)
  - [ ] Studio segments (presenters at desk)
  - [ ] Intro/outro sequences
  - [ ] Transitions between segments
- [ ] Screenshot or note 2-3 examples of each pattern type

### 3. Complete Documentation Template (15-30 min)
- [ ] Fill in all sections of `docs/motd_visual_patterns.md`:
  - [ ] Episode timeline table
  - [ ] Formation graphics section (with scene examples)
  - [ ] Scoreboard graphics section (with scene examples)
  - [ ] Studio segments section (with scene examples)
  - [ ] Transition patterns
  - [ ] OCR implementation recommendations
  - [ ] Answer questions section
- [ ] Take manual screenshots only if critical patterns missing from auto-frames

### 4. Create Episode Manifest (10-15 min)
- [ ] Create `data/episodes/episode_manifest.json`
- [ ] Link episode `motd_2025-26_2025-11-01` to expected match_ids from fixtures
- [ ] Use the 7 matches from `data/fixtures/premier_league_2025_26.json` for 2025-11-01:
  - Brighton vs Leeds
  - Burnley vs Arsenal
  - Crystal Palace vs Brentford
  - Fulham vs Wolves
  - Forest vs Man Utd
  - Tottenham vs Chelsea
  - Liverpool vs Aston Villa

## Episode Manifest Structure

Create `data/episodes/episode_manifest.json`:
```json
{
  "episodes": [
    {
      "episode_id": "motd_2025-26_2025-11-01",
      "broadcast_date": "2025-11-01",
      "video_path": "data/videos/motd_2025-26_2025-11-01.mp4",
      "expected_matches": [
        "2025-11-01-brighton-leeds",
        "2025-11-01-burnley-arsenal",
        "2025-11-01-palace-brentford",
        "2025-11-01-fulham-wolves",
        "2025-11-01-forest-manutd",
        "2025-11-01-tottenham-chelsea",
        "2025-11-01-liverpool-villa"
      ],
      "notes": "Opening weekend of 2025-26 season"
    }
  ]
}
```

**Note:** The `match_id` format should match what's in `data/fixtures/premier_league_2025_26.json`.

## Success Criteria
- [ ] `docs/motd_visual_patterns.md` fully completed with all sections filled in
- [ ] At least 2-3 frame examples identified for formation graphics
- [ ] At least 2-3 frame examples identified for scoreboard graphics
- [ ] Episode timeline table shows all major segments with timecodes
- [ ] OCR recommendations section provides clear filtering strategy
- [ ] Questions section answered based on observations
- [ ] `data/episodes/episode_manifest.json` created and links episode to 7 expected matches
- [ ] Episode manifest JSON is valid (no syntax errors)

## Estimated Time
1-1.5 hours total:
- Video scan: 10-15 min
- Frame browsing: 30-45 min
- Documentation: 15-30 min
- Episode manifest: 10-15 min

## Tips
- **Use auto-extracted frames as primary reference** - they're what OCR will process
- **Don't spend too long on perfection** - rough documentation is fine, we'll iterate
- **Focus on formation graphics** - they're the highest quality for team detection
- **Note any surprises** - unexpected graphics, team name formats, etc.

## Output Files
- `docs/motd_visual_patterns.md` (completed from template)
- `data/episodes/episode_manifest.json` (new file)

## Next Task
[009b-implement-ocr-reader.md](009b-implement-ocr-reader.md) - OCR reader implementation guided by pattern documentation
