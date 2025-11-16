"""Whisper transcription module for MOTD audio analysis.

This module uses faster-whisper (NOT openai-whisper) for 4x faster processing
with identical accuracy. Generates word-level timestamps for precise analysis.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using faster-whisper with word-level timestamps.

    Uses CTranslate2-optimised Whisper models for fast, accurate transcription.
    Automatically detects and uses GPU (CUDA/MPS) if available, falls back to CPU.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialise Whisper transcriber with configuration.

        Args:
            config: Optional configuration dict with:
                - model_size: Model size (default: "large-v3")
                - device: Device to use - "auto"/"cuda"/"mps"/"cpu" (default: "auto")
                - compute_type: Compute type (default: "float16" for GPU, "int8" for CPU)
                - language: Language code (default: "en")

        Raises:
            RuntimeError: If model loading fails
        """
        self.config = config or {}
        self.model_size = self.config.get("model_size", "large-v3")
        self.language = self.config.get("language", "en")

        # Determine device and compute type
        device_pref = self.config.get("device", "auto")
        device, compute_type = self._select_device_and_compute_type(device_pref)
        self.device = device
        self.compute_type = compute_type

        logger.info(
            f"Loading Whisper model '{self.model_size}' "
            f"(device={self.device}, compute={self.compute_type})"
        )
        logger.debug("Note: First run will download ~3GB model (one-time)")

        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info(f"✓ Model loaded successfully on {self.device}")
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}") from e

    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file with word-level timestamps.

        Args:
            audio_path: Path to audio file (16kHz mono WAV preferred)

        Returns:
            Dict with:
                - language: Detected/specified language code
                - duration: Audio duration in seconds
                - segment_count: Number of segments
                - segments: List of transcribed segments with word timestamps

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path.name}")
        logger.debug(f"Audio size: {audio_path.stat().st_size / (1024*1024):.1f} MB")

        start_time = time.time()

        try:
            segments_generator, info = self.model.transcribe(
                str(audio_path),
                language=self.language,
                word_timestamps=True,
                vad_filter=True,  # Voice Activity Detection - removes silence
            )

            # Process segments (generator → list with structured data)
            result = self._process_segments(segments_generator, info)

            elapsed = time.time() - start_time
            duration = result["duration"]
            rtf = duration / elapsed if elapsed > 0 else 0  # Real-time factor

            logger.info(
                f"✓ Transcribed {result['segment_count']} segments in {elapsed:.1f}s "
                f"(RTF: {rtf:.1f}x real-time)"
            )
            logger.debug(
                f"Language: {info.language} (probability: {info.language_probability:.2f})"
            )

            return result

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}") from e

    def _process_segments(self, segments_generator, info) -> Dict:
        """Convert Whisper segments generator to structured output.

        Args:
            segments_generator: Generator of TranscriptionSegment objects
            info: TranscriptionInfo object with metadata

        Returns:
            Dict with structured segments and metadata
        """
        segments_list = []

        for seg_id, segment in enumerate(segments_generator):
            # Extract word-level timestamps
            words = []
            if hasattr(segment, "words") and segment.words:
                for word_info in segment.words:
                    words.append({
                        "word": word_info.word,
                        "start": round(word_info.start, 2),
                        "end": round(word_info.end, 2),
                        "probability": round(word_info.probability, 3),
                    })

            # Build segment dict
            segments_list.append({
                "id": seg_id,
                "text": segment.text.strip(),
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "words": words,
            })

        return {
            "language": info.language,
            "duration": round(info.duration, 2),
            "segment_count": len(segments_list),
            "segments": segments_list,
        }

    def _select_device_and_compute_type(self, device_pref: str) -> tuple[str, str]:
        """Determine optimal device and compute type.

        Note: faster-whisper uses CTranslate2 which doesn't support MPS (Apple Metal) yet.
        For Apple Silicon Macs, we fall back to CPU with optimized compute type.

        Args:
            device_pref: Device preference ("auto", "cuda", "cpu")

        Returns:
            Tuple of (device, compute_type)
        """
        import torch

        if device_pref == "auto":
            # Auto-detect best available device
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
                logger.debug("GPU detected: CUDA")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                # MPS (Apple Metal) not supported by CTranslate2 - use CPU
                device = "cpu"
                compute_type = "int8"
                logger.info(
                    "Apple Silicon detected - using CPU (CTranslate2 doesn't support MPS yet). "
                    "Expect 15-20 min for 90-min video."
                )
            else:
                device = "cpu"
                compute_type = "int8"
                logger.warning(
                    "No GPU detected - using CPU (slower). "
                    "Expect 15-20 min for 90-min video."
                )
        else:
            # Use explicit preference
            device = device_pref
            if device == "cuda":
                compute_type = "float16"
            else:
                compute_type = "int8"

        # Allow compute_type override from config
        if "compute_type" in self.config:
            compute_type = self.config["compute_type"]

        return device, compute_type
