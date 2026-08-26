"""Tests for the episode resolution module."""

from __future__ import annotations

from pathlib import Path

import pytest

from motd.episode import DEFAULT_ANALYSIS_DIR, DEFAULT_CACHE_DIR, Episode


class TestFromId:
    """Test resolving episode identity from an episode_id string."""

    def test_standard_episode_id(self) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01")
        assert ep.episode_id == "motd_2025-26_2025-11-01"
        assert ep.broadcast_date == "2025-11-01"
        assert ep.season == "2025-26"

    def test_spring_episode_id(self) -> None:
        ep = Episode.from_id("motd_2025-26_2026-03-15")
        assert ep.broadcast_date == "2026-03-15"
        assert ep.season == "2025-26"

    def test_cache_paths_derived(self) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01")
        assert ep.cache_dir == DEFAULT_CACHE_DIR / "motd_2025-26_2025-11-01"
        assert ep.transcript_path == ep.cache_dir / "transcript.json"
        assert ep.analysis_path == DEFAULT_ANALYSIS_DIR / "motd_2025-26_2025-11-01.json"

    def test_custom_cache_base(self, tmp_path: Path) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01", cache_base=tmp_path)
        assert ep.cache_dir == tmp_path / "motd_2025-26_2025-11-01"

    def test_custom_analysis_base(self, tmp_path: Path) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01", analysis_base=tmp_path)
        assert ep.analysis_path == tmp_path / "motd_2025-26_2025-11-01.json"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid episode_id"):
            Episode.from_id("bad_id")

    def test_missing_season_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid episode_id"):
            Episode.from_id("motd_2025-11-01")

    def test_malformed_date_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid episode_id"):
            Episode.from_id("motd_2025-26_not-a-date")


class TestFromBroadcastDate:
    """Test deriving episode identity from a broadcast date."""

    def test_autumn_date(self) -> None:
        ep = Episode.from_broadcast_date("2025-11-01")
        assert ep.episode_id == "motd_2025-26_2025-11-01"
        assert ep.season == "2025-26"

    def test_august_start(self) -> None:
        ep = Episode.from_broadcast_date("2025-08-16")
        assert ep.season == "2025-26"

    def test_spring_date(self) -> None:
        ep = Episode.from_broadcast_date("2026-03-15")
        assert ep.episode_id == "motd_2025-26_2026-03-15"
        assert ep.season == "2025-26"

    def test_may_end(self) -> None:
        ep = Episode.from_broadcast_date("2026-05-25")
        assert ep.season == "2025-26"

    def test_january(self) -> None:
        ep = Episode.from_broadcast_date("2026-01-10")
        assert ep.season == "2025-26"

    def test_cache_paths_derived(self) -> None:
        ep = Episode.from_broadcast_date("2025-11-01")
        assert ep.cache_dir == DEFAULT_CACHE_DIR / "motd_2025-26_2025-11-01"
        assert ep.transcript_path == ep.cache_dir / "transcript.json"


class TestRoundtrip:
    """Test that from_broadcast_date and from_id are inverses."""

    def test_roundtrip(self) -> None:
        ep1 = Episode.from_broadcast_date("2025-11-01")
        ep2 = Episode.from_id(ep1.episode_id)
        assert ep1.episode_id == ep2.episode_id
        assert ep1.broadcast_date == ep2.broadcast_date
        assert ep1.season == ep2.season


class TestEnsureCacheDir:
    """Test cache directory creation."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01", cache_base=tmp_path)
        assert not ep.cache_dir.exists()
        ep.ensure_cache_dir()
        assert ep.cache_dir.exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01", cache_base=tmp_path)
        ep.ensure_cache_dir()
        ep.ensure_cache_dir()  # should not raise
        assert ep.cache_dir.exists()


class TestFrozen:
    """Episode is immutable."""

    def test_cannot_modify_fields(self) -> None:
        ep = Episode.from_id("motd_2025-26_2025-11-01")
        with pytest.raises(AttributeError):
            ep.episode_id = "other"  # type: ignore[misc]
