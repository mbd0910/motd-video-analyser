# Task 008: Scene Detection Testing

> **Last reviewed:** 2025-12-18

## Summary

Created CLI command for scene detection and validated on first MOTD video.

## Approach

1. **CLI command** (`python -m motd detect-scenes`) - Accepts video path, threshold, output path
2. **Test on video** - Ran on `motd_2025-26_2025-11-01.mp4`
3. **Validation** - Manual review of detected scenes vs actual transitions

## Key Decisions

- **Threshold 27.0** - Tuned from default 30.0 for better capture of walkout sequences
- **810 scenes detected** - More than expected (40-80) due to low threshold capturing formation graphics
- **Smart filtering needed** - Identified need for downstream filtering in OCR stage

## Results

- Scene detection CLI working
- Frames extracted to `data/cache/{episode_id}/frames/`
- JSON output with timestamps and frame paths
- Validated: detected scenes match actual transitions
