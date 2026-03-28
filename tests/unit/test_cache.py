"""Tests for the cache module."""

from __future__ import annotations

from pathlib import Path

from motd.cache import get_or_compute, load
from motd.models import Transcript, TranscriptSegment


def _make_transcript(episode_id: str = "ep1") -> Transcript:
    return Transcript(
        episode_id=episode_id,
        duration_seconds=60.0,
        segments=[TranscriptSegment(start=0.0, end=5.0, text="Hello.")],
    )


class TestGetOrCompute:
    """Test the get_or_compute cache function."""

    def test_computes_on_cache_miss(self, tmp_path: Path) -> None:
        path = tmp_path / "ep1" / "transcript.json"
        result, was_computed = get_or_compute(
            path, Transcript, _make_transcript
        )
        assert was_computed is True
        assert result.episode_id == "ep1"
        assert path.exists()

    def test_returns_cached_on_hit(self, tmp_path: Path) -> None:
        path = tmp_path / "ep1" / "transcript.json"
        # First call: compute
        get_or_compute(path, Transcript, _make_transcript)
        # Second call: cache hit
        call_count = 0

        def counting_compute() -> Transcript:
            nonlocal call_count
            call_count += 1
            return _make_transcript()

        result, was_computed = get_or_compute(
            path, Transcript, counting_compute
        )
        assert was_computed is False
        assert call_count == 0
        assert result.episode_id == "ep1"

    def test_force_recomputes(self, tmp_path: Path) -> None:
        path = tmp_path / "ep1" / "transcript.json"
        get_or_compute(path, Transcript, _make_transcript)

        call_count = 0

        def counting_compute() -> Transcript:
            nonlocal call_count
            call_count += 1
            return _make_transcript("recomputed")

        result, was_computed = get_or_compute(
            path, Transcript, counting_compute, force=True
        )
        assert was_computed is True
        assert call_count == 1
        assert result.episode_id == "recomputed"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "transcript.json"
        get_or_compute(path, Transcript, _make_transcript)
        assert path.exists()

    def test_serialisation_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "ep1" / "transcript.json"
        original = _make_transcript()
        get_or_compute(path, Transcript, lambda: original)
        loaded, _ = get_or_compute(path, Transcript, lambda: _make_transcript("wrong"))
        assert loaded.episode_id == original.episode_id
        assert len(loaded.segments) == len(original.segments)


class TestLoad:
    """Test the load function."""

    def test_returns_none_on_miss(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.json"
        assert load(path, Transcript) is None

    def test_loads_cached_artefact(self, tmp_path: Path) -> None:
        path = tmp_path / "transcript.json"
        transcript = _make_transcript()
        path.write_text(transcript.model_dump_json(indent=2))
        result = load(path, Transcript)
        assert result is not None
        assert result.episode_id == "ep1"
