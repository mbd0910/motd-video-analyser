"""Whisper transcription module for MOTD audio analysis.

This module uses faster-whisper (NOT openai-whisper) for 4x faster processing
with identical accuracy. Generates word-level timestamps for precise analysis.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


# Known Whisper spelling errors that initial_prompt cannot fix.
# Whisper has ingrained biases from training data (e.g., "Molyneux" the surname
# appears more frequently than "Molineux" the stadium).
# See: https://github.com/SYSTRAN/faster-whisper/issues/948
SPELLING_CORRECTIONS: dict[str, str] = {
    "Molyneux": "Molineux",  # Wolves stadium (Whisper prefers the surname spelling)
}


class WhisperTranscriber:
    """Transcribes audio using faster-whisper with word-level timestamps.

    Uses CTranslate2-optimised Whisper models for fast, accurate transcription.
    Automatically detects and uses GPU (CUDA/MPS) if available, falls back to CPU.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialise Whisper transcriber with configuration.

        Args:
            config: Optional configuration dict with:
                - model_size: Model size (default: "large-v3")
                - device: Device to use - "auto"/"cuda"/"mps"/"cpu" (default: "auto")
                - compute_type: Compute type (default: "float16" for GPU, "int8" for CPU)
                - language: Language code (default: "en")
                - enable_vocabulary_hints: Enable venue/team hints (default: True)

        Raises:
            RuntimeError: If model loading fails
        """
        self.config = config or {}
        self.model_size = self.config.get("model_size", "large-v3")
        self.language = self.config.get("language", "en")
        self.enable_vocabulary_hints = self.config.get("enable_vocabulary_hints", True)

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

        # Build vocabulary hints for better transcription accuracy
        if self.enable_vocabulary_hints:
            self.initial_prompt, self.hotwords = self._build_vocabulary_hints()
            logger.info(f"✓ Vocabulary hints loaded ({len(self.initial_prompt)} chars)")
        else:
            self.initial_prompt = None
            self.hotwords = None

    def transcribe(self, audio_path: str) -> dict[str, Any]:
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
            # Build transcribe parameters
            transcribe_params = {
                "language": self.language,
                "word_timestamps": True,
                "vad_filter": True,  # Voice Activity Detection - removes silence
            }

            # Add vocabulary hints if enabled
            if self.enable_vocabulary_hints:
                transcribe_params["initial_prompt"] = self.initial_prompt
                # Note: hotwords disabled due to faster-whisper token limit issues
                # See: https://github.com/SYSTRAN/faster-whisper/issues/948
                if self.hotwords is not None:
                    transcribe_params["hotwords"] = self.hotwords
                logger.debug("Using vocabulary hints (initial_prompt only)")

            segments_generator, info = self.model.transcribe(
                str(audio_path),
                **transcribe_params
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

    def _process_segments(self, segments_generator, info) -> dict[str, Any]:
        """Convert Whisper segments generator to structured output.

        Args:
            segments_generator: Generator of TranscriptionSegment objects
            info: TranscriptionInfo object with metadata

        Returns:
            Dict with structured segments and metadata
        """
        segments_list = []

        for seg_id, segment in enumerate(segments_generator):
            # Extract word-level timestamps (with spelling corrections)
            words = []
            if hasattr(segment, "words") and segment.words:
                for word_info in segment.words:
                    words.append({
                        "word": self._apply_spelling_corrections(word_info.word),
                        "start": round(word_info.start, 2),
                        "end": round(word_info.end, 2),
                        "probability": round(word_info.probability, 3),
                    })

            # Build segment dict (with spelling corrections)
            segments_list.append({
                "id": seg_id,
                "text": self._apply_spelling_corrections(segment.text.strip()),
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

    def _apply_spelling_corrections(self, text: str) -> str:
        """Apply known spelling corrections to transcribed text.

        Whisper has ingrained biases for certain spellings (e.g., "Molyneux"
        instead of "Molineux") that initial_prompt cannot override. This
        post-processing step corrects known issues.

        Uses case-insensitive matching but preserves the original case pattern:
        - "Molyneux" → "Molineux"
        - "molyneux" → "molineux"
        - "MOLYNEUX" → "MOLINEUX"

        Args:
            text: Text to correct

        Returns:
            Corrected text
        """
        for wrong, correct in SPELLING_CORRECTIONS.items():
            # Case-insensitive replacement preserving case
            # Use default argument to bind `correct` at function definition time
            def replace_preserving_case(
                match: re.Match, replacement: str = correct
            ) -> str:
                matched = match.group(0)
                if matched.isupper():
                    return replacement.upper()
                elif matched.islower():
                    return replacement.lower()
                elif matched[0].isupper():
                    return replacement.capitalize()
                return replacement

            text = re.sub(wrong, replace_preserving_case, text, flags=re.IGNORECASE)

        return text

    def _build_vocabulary_hints(self) -> tuple[str, str | None]:
        """Build vocabulary hints from Premier League venues and teams data.

        Loads stadium names and team names from JSON files to guide Whisper transcription.
        This improves accuracy for proper nouns (e.g., "Molineux" vs "Molyneux").

        Note: We only use initial_prompt, not hotwords. The hotwords parameter causes
        "maximum decoding length must be > 0" errors when combined with initial_prompt
        due to faster-whisper's 224 token limit. See:
        https://github.com/SYSTRAN/faster-whisper/issues/948

        Returns:
            Tuple of (initial_prompt, hotwords):
                - initial_prompt: Context string for transcription (~200 chars, well under 224 token limit)
                - hotwords: Always None (disabled to avoid token overflow)

        Raises:
            FileNotFoundError: If venue/team JSON files not found
            ValueError: If JSON files have invalid structure
        """
        # Determine project root (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        venues_path = project_root / "data" / "venues" / "premier_league_2025_26.json"
        teams_path = project_root / "data" / "teams" / "premier_league_2025_26.json"

        # Load venues data
        if not venues_path.exists():
            raise FileNotFoundError(f"Venues file not found: {venues_path}")

        try:
            with open(venues_path) as f:
                venues_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in venues file: {e}") from e

        # Load teams data
        if not teams_path.exists():
            raise FileNotFoundError(f"Teams file not found: {teams_path}")

        try:
            with open(teams_path) as f:
                teams_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in teams file: {e}") from e

        # Extract stadium names and aliases
        stadium_names = []
        for venue in venues_data.get("venues", []):
            # Add main stadium name
            if "stadium" in venue:
                stadium_names.append(venue["stadium"])
            # Add aliases (common short forms like "Anfield", "The Amex")
            for alias in venue.get("aliases", []):
                if alias:  # Skip empty strings
                    stadium_names.append(alias)

        # Extract team names and alternates
        team_names = []
        for team in teams_data.get("teams", []):
            # Add full team name
            if "full" in team:
                team_names.append(team["full"])
            # Add alternates (e.g., "Man United", "The Gunners")
            for alternate in team.get("alternates", []):
                if alternate:  # Skip empty strings
                    team_names.append(alternate)

        # Build initial_prompt with priority words (known problematic spellings first)
        # Keep under 224 tokens (~890 chars) to avoid faster-whisper errors
        # Priority: Include words we know Whisper misspells (Molineux, Amex, etc.)
        priority_stadiums = ["Molineux", "The Amex", "Selhurst Park", "Craven Cottage", "Kenilworth Road"]
        priority_teams = ["Wolverhampton Wanderers", "Brighton", "Crystal Palace", "Fulham", "Luton Town"]

        # Add some common stadiums for broader context
        common_stadiums = ["Anfield", "Old Trafford", "Emirates Stadium", "Stamford Bridge", "Etihad Stadium"]

        all_stadium_examples = priority_stadiums + common_stadiums
        initial_prompt = (
            "This is BBC Match of the Day football commentary. "
            f"Premier League stadiums: {', '.join(all_stadium_examples)}. "
            f"Teams: {', '.join(priority_teams)}."
        )

        # Don't use hotwords - causes token overflow errors with faster-whisper
        # See: https://github.com/SYSTRAN/faster-whisper/issues/948
        hotwords = None

        logger.debug(f"Loaded {len(stadium_names)} stadium names, {len(team_names)} team names")
        logger.debug(f"Initial prompt length: {len(initial_prompt)} chars")

        return initial_prompt, hotwords
