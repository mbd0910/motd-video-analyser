# Task 012: Match Boundary Detection

> **Last reviewed:** 2025-12-18

## Summary

Wired running order detector into pipeline and implemented transcript-based boundary detection. Produces complete match segments with three-part structure.

## Approach

1. **Match start detection** - Dual-strategy (venue + clustering) with cross-validation
2. **Match end detection** - Keyword + team mention validation
3. **Edge case handling** - BBC interludes, table reviews, alternate team names

## Key Decisions

- **Three segments per match:**
  - Studio Intro (`match_start` → `highlights_start`)
  - Highlights (`highlights_start` → `highlights_end`)
  - Post-Match (`highlights_end` → `match_end`)
- **Dual-signal boundary detection** - More reliable than single strategy
- **Interlude handling** - Detect "MOTD 2" keywords with team mention validation

## Results

- Episode 01: 7/7 matches (100% accuracy), ±1.27s average error
- Episode 02: 5/5 matches detected
- 58 running order tests + 14 CLI output tests passing
- CLI command: `python -m motd analyze-running-order <episode_id>`
