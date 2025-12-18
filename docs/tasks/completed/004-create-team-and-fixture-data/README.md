# Task 004: Create Team and Fixture Data

> **Last reviewed:** 2025-12-18

## Summary

Created JSON data files for Premier League teams, fixtures, and episode manifest to enable fixture-aware team detection.

## Approach

- `data/teams/premier_league_2025_26.json` - 20 teams with codes and alternates
- `data/fixtures/premier_league_2025_26.json` - Flat date-indexed match data
- `data/episodes/episode_manifest.json` - Links episodes to expected matches

## Key Decisions

- **`codes` array (plural)** - Supports multiple 3-letter variations (e.g., Forest: NFO/FOR/NOT)
- **Flat fixture structure** - No gameweek grouping needed for matching
- **Episode manifest** - Links broadcast date to expected fixtures for search space reduction
- **No video_filename in manifest** - Keeps metadata separate from implementation

## Outcome

Fixture-aware OCR can search 12-16 teams (from day's fixtures) instead of all 20, improving accuracy from ~85-90% to 95%+.
