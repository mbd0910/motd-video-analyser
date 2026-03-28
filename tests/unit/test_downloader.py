"""Tests for the downloader module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from motd.downloader import (
    DownloadError,
    _derive_episode_id,
    _derive_season,
    _normalise_url,
    _parse_broadcast_date,
    download,
    parse_episode_id,
)


class TestNormaliseUrl:
    """Test URL normalisation from programme ID or URL."""

    def test_full_url_passes_through(self) -> None:
        url = "https://www.bbc.co.uk/iplayer/episode/m0025t4g/match-of-the-day-2025-26-01112025"
        assert _normalise_url(url) == url

    def test_programme_id_becomes_url(self) -> None:
        result = _normalise_url("m0025t4g")
        assert result == "https://www.bbc.co.uk/iplayer/episode/m0025t4g"

    def test_http_url_passes_through(self) -> None:
        url = "http://www.bbc.co.uk/iplayer/episode/m0025t4g"
        assert _normalise_url(url) == url


class TestParseBroadcastDate:
    """Test extracting broadcast date from yt-dlp metadata."""

    def test_uses_release_date_when_present(self) -> None:
        metadata = {"release_date": "20251101", "upload_date": "20251102"}
        assert _parse_broadcast_date(metadata) == "2025-11-01"

    def test_falls_back_to_upload_date(self) -> None:
        metadata = {"upload_date": "20251101"}
        assert _parse_broadcast_date(metadata) == "2025-11-01"

    def test_missing_date_raises(self) -> None:
        with pytest.raises(DownloadError, match="broadcast date"):
            _parse_broadcast_date({})


class TestDeriveSeason:
    """Test season derivation from broadcast date."""

    def test_autumn_date_is_first_year(self) -> None:
        assert _derive_season("2025-11-01") == "2025-26"

    def test_august_start(self) -> None:
        assert _derive_season("2025-08-16") == "2025-26"

    def test_spring_date_is_second_year(self) -> None:
        assert _derive_season("2026-03-15") == "2025-26"

    def test_may_end(self) -> None:
        assert _derive_season("2026-05-25") == "2025-26"

    def test_january(self) -> None:
        assert _derive_season("2026-01-10") == "2025-26"


class TestDeriveEpisodeId:
    """Test episode_id derivation."""

    def test_standard_date(self) -> None:
        assert _derive_episode_id("2025-11-01") == "motd_2025-26_2025-11-01"

    def test_spring_date(self) -> None:
        assert _derive_episode_id("2026-03-15") == "motd_2025-26_2026-03-15"


class TestParseEpisodeId:
    """Test parsing broadcast_date and season from episode_id."""

    def test_standard_episode_id(self) -> None:
        date, season = parse_episode_id("motd_2025-26_2025-11-01")
        assert date == "2025-11-01"
        assert season == "2025-26"

    def test_spring_episode_id(self) -> None:
        date, season = parse_episode_id("motd_2025-26_2026-03-15")
        assert date == "2026-03-15"
        assert season == "2025-26"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot derive date"):
            parse_episode_id("bad_id")

    def test_roundtrip_with_derive(self) -> None:
        """parse_episode_id is the inverse of _derive_episode_id."""
        episode_id = _derive_episode_id("2025-11-01")
        date, season = parse_episode_id(episode_id)
        assert date == "2025-11-01"
        assert season == "2025-26"


class TestDownload:
    """Test the download function end-to-end with mocked subprocess."""

    @patch("motd.downloader.subprocess.run")
    def test_successful_download(self, mock_run: MagicMock, tmp_path: Path) -> None:
        metadata = {
            "id": "m0025t4g",
            "title": "Match of the Day, Series 60: 01/11/2025",
            "release_date": "20251101",
            "ext": "mp4",
        }

        # First call: --dump-json returns metadata
        dump_result = MagicMock()
        dump_result.stdout = json.dumps(metadata)
        dump_result.returncode = 0

        # Second call: actual download
        dl_result = MagicMock()
        dl_result.returncode = 0

        mock_run.side_effect = [dump_result, dl_result]

        result = download(
            "https://www.bbc.co.uk/iplayer/episode/m0025t4g",
            output_dir=str(tmp_path),
        )

        assert result.episode_id == "motd_2025-26_2025-11-01"
        assert result.video_path == str(tmp_path / "motd_2025-26_2025-11-01.mp4")
        assert mock_run.call_count == 2

    @patch("motd.downloader.subprocess.run")
    def test_programme_id_normalised(self, mock_run: MagicMock, tmp_path: Path) -> None:
        metadata = {"release_date": "20251101", "ext": "mp4"}
        dump_result = MagicMock()
        dump_result.stdout = json.dumps(metadata)
        dump_result.returncode = 0

        dl_result = MagicMock()
        dl_result.returncode = 0

        mock_run.side_effect = [dump_result, dl_result]

        result = download("m0025t4g", output_dir=str(tmp_path))
        assert result.episode_id == "motd_2025-26_2025-11-01"

        # Verify the URL was normalised in the subprocess call
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "https://www.bbc.co.uk/iplayer/episode/m0025t4g" in first_call_args

    @patch("motd.downloader.subprocess.run")
    def test_metadata_fetch_failure_raises(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: programme unavailable"
        )
        with pytest.raises(DownloadError, match="metadata"):
            download("m0025t4g", output_dir=str(tmp_path))

    @patch("motd.downloader.subprocess.run")
    def test_download_failure_raises(self, mock_run: MagicMock, tmp_path: Path) -> None:
        metadata = {"release_date": "20251101", "ext": "mp4"}
        dump_result = MagicMock()
        dump_result.stdout = json.dumps(metadata)
        dump_result.returncode = 0

        mock_run.side_effect = [
            dump_result,
            subprocess.CalledProcessError(1, "yt-dlp", stderr="network error"),
        ]

        with pytest.raises(DownloadError, match="download"):
            download("m0025t4g", output_dir=str(tmp_path))

    @patch("motd.downloader.subprocess.run")
    def test_default_extension_when_missing(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        metadata = {"release_date": "20251101"}
        dump_result = MagicMock()
        dump_result.stdout = json.dumps(metadata)
        dump_result.returncode = 0

        dl_result = MagicMock()
        dl_result.returncode = 0

        mock_run.side_effect = [dump_result, dl_result]

        result = download("m0025t4g", output_dir=str(tmp_path))
        assert result.video_path.endswith(".mp4")

    @patch("motd.downloader.subprocess.run")
    def test_skips_download_if_video_exists(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        metadata = {"release_date": "20251101", "ext": "mp4"}
        dump_result = MagicMock()
        dump_result.stdout = json.dumps(metadata)
        dump_result.returncode = 0

        mock_run.side_effect = [dump_result]

        # Pre-create the video file
        video_path = tmp_path / "motd_2025-26_2025-11-01.mp4"
        video_path.write_bytes(b"fake video content")

        result = download("m0025t4g", output_dir=str(tmp_path))
        assert result.video_path == str(video_path)
        # Only metadata fetch, no download
        assert mock_run.call_count == 1
