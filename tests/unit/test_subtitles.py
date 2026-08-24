"""Tests for the subtitles module — TTML fetching and parsing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from motd.subtitles import SubtitleError, download_subtitles, parse_ttml

pytestmark = pytest.mark.unit


def _ttml(body: str, styling: str | None = None) -> str:
    """Wrap cue XML in the TTML envelope iPlayer serves."""
    default_styling = """
        <style xml:id="S1" tts:color="#FFFF00" tts:backgroundColor="#000000"/>
        <style xml:id="S2" tts:color="#FFFFFF" tts:backgroundColor="#000000"/>
        <style xml:id="S3" tts:color="#00FFFF" tts:backgroundColor="#000000"/>
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml"
    xmlns:tts="http://www.w3.org/ns/ttml#styling"
    xml:lang="en-GB">
  <head>
    <styling>{styling if styling is not None else default_styling}</styling>
  </head>
  <body><div>{body}</div></body>
</tt>"""


def _write(tmp_path: Path, body: str, styling: str | None = None) -> Path:
    path = tmp_path / "subtitles.ttml"
    path.write_text(_ttml(body, styling))
    return path


class TestParseTiming:
    """Clock times convert to seconds."""

    def test_timings_converted_to_seconds(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:21.680" end="00:00:34.840">'
            '<span style="S2">First cue</span></p>',
        )
        transcript = parse_ttml(path, "motd_2026-27_2026-08-22")

        assert transcript.segments[0].start == pytest.approx(21.68)
        assert transcript.segments[0].end == pytest.approx(34.84)

    def test_hours_included_in_conversion(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="01:19:12.500" end="01:19:15.000">'
            '<span style="S2">Past the hour</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert transcript.segments[0].start == pytest.approx(4752.5)

    def test_duration_is_last_cue_end(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S2">One</span></p>'
            '<p begin="00:01:00.000" end="00:01:30.250">'
            '<span style="S2">Two</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert transcript.duration_seconds == pytest.approx(90.25)

    def test_unsupported_time_expression_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="10s" end="12s"><span style="S2">Offset time</span></p>',
        )

        with pytest.raises(SubtitleError, match="Unsupported TTML time expression"):
            parse_ttml(path, "ep")

    def test_non_numeric_time_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:ab.000" end="00:00:02.000">'
            '<span style="S2">Bad</span></p>',
        )

        with pytest.raises(SubtitleError, match="Unsupported TTML time expression"):
            parse_ttml(path, "ep")

    def test_end_before_start_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p xml:id="C9" begin="00:00:10.000" end="00:00:05.000">'
            '<span style="S2">Reversed</span></p>',
        )

        with pytest.raises(SubtitleError, match="before it begins"):
            parse_ttml(path, "ep")


class TestParseSpeakers:
    """Subtitle colours become speaker markers."""

    def test_colours_map_to_names(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S1">Yellow speaker</span></p>'
            '<p begin="00:00:02.000" end="00:00:03.000">'
            '<span style="S2">White speaker</span></p>'
            '<p begin="00:00:03.000" end="00:00:04.000">'
            '<span style="S3">Cyan speaker</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert [s.speaker for s in transcript.segments] == ["yellow", "white", "cyan"]

    def test_unknown_colour_falls_back_to_hex(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S9">Odd colour</span></p>',
            styling='<style xml:id="S9" tts:color="#FF00FF"/>',
        )
        transcript = parse_ttml(path, "ep")

        assert transcript.segments[0].speaker == "#FF00FF"

    def test_span_without_style_has_no_speaker(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000"><span>Unstyled</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert transcript.segments[0].speaker is None


class TestParseCueRuns:
    """A cue splits into contiguous runs of one speaker."""

    def test_single_speaker_cue_is_one_segment(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:03.000">'
            '<span style="S2">One half</span><br/>'
            '<span style="S2">other half</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert len(transcript.segments) == 1
        assert transcript.segments[0].text == "One half other half"

    def test_mixed_speaker_cue_splits(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:04.000">'
            '<span style="S1">Studio question</span><br/>'
            '<span style="S3">Pundit answer</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert len(transcript.segments) == 2
        assert transcript.segments[0].speaker == "yellow"
        assert transcript.segments[1].speaker == "cyan"

    def test_split_segments_share_cue_timing(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:04.000">'
            '<span style="S1">Question</span><br/>'
            '<span style="S3">Answer</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert all(s.start == pytest.approx(1.0) for s in transcript.segments)
        assert all(s.end == pytest.approx(4.0) for s in transcript.segments)

    def test_speaker_returning_within_cue_starts_new_run(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:05.000">'
            '<span style="S1">Alpha</span><br/>'
            '<span style="S3">Beta</span><br/>'
            '<span style="S1">Alpha again</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert [s.speaker for s in transcript.segments] == ["yellow", "cyan", "yellow"]

    def test_empty_spans_skipped(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S2">   </span><span style="S2">Real text</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert len(transcript.segments) == 1
        assert transcript.segments[0].text == "Real text"

    def test_cue_without_timing_skipped(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p><span style="S2">No timing</span></p>'
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S2">Timed</span></p>',
        )
        transcript = parse_ttml(path, "ep")

        assert len(transcript.segments) == 1
        assert transcript.segments[0].text == "Timed"


class TestParseErrors:
    """Unusable input fails loudly."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SubtitleError, match="not found"):
            parse_ttml(tmp_path / "absent.ttml", "ep")

    def test_malformed_xml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "subtitles.ttml"
        path.write_text("<tt><body><div><p>unclosed")

        with pytest.raises(SubtitleError, match="Malformed TTML"):
            parse_ttml(path, "ep")

    def test_no_cues_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "")

        with pytest.raises(SubtitleError, match="No subtitle cues"):
            parse_ttml(path, "ep")

    def test_cues_with_only_empty_text_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000"><span style="S2"> </span></p>',
        )

        with pytest.raises(SubtitleError, match="No subtitle cues"):
            parse_ttml(path, "ep")


class TestParseResult:
    """Transcript carries episode identity."""

    def test_episode_id_preserved(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            '<p begin="00:00:01.000" end="00:00:02.000">'
            '<span style="S2">Text</span></p>',
        )
        transcript = parse_ttml(path, "motd_2026-27_2026-08-22")

        assert transcript.episode_id == "motd_2026-27_2026-08-22"


class TestDownloadSubtitles:
    """yt-dlp invocation and file placement."""

    def test_written_file_moved_to_destination(self, tmp_path: Path) -> None:
        destination = tmp_path / "cache" / "subtitles.ttml"

        def fake_run(cmd, **kwargs):
            out_template = cmd[cmd.index("-o") + 1]
            Path(out_template.replace("%(ext)s", "en.ttml")).write_text("<tt/>")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch("motd.subtitles.subprocess.run", side_effect=fake_run):
            result = download_subtitles("https://example.com/ep", destination)

        assert result == destination
        assert destination.read_text() == "<tt/>"

    def test_requests_ttml_not_converted_format(self, tmp_path: Path) -> None:
        """Colour styling only survives in TTML, so the format is pinned."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            out_template = cmd[cmd.index("-o") + 1]
            Path(out_template.replace("%(ext)s", "en.ttml")).write_text("<tt/>")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch("motd.subtitles.subprocess.run", side_effect=fake_run):
            download_subtitles("https://example.com/ep", tmp_path / "subs.ttml")

        assert "--sub-format" in captured["cmd"]
        assert captured["cmd"][captured["cmd"].index("--sub-format") + 1] == "ttml"
        assert "--skip-download" in captured["cmd"]

    def test_yt_dlp_failure_raises(self, tmp_path: Path) -> None:
        error = subprocess.CalledProcessError(1, "yt-dlp", stderr="boom")

        with (
            patch("motd.subtitles.subprocess.run", side_effect=error),
            pytest.raises(SubtitleError, match="yt-dlp failed"),
        ):
            download_subtitles("https://example.com/ep", tmp_path / "subs.ttml")

    def test_no_subtitles_produced_raises(self, tmp_path: Path) -> None:
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with (
            patch("motd.subtitles.subprocess.run", side_effect=fake_run),
            pytest.raises(SubtitleError, match="No subtitles available"),
        ):
            download_subtitles("https://example.com/ep", tmp_path / "subs.ttml")
