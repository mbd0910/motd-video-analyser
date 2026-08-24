"""Tests for the downloader module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from motd.downloader import DownloadError, download, normalise_url
from motd.episode import Episode


class TestNormaliseUrl:
    """Test URL normalisation from programme ID or URL."""

    def test_full_url_passes_through(self) -> None:
        url = "https://www.bbc.co.uk/iplayer/episode/m0025t4g/match-of-the-day-2025-26-01112025"
        assert normalise_url(url) == url

    def test_programme_id_becomes_url(self) -> None:
        result = normalise_url("m0025t4g")
        assert result == "https://www.bbc.co.uk/iplayer/episode/m0025t4g"

    def test_http_url_passes_through(self) -> None:
        url = "http://www.bbc.co.uk/iplayer/episode/m0025t4g"
        assert normalise_url(url) == url


class TestEpisodeDerivation:
    """Test season derivation and episode_id construction via Episode."""

    def test_autumn_date_is_first_year(self) -> None:
        ep = Episode.from_broadcast_date("2025-11-01")
        assert ep.season == "2025-26"

    def test_august_start(self) -> None:
        ep = Episode.from_broadcast_date("2025-08-16")
        assert ep.season == "2025-26"

    def test_spring_date_is_second_year(self) -> None:
        ep = Episode.from_broadcast_date("2026-03-15")
        assert ep.season == "2025-26"

    def test_may_end(self) -> None:
        ep = Episode.from_broadcast_date("2026-05-25")
        assert ep.season == "2025-26"

    def test_january(self) -> None:
        ep = Episode.from_broadcast_date("2026-01-10")
        assert ep.season == "2025-26"

    def test_standard_date(self) -> None:
        ep = Episode.from_broadcast_date("2025-11-01")
        assert ep.episode_id == "motd_2025-26_2025-11-01"

    def test_spring_date(self) -> None:
        ep = Episode.from_broadcast_date("2026-03-15")
        assert ep.episode_id == "motd_2025-26_2026-03-15"

    def test_roundtrip_with_from_id(self) -> None:
        """from_id is the inverse of from_broadcast_date."""
        ep1 = Episode.from_broadcast_date("2025-11-01")
        ep2 = Episode.from_id(ep1.episode_id)
        assert ep2.broadcast_date == "2025-11-01"
        assert ep2.season == "2025-26"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid episode_id"):
            Episode.from_id("bad_id")


class TestBroadcastDateValidation:
    """Test that malformed dates are rejected rather than silently sliced."""

    @pytest.mark.parametrize(
        "bad_date",
        [
            "22/08/2026",
            "20260822",
            "2026-8-22",
            "not-a-date",
            "",
        ],
    )
    def test_malformed_date_raises(self, bad_date: str) -> None:
        with pytest.raises(ValueError, match="Invalid broadcast date"):
            Episode.from_broadcast_date(bad_date)

    def test_impossible_calendar_date_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid broadcast date"):
            Episode.from_broadcast_date("2026-02-30")

    @patch("motd.downloader.subprocess.run")
    def test_download_surfaces_bad_date_as_download_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        with pytest.raises(DownloadError, match="Invalid broadcast date"):
            download("m0025t4g", "22/08/2026", output_dir=str(tmp_path))
        mock_run.assert_not_called()


class TestDownload:
    """Test the download function end-to-end with mocked subprocess."""

    @staticmethod
    def _writes_video(tmp_path: Path, name: str) -> object:
        """Build a subprocess.run side effect that creates the file yt-dlp would."""

        def _run(cmd: list[str], **kwargs: object) -> MagicMock:
            (tmp_path / name).write_bytes(b"fake video content")
            return MagicMock(returncode=0)

        return _run

    @patch("motd.downloader.subprocess.run")
    def test_successful_download(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = self._writes_video(
            tmp_path, "motd_2025-26_2025-11-01.mp4"
        )

        result = download(
            "https://www.bbc.co.uk/iplayer/episode/m0025t4g",
            "2025-11-01",
            output_dir=str(tmp_path),
        )

        assert result.episode_id == "motd_2025-26_2025-11-01"
        assert result.video_path == str(tmp_path / "motd_2025-26_2025-11-01.mp4")
        assert mock_run.call_count == 1

    @patch("motd.downloader.subprocess.run")
    def test_output_template_carries_episode_id(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """yt-dlp supplies the extension, so no metadata round-trip is needed."""
        mock_run.side_effect = self._writes_video(
            tmp_path, "motd_2025-26_2025-11-01.mkv"
        )

        result = download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

        cmd = mock_run.call_args_list[0][0][0]
        assert cmd[0] == "yt-dlp"
        assert str(tmp_path / "motd_2025-26_2025-11-01.%(ext)s") in cmd
        assert "https://www.bbc.co.uk/iplayer/episode/m0025t4g" in cmd
        assert result.video_path.endswith(".mkv")

    @patch("motd.downloader.subprocess.run")
    def test_streams_output_rather_than_capturing(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Progress must reach the terminal during a multi-GB download."""
        mock_run.side_effect = self._writes_video(
            tmp_path, "motd_2025-26_2025-11-01.mp4"
        )

        download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

        kwargs = mock_run.call_args_list[0][1]
        assert not kwargs.get("capture_output")
        assert kwargs.get("stdout") is None
        assert kwargs.get("stderr") is None

    @patch("motd.downloader.subprocess.run")
    def test_download_failure_raises(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "yt-dlp")

        with pytest.raises(DownloadError, match="download"):
            download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

    @patch("motd.downloader.subprocess.run")
    def test_missing_video_after_success_raises(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """A zero exit with no output file must not be reported as success."""
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(DownloadError, match="no video was found"):
            download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

    @patch("motd.downloader.subprocess.run")
    def test_skips_download_if_video_exists(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        video_path = tmp_path / "motd_2025-26_2025-11-01.mp4"
        video_path.write_bytes(b"fake video content")

        result = download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

        assert result.video_path == str(video_path)
        mock_run.assert_not_called()

    @patch("motd.downloader.subprocess.run")
    def test_partial_download_is_not_mistaken_for_a_video(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """An abandoned .part file must not short-circuit the download."""
        (tmp_path / "motd_2025-26_2025-11-01.mp4.part").write_bytes(b"partial")
        mock_run.side_effect = self._writes_video(
            tmp_path, "motd_2025-26_2025-11-01.mp4"
        )

        result = download("m0025t4g", "2025-11-01", output_dir=str(tmp_path))

        assert mock_run.call_count == 1
        assert result.video_path.endswith(".mp4")
