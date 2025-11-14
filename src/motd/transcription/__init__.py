"""MOTD transcription module for audio extraction and transcription."""

from motd.transcription.audio_extractor import AudioExtractor
from motd.transcription.whisper_transcriber import WhisperTranscriber

__all__ = ["AudioExtractor", "WhisperTranscriber"]
