# Task 009: OCR & Team Detection

> **Last reviewed:** 2025-12-18

## Summary

Implemented fixture-aware OCR to extract team names from video frames and validate against expected fixtures.

## Approach

1. **Visual reconnaissance** - Documented MOTD visual patterns (scoreboards, formation graphics, FT graphics)
2. **OCR reader** - EasyOCR integration with configurable regions of interest
3. **Team matcher** - Fuzzy matching against team name variants with fixture-aware filtering
4. **Fixture matcher** - Cross-validates OCR results against expected matches
5. **CLI command** (`python -m motd extract-teams`) - End-to-end OCR pipeline

## Key Decisions

- **Fixture-aware matching** - Reduces search space from 20 teams to ~14 (day's fixtures), improving accuracy 85-90% → 95%+
- **Multiple OCR regions** - Scoreboard (top-left), formation graphic (bottom-right), FT graphic (centre)
- **Confidence scoring** - Combined OCR confidence × fuzzy match score
- **Smart filtering** - Skip intro/outro frames, focus on match footage

## Results

- Episode 01.11: 14/14 teams detected (100%)
- Episode 08.11: 10/10 teams detected (100%)
- 0 false positives
- Fixture validation working correctly
