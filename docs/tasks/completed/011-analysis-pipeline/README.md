# Task 011: Analysis Pipeline - Running Order Detection

> **Last reviewed:** 2025-12-18

## Summary

Implemented running order detection using multi-strategy approach with cross-validation. Achieved 100% accuracy on test episodes.

## Approach

1. **Reconnaissance** - Analysed data relationships between scenes, OCR, and transcript
2. **OCR region calibration** - Adjusted for 1280x720 resolution
3. **Frame extraction fix** - Fixed serialization bug, reduced interval to 2.0s
4. **Running order detector** - 2-strategy detection with cross-validation

## Key Decisions

- **Strategic pivot** - From sequential scene classification to multi-strategy detection
- **Two-strategy approach:**
  - Scoreboard appearance order (386 detections, most abundant)
  - FT graphic appearance order (7 deduplicated, most reliable)
- **Pydantic models** - Type-safe `MatchBoundary` and `RunningOrderResult`
- **Dependency injection** - Detector takes data, not file paths

## Results

- Episode 01: 7/7 matches detected (100% accuracy)
- 100% consensus between both strategies
- 18 unit tests passing
- Production code with TDD methodology
