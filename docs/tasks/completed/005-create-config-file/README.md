# Task 005: Create Configuration File

> **Last reviewed:** 2025-12-18

## Summary

Created `config/config.yaml` with all pipeline parameters.

## Approach

Centralised configuration for:
- Scene detection (threshold, min duration)
- OCR (regions, confidence threshold, GPU settings)
- Transcription (model size, language, timestamps)
- Caching and output settings

## Key Decisions

- **YAML format** - Human-readable, easy to edit
- **OCR regions configurable** - Needs adjustment per video resolution
- **Caching enabled by default** - Critical for expensive operations like Whisper

## Outcome

Single source of truth for pipeline configuration at `config/config.yaml`.
