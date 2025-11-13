# Task 010b: Implement Audio Extractor

## Status
⏳ Not Started

## Objective
Create a robust audio extraction module that converts video files to Whisper's optimal audio format (16kHz mono WAV) using ffmpeg.

## Prerequisites
- Task 010a (Audio Reconnaissance) completed
- Audio format documented and verified

## Why This Phase Matters
Whisper performs best with specific audio format:
- **16kHz sample rate** (Whisper's training data rate)
- **Mono channel** (reduces file size, no loss in quality for speech)
- **WAV format** (uncompressed, fast to process)

This module handles the conversion automatically, with proper error handling for edge cases.

## Tasks

### 1. Create Module Structure
- [ ] Create file: `src/motd/transcription/__init__.py` (if not exists)
- [ ] Create file: `src/motd/transcription/audio_extractor.py`
- [ ] Add module docstring explaining purpose

### 2. Implement AudioExtractor Class
- [ ] Create `AudioExtractor` class with configuration support
- [ ] Add `__init__(self, config: dict)` method:
  - Accept target sample rate (default: 16000)
  - Accept target channels (default: 1 for mono)
  - Accept output format (default: "wav")
- [ ] Add `extract(self, video_path: str, output_path: str) -> dict` method:
  - Validate video file exists
  - Run ffmpeg to extract audio
  - Return metadata (duration, file size, success status)

### 3. Implement ffmpeg Command Generation
- [ ] Build ffmpeg command with proper parameters:
  ```python
  cmd = [
      "ffmpeg",
      "-i", video_path,        # Input video
      "-vn",                    # No video
      "-ar", "16000",          # Sample rate 16kHz
      "-ac", "1",              # Mono channel
      "-acodec", "pcm_s16le",  # PCM 16-bit little-endian (WAV)
      "-y",                     # Overwrite output
      output_path
  ]
  ```
- [ ] Use subprocess to execute ffmpeg
- [ ] Capture stdout/stderr for error handling

### 4. Add Error Handling
- [ ] Check video file exists before extraction
- [ ] Raise clear error if ffmpeg not installed
- [ ] Raise clear error if video has no audio track
- [ ] Handle ffmpeg errors (corrupted file, unsupported codec)
- [ ] Validate output file was created successfully

### 5. Add Logging
- [ ] Log extraction start (video filename, size)
- [ ] Log extraction progress (if possible with ffmpeg stderr parsing)
- [ ] Log extraction complete (output size, duration)
- [ ] Log any warnings or errors

### 6. Add Duration Extraction
- [ ] Use ffprobe to get audio duration:
  ```python
  ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 input.mp4
  ```
- [ ] Return duration in metadata (useful for validation)

### 7. Write Unit Tests (Optional but Recommended)
- [ ] Create `tests/test_audio_extractor.py`
- [ ] Test: Extract audio from sample video
- [ ] Test: Error handling for missing file
- [ ] Test: Error handling for video without audio
- [ ] Mock ffmpeg calls if preferred

### 8. Manual Testing
- [ ] Test on test video from Task 009/010a
- [ ] Verify output file format (16kHz mono WAV)
- [ ] Verify file size is reasonable (~10MB per minute)
- [ ] Verify extraction time (<1 minute for 90-min video)
- [ ] Play output file to verify quality

### 9. Code Quality Check
- [ ] Follow Python style guidelines (type hints, docstrings)
- [ ] No hardcoded paths
- [ ] Configuration from config.yaml supported
- [ ] Error messages are helpful and actionable

## Validation Checklist

Before marking this task complete, verify:

- ✅ Module created at `src/motd/transcription/audio_extractor.py`
- ✅ AudioExtractor class implemented with extract() method
- ✅ Converts to 16kHz mono WAV correctly
- ✅ Error handling works (missing file, no audio track)
- ✅ Processing time <1 min for 90-min video
- ✅ Output file plays correctly
- ✅ Code follows Python guidelines (type hints, docstrings)
- ✅ Logging is clear and helpful
- ✅ Manual test on real video successful

## Expected Output

**Files created:**
- `src/motd/transcription/audio_extractor.py`
- `src/motd/transcription/__init__.py` (if not exists)
- `tests/test_audio_extractor.py` (optional)

**Example usage:**
```python
from motd.transcription.audio_extractor import AudioExtractor

extractor = AudioExtractor(config={"sample_rate": 16000})
result = extractor.extract(
    video_path="data/videos/motd_2025-11-01.mp4",
    output_path="data/cache/audio.wav"
)

print(result)
# {
#   "success": True,
#   "duration_seconds": 5400,
#   "output_size_mb": 54.2,
#   "sample_rate": 16000,
#   "channels": 1
# }
```

## Example Implementation Outline

```python
"""Audio extraction module for MOTD video analysis."""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extracts audio from video files in Whisper-optimal format."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize audio extractor.

        Args:
            config: Optional configuration dict with:
                - sample_rate: Target sample rate (default: 16000)
                - channels: Target channels (default: 1 for mono)
        """
        self.config = config or {}
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.channels = self.config.get("channels", 1)

    def extract(self, video_path: str, output_path: str) -> Dict:
        """Extract audio from video to WAV format.

        Args:
            video_path: Path to input video file
            output_path: Path to output audio file (WAV)

        Returns:
            Metadata dict with success status, duration, file size

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If ffmpeg extraction fails
        """
        # Implementation here...
        pass

    def _get_duration(self, video_path: str) -> float:
        """Get audio duration using ffprobe."""
        pass

    def _run_ffmpeg(self, video_path: str, output_path: str) -> None:
        """Execute ffmpeg command to extract audio."""
        pass
```

## Time Estimate
45-60 minutes

## Dependencies
- **Blocks:** 010c (transcriber needs audio files)
- **Blocked by:** 010a (need to know audio format)

## Notes
- ffmpeg must be installed (added in Task 001)
- WAV files are large (~10MB/min) but fast to process
- Could add MP3 output option later if disk space is concern
- Extraction is fast (<1 min) so caching not critical at this stage
- Use subprocess.run() with check=True for cleaner error handling

## Reference
- [docs/roadmap.md - Phase 3: Audio Transcription](../../roadmap.md)
- [docs/architecture.md - Transcription Module](../../architecture.md)

## Next Phase
[010c-whisper-transcriber.md](010c-whisper-transcriber.md) - Implement Whisper transcription
