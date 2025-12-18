# Task 003: Install Python Dependencies

> **Last reviewed:** 2025-12-18

## Summary

Created requirements.txt and installed all Python dependencies for the pipeline.

## Approach

- Core: OpenCV, NumPy, PyYAML
- Scene detection: PySceneDetect
- OCR: EasyOCR with PyTorch
- Transcription: faster-whisper (NOT openai-whisper - 4x faster)
- Testing: pytest, pytest-cov

## Key Decisions

- **faster-whisper over openai-whisper** - 3-4 mins vs 10-15 mins per 90-min video
- **EasyOCR over Tesseract** - Better accuracy on sports graphics
- **PyTorch with MPS support** - GPU acceleration on Apple Silicon

## Outcome

All dependencies installed, imports verified working.
