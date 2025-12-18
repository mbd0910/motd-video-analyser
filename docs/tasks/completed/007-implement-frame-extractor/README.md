# Task 007: Implement Frame Extractor

> **Last reviewed:** 2025-12-18

## Summary

Created module to extract key frames at scene transitions for OCR processing.

## Approach

- Uses OpenCV to seek to timestamp and extract frame
- Saves as JPEG with configurable quality
- Supports start/middle/end extraction positions
- Optional multi-frame extraction per scene (for OCR fallback)

## Key Decisions

- **Single frame per scene as default** - Multi-frame only if OCR accuracy <90%
- **JPEG quality 95** - Balance of quality and file size
- **Start position default** - Scoreboards typically visible early in highlights

## Outcome

`src/motd/scene_detection/frame_extractor.py` - Extracts frames for downstream OCR processing.
