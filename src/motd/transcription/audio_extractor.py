"""Audio extraction module for MOTD video analysis.

This module extracts audio from video files and converts it to Whisper's
optimal format (16kHz mono WAV) using ffmpeg.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extracts audio from video files in Whisper-optimal format.

    Converts video audio tracks to 16kHz mono WAV format, which is optimal
    for faster-whisper transcription. Handles various input formats via ffmpeg.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialise audio extractor with configuration.

        Args:
            config: Optional configuration dict with:
                - sample_rate: Target sample rate in Hz (default: 16000)
                - channels: Target channels, 1=mono, 2=stereo (default: 1)
        """
        self.config = config or {}
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.channels = self.config.get("channels", 1)
        logger.debug(
            f"AudioExtractor initialised: {self.sample_rate}Hz, "
            f"{self.channels} channel(s)"
        )

    def extract(self, video_path: str, output_path: str) -> Dict:
        """Extract audio from video to WAV format.

        Args:
            video_path: Path to input video file
            output_path: Path to output audio file (.wav)

        Returns:
            Metadata dict with:
                - success: True if extraction succeeded
                - duration_seconds: Audio duration
                - output_size_mb: Output file size in MB
                - sample_rate: Sample rate used
                - channels: Number of channels

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If ffmpeg not installed or extraction fails
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        # Validate input
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Extracting audio from {video_path.name}")
        logger.debug(f"Input: {video_path} ({video_path.stat().st_size / 1e9:.2f} GB)")
        logger.debug(f"Output: {output_path}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get video duration first
        try:
            duration = self._get_duration(video_path)
            logger.debug(f"Video duration: {duration:.2f} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to get video duration: {e}") from e

        # Extract audio with ffmpeg
        try:
            self._run_ffmpeg(video_path, output_path)
        except Exception as e:
            raise RuntimeError(f"Audio extraction failed: {e}") from e

        # Validate output
        if not output_path.exists():
            raise RuntimeError(f"Output file not created: {output_path}")

        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"✓ Audio extracted: {output_size_mb:.1f} MB, "
            f"{duration:.1f}s ({self.sample_rate}Hz, {self.channels}ch)"
        )

        return {
            "success": True,
            "duration_seconds": duration,
            "output_size_mb": round(output_size_mb, 2),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
        }

    def _get_duration(self, video_path: Path) -> float:
        """Get audio duration using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds

        Raises:
            RuntimeError: If ffprobe command fails
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",  # First audio stream
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            duration = float(result.stdout.strip())
            return duration
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ffprobe failed: {e.stderr if e.stderr else str(e)}"
            ) from e
        except ValueError as e:
            raise RuntimeError(f"Invalid duration value: {result.stdout}") from e

    def _run_ffmpeg(self, video_path: Path, output_path: Path) -> None:
        """Execute ffmpeg command to extract audio.

        Args:
            video_path: Path to input video
            output_path: Path to output audio file

        Raises:
            RuntimeError: If ffmpeg command fails
        """
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-ar", str(self.sample_rate),  # Sample rate
            "-ac", str(self.channels),  # Channels
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian (WAV)
            "-y",  # Overwrite output
            str(output_path),
        ]

        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            # Run ffmpeg with stderr capture (ffmpeg outputs to stderr)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            # ffmpeg writes progress to stderr, but success messages too
            if result.stderr:
                # Log last few lines (summary)
                stderr_lines = result.stderr.strip().split("\n")
                for line in stderr_lines[-3:]:
                    if line and not line.startswith("["):  # Skip progress lines
                        logger.debug(line)

        except FileNotFoundError as e:
            raise RuntimeError(
                "ffmpeg not found. Please install ffmpeg: brew install ffmpeg"
            ) from e
        except subprocess.CalledProcessError as e:
            # Extract meaningful error from stderr
            error_msg = e.stderr if e.stderr else str(e)
            if "Invalid data found" in error_msg:
                raise RuntimeError(
                    f"Video file appears corrupted or has invalid format"
                ) from e
            elif "Stream specifier ':a' does not match" in error_msg:
                raise RuntimeError(
                    f"Video file has no audio track"
                ) from e
            else:
                raise RuntimeError(f"ffmpeg extraction failed: {error_msg}") from e
