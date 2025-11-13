# Task 010c: Implement Whisper Transcriber

## Status
⏳ Not Started

## Objective
Create a transcription module using faster-whisper (NOT openai-whisper) that generates word-level timestamps for speech in MOTD videos.

## Prerequisites
- Task 010b (Audio Extractor) completed
- Audio extraction tested and working

## Why This Phase Matters
**Critical Library Choice:** This project uses **faster-whisper**, NOT the standard openai-whisper library.

**Why faster-whisper?**
- 4x faster processing (3-4 min vs 10-15 min per 90-min video)
- Identical accuracy to openai-whisper
- GPU-accelerated with CTranslate2
- Lower memory usage

**Why word-level timestamps?**
- Needed to detect "first team mentioned" in analysis segments
- Enables precise alignment with video segments
- Supports validation (check what was said at specific time)

## Tasks

### 1. Install faster-whisper
- [ ] Verify faster-whisper in requirements.txt (should be from Task 001)
- [ ] If not present, add: `faster-whisper==1.0.1` (or latest)
- [ ] Install: `pip install faster-whisper`
- [ ] Verify GPU support (if available):
  ```python
  import torch
  print(torch.cuda.is_available())  # Should print True if GPU available
  ```

### 2. Create Module Structure
- [ ] Create file: `src/motd/transcription/whisper_transcriber.py`
- [ ] Add module docstring

### 3. Implement WhisperTranscriber Class
- [ ] Create `WhisperTranscriber` class
- [ ] Add `__init__(self, config: dict)` method:
  - Model size (default: "large-v3" for best accuracy)
  - Device (default: "auto" - use GPU if available, else CPU)
  - Compute type (default: "float16" for GPU, "int8" for CPU)
  - Language (default: "en" for English)
- [ ] Initialize faster-whisper model in __init__
- [ ] Handle model download on first run (~3GB download)

### 4. Implement Transcription Method
- [ ] Add `transcribe(self, audio_path: str) -> dict` method
- [ ] Call model.transcribe() with word timestamps enabled:
  ```python
  segments, info = model.transcribe(
      audio_path,
      language="en",
      word_timestamps=True,
      vad_filter=True  # Voice Activity Detection - improves accuracy
  )
  ```
- [ ] Return structured result with segments and word-level data

### 5. Process Whisper Output
- [ ] Convert generator to list (segments is generator)
- [ ] Extract for each segment:
  - Text content
  - Start time (seconds)
  - End time (seconds)
  - Words array (each with: word, start, end, probability)
- [ ] Build output dict matching schema:
  ```python
  {
      "language": "en",
      "duration": 5400.2,
      "segments": [
          {
              "id": 0,
              "text": "Welcome to Match of the Day.",
              "start": 12.5,
              "end": 15.2,
              "words": [
                  {"word": "Welcome", "start": 12.5, "end": 12.8, "probability": 0.98},
                  {"word": "to", "start": 12.8, "end": 12.9, "probability": 0.99},
                  ...
              ]
          },
          ...
      ]
  }
  ```

### 6. Add GPU/CPU Configuration
- [ ] Read device preference from config.yaml:
  ```yaml
  transcription:
    device: "auto"  # or "cuda" or "cpu"
    compute_type: "float16"  # or "int8"
    model_size: "large-v3"
  ```
- [ ] Auto-detect GPU and fall back to CPU gracefully
- [ ] Log which device is being used
- [ ] Warn if using CPU (much slower but still works)

### 7. Add Progress Logging
- [ ] Log model loading (first time = download)
- [ ] Log transcription start (audio duration)
- [ ] Log transcription progress (if possible)
- [ ] Log transcription complete (processing time)
- [ ] Log performance metrics (real-time factor: duration/processing_time)

### 8. Add Error Handling
- [ ] Handle missing audio file
- [ ] Handle corrupted audio file
- [ ] Handle out-of-memory errors (suggest smaller model or CPU)
- [ ] Handle model download failures
- [ ] Validate output has segments

### 9. Test on Short Sample
- [ ] Create test script to transcribe 30-second sample from 010a
- [ ] Verify model downloads correctly (~3GB, one-time)
- [ ] Verify transcription accuracy (read output)
- [ ] Verify word timestamps are present
- [ ] Check processing time (should be near real-time or faster with GPU)

### 10. Code Quality Check
- [ ] Follow Python style guidelines (type hints, docstrings)
- [ ] Configuration from config.yaml supported
- [ ] Error messages are clear
- [ ] Logging is informative

## Validation Checklist

Before marking this task complete, verify:

- ✅ Module created at `src/motd/transcription/whisper_transcriber.py`
- ✅ WhisperTranscriber class implemented
- ✅ faster-whisper model loads successfully
- ✅ Model downloads automatically on first run (~3GB)
- ✅ GPU acceleration detected and used (if available)
- ✅ Word-level timestamps present in output
- ✅ Sample transcription accurate (>95% subjective)
- ✅ Processing is fast (near real-time with GPU)
- ✅ Code follows Python guidelines
- ✅ Error handling works

## Expected Output

**Files created:**
- `src/motd/transcription/whisper_transcriber.py`

**Example usage:**
```python
from motd.transcription.whisper_transcriber import WhisperTranscriber

config = {
    "model_size": "large-v3",
    "device": "auto",
    "language": "en"
}

transcriber = WhisperTranscriber(config)
result = transcriber.transcribe("data/cache/audio.wav")

print(f"Transcribed {len(result['segments'])} segments")
print(f"First segment: {result['segments'][0]['text']}")
print(f"Duration: {result['duration']}s")

# Check word timestamps
first_words = result['segments'][0]['words']
print(f"First word: '{first_words[0]['word']}' at {first_words[0]['start']}s")
```

## Example Implementation Outline

```python
"""Whisper transcription module for MOTD audio analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using faster-whisper with word timestamps."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Whisper transcriber.

        Args:
            config: Optional configuration dict with:
                - model_size: Model size (default: "large-v3")
                - device: Device to use (default: "auto")
                - compute_type: Compute type (default: "float16")
                - language: Language code (default: "en")
        """
        self.config = config or {}
        self.model_size = self.config.get("model_size", "large-v3")
        self.device = self.config.get("device", "auto")
        self.compute_type = self.config.get("compute_type", "float16")
        self.language = self.config.get("language", "en")

        logger.info(f"Loading Whisper model: {self.model_size}")
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type
        )
        logger.info(f"Model loaded on device: {self.device}")

    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file with word-level timestamps.

        Args:
            audio_path: Path to audio file (WAV format preferred)

        Returns:
            Dict with:
                - language: Detected language
                - duration: Audio duration in seconds
                - segments: List of transcribed segments with words

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        # Implementation here...
        pass

    def _process_segments(self, segments, info) -> Dict:
        """Convert Whisper segments to structured output."""
        pass
```

## Time Estimate
1-1.5 hours (includes model download time on first run)

## Dependencies
- **Blocks:** 010d (CLI needs working transcriber)
- **Blocked by:** 010b (need audio extraction)

## Notes
- **Model download:** First run downloads ~3GB (large-v3 model)
- **GPU vs CPU:** GPU is 10-15x faster but CPU still works (just slower)
- **Model size options:** base, small, medium, large-v2, large-v3 (larger = more accurate)
- **VAD filter:** Voice Activity Detection helps remove silence and improve accuracy
- **Alternative:** If faster-whisper has issues, fall back to Whisper API (cloud, costs ~$0.006/min)

## Performance Expectations
- **With GPU:** 3-4 minutes for 90-min video (25-30x real-time)
- **With CPU:** 15-20 minutes for 90-min video (4-6x real-time)
- **Accuracy:** >95% on clear speech (better than most humans on names/accents)

## Troubleshooting
- **Out of memory:** Try smaller model (large-v2, medium) or use CPU
- **Model download fails:** Check internet connection, try manual download
- **Slow processing:** Verify GPU is being used, check CUDA installation
- **Poor accuracy:** Check audio quality, try large-v3 model, adjust VAD parameters

## Reference
- [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper)
- [docs/roadmap.md - Phase 3: Audio Transcription](../../roadmap.md)
- [docs/tech-tradeoffs.md - Whisper comparison](../../tech-tradeoffs.md)

## Next Phase
[010d-cli-integration.md](010d-cli-integration.md) - Create CLI command for transcription
