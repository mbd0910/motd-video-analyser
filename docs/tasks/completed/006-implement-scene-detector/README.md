# Task 006: Implement Scene Detector

> **Last reviewed:** 2025-12-18

## Summary

Created scene detection module using PySceneDetect to identify transitions in MOTD videos.

## Approach

- Integrated PySceneDetect's ContentDetector for frame-to-frame comparison
- Returns scene boundaries with timestamps, frame numbers, and duration
- Supports both Content (hard cuts) and Adaptive (fades) detectors

## Key Decisions

- **ContentDetector as default** - BBC MOTD uses mostly hard cuts
- **Threshold 30.0 default** - Tunable via config, lower = more sensitive
- **Min scene duration 3.0s** - Prevents very short false positives

## Outcome

`src/motd/scene_detection/detector.py` - Detects 40-80 scenes for typical 90-min episode.
