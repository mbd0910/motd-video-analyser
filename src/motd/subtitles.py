"""Subtitle handling — fetches BBC iPlayer subtitles and parses them to a Transcript.

iPlayer publishes broadcast subtitles as EBU-TT/TTML carrying millisecond timings
and colour-coded speaker changes, which stands in for a speech-to-text round-trip.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

from motd.models import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)

_TTML = "{http://www.w3.org/ns/ttml}"
_TTS = "{http://www.w3.org/ns/ttml#styling}"
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

SUBTITLE_LANGUAGE = "en"

# BBC subtitles mark a change of speaker by colour. The palette is conventional
# even though the style ids carrying it are assigned per file.
_COLOUR_NAMES = {
    "#FFFFFF": "white",
    "#FFFF00": "yellow",
    "#00FFFF": "cyan",
    "#00FF00": "green",
}


class SubtitleError(Exception):
    """Raised when subtitle download or parsing fails."""


def download_subtitles(url: str, destination: Path) -> Path:
    """Download an episode's TTML subtitles to destination.

    Args:
        url: BBC iPlayer programme URL.
        destination: File path to write the .ttml to.

    Returns:
        The destination path.

    Raises:
        SubtitleError: If yt-dlp fails or the programme carries no subtitles.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    # yt-dlp names the file from the language and format, so it lands in a
    # scratch directory and is moved to the deterministic path callers expect.
    with TemporaryDirectory(prefix="motd_subs_") as tmp_dir:
        cmd = [
            "yt-dlp",
            "--write-subs",
            "--sub-langs", SUBTITLE_LANGUAGE,
            "--sub-format", "ttml",
            "--skip-download",
            "-o", str(Path(tmp_dir) / "subs.%(ext)s"),
            url,
        ]
        logger.info("Fetching subtitles for %s", url)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise SubtitleError(
                f"yt-dlp failed to fetch subtitles: {exc.stderr or exc}"
            ) from exc

        written = sorted(Path(tmp_dir).glob("*.ttml"))
        if not written:
            raise SubtitleError(
                f"No subtitles available for {url}. iPlayer removes episodes "
                "after their availability window, so this may have expired."
            )

        shutil.move(str(written[0]), destination)

    logger.info("Subtitles saved: %s", destination)
    return destination


def parse_ttml(path: Path, episode_id: str) -> Transcript:
    """Parse a TTML subtitle file into a Transcript.

    Raises:
        SubtitleError: If the file is unreadable, malformed, or has no cues.
    """
    if not path.exists():
        raise SubtitleError(f"Subtitle file not found: {path}")

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise SubtitleError(f"Malformed TTML in {path}: {exc}") from exc

    colours = _style_colours(root)
    segments: list[TranscriptSegment] = []

    for cue in root.iter(_TTML + "p"):
        begin, end = cue.get("begin"), cue.get("end")
        if begin is None or end is None:
            continue

        start_seconds = _clock_seconds(begin)
        end_seconds = _clock_seconds(end)
        if end_seconds < start_seconds:
            raise SubtitleError(
                f"Cue {cue.get(_XML_ID)!r} ends ({end}) before it begins ({begin})"
            )

        for speaker, text in _cue_runs(cue, colours):
            segments.append(
                TranscriptSegment(
                    start=start_seconds,
                    end=end_seconds,
                    text=text,
                    speaker=speaker,
                )
            )

    if not segments:
        raise SubtitleError(f"No subtitle cues found in {path}")

    duration = max(seg.end for seg in segments)
    logger.info(
        "Parsed %d cues into %d segments (%.0fs)",
        len(list(root.iter(_TTML + "p"))), len(segments), duration,
    )
    return Transcript(
        episode_id=episode_id,
        duration_seconds=duration,
        segments=segments,
    )


def _style_colours(root: ET.Element) -> dict[str, str]:
    """Map TTML style ids to speaker colour names."""
    colours = {}
    for style in root.iter(_TTML + "style"):
        style_id = style.get(_XML_ID)
        colour = style.get(_TTS + "color")
        if style_id and colour:
            colours[style_id] = _COLOUR_NAMES.get(colour.upper(), colour)
    return colours


def _cue_runs(cue: ET.Element, colours: dict[str, str]) -> list[tuple[str | None, str]]:
    """Split one cue into contiguous runs of a single speaker colour.

    Roughly a tenth of cues change speaker mid-cue; the runs share the cue's
    timing because TTML carries no finer granularity than the cue itself.
    """
    runs: list[tuple[str | None, list[str]]] = []

    for span in cue.iter(_TTML + "span"):
        text = (span.text or "").strip()
        if not text:
            continue
        speaker = colours.get(span.get("style", ""))
        if runs and runs[-1][0] == speaker:
            runs[-1][1].append(text)
        else:
            runs.append((speaker, [text]))

    return [(speaker, " ".join(parts)) for speaker, parts in runs]


def _clock_seconds(value: str) -> float:
    """Convert a TTML HH:MM:SS.mmm clock time to seconds."""
    parts = value.split(":")
    if len(parts) != 3:
        raise SubtitleError(
            f"Unsupported TTML time expression: {value!r}. Expected HH:MM:SS.mmm"
        )
    hours, minutes, seconds = parts
    try:
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError as exc:
        raise SubtitleError(
            f"Unsupported TTML time expression: {value!r}. Expected HH:MM:SS.mmm"
        ) from exc
