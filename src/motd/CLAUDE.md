# src/motd

Main package for MOTD video analysis pipeline.

- `__main__.py` - CLI entry point (run with `python -m motd`)
- `config/` - Configuration loading and validation
- `llm/` - LLM prompt generation for Claude analysis
- `ocr/` - EasyOCR-based text extraction from video frames
- `pipeline/` - Orchestration of pipeline stages
- `scene_detection/` - PySceneDetect-based scene boundary detection
- `transcription/` - faster-whisper audio transcription
- `utils/` - Shared utilities
- `validation/` - Input/output validation
