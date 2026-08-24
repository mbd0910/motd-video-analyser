"""Tests for the publisher module."""

from __future__ import annotations

import json

import pytest

from motd.models import EpisodeAnalysis, MatchCoverage, Segment
from motd.publisher import (
    _build_index_entry,
    _update_index,
    publish,
)


def _make_analysis(
    episode_id: str = "motd_2025-26_2025-11-01",
    broadcast_date: str = "2025-11-01",
    season: str = "2025-26",
    num_matches: int = 2,
) -> EpisodeAnalysis:
    matches = [
        MatchCoverage(
            fpl_code=2645195 + i,
            order=i + 1,
            segments={"highlights": Segment(start="00:00", end="05:00")},
        )
        for i in range(num_matches)
    ]
    return EpisodeAnalysis(
        episode_id=episode_id,
        broadcast_date=broadcast_date,
        season=season,
        matches=matches,
    )


class FakeR2Client:
    """In-memory fake R2 client for testing."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes, content_type: str = "application/json") -> None:
        self.objects[key] = data

    def download(self, key: str) -> bytes | None:
        return self.objects.get(key)


# -- _build_index_entry tests --


@pytest.mark.unit
class TestBuildIndexEntry:
    def test_extracts_metadata(self) -> None:
        analysis = _make_analysis()
        entry = _build_index_entry(analysis)

        assert entry["episode_id"] == "motd_2025-26_2025-11-01"
        assert entry["broadcast_date"] == "2025-11-01"
        assert entry["season"] == "2025-26"
        assert entry["match_count"] == 2

    def test_zero_matches(self) -> None:
        analysis = _make_analysis(num_matches=0)
        entry = _build_index_entry(analysis)
        assert entry["match_count"] == 0


# -- _update_index tests --


@pytest.mark.unit
class TestUpdateIndex:
    def test_adds_new_episode_to_empty_index(self) -> None:
        existing: list[dict[str, object]] = []
        entry = {"episode_id": "ep1", "broadcast_date": "2025-11-01", "season": "2025-26",
                 "match_count": 3}
        result = _update_index(existing, entry)

        assert len(result) == 1
        assert result[0]["episode_id"] == "ep1"

    def test_adds_new_episode_to_existing_index(self) -> None:
        existing = [
            {"episode_id": "ep1", "broadcast_date": "2025-10-01", "season": "2025-26",
             "match_count": 2},
        ]
        entry = {"episode_id": "ep2", "broadcast_date": "2025-11-01", "season": "2025-26",
                 "match_count": 3}
        result = _update_index(existing, entry)

        assert len(result) == 2

    def test_updates_existing_episode_no_duplicate(self) -> None:
        existing = [
            {"episode_id": "ep1", "broadcast_date": "2025-10-01", "season": "2025-26",
             "match_count": 2},
        ]
        entry = {"episode_id": "ep1", "broadcast_date": "2025-10-01", "season": "2025-26",
                 "match_count": 5}
        result = _update_index(existing, entry)

        assert len(result) == 1
        assert result[0]["match_count"] == 5

    def test_preserves_other_episodes_on_update(self) -> None:
        existing = [
            {"episode_id": "ep1", "broadcast_date": "2025-10-01", "season": "2025-26",
             "match_count": 2},
            {"episode_id": "ep2", "broadcast_date": "2025-10-08", "season": "2025-26",
             "match_count": 3},
        ]
        entry = {"episode_id": "ep1", "broadcast_date": "2025-10-01", "season": "2025-26",
                 "match_count": 5}
        result = _update_index(existing, entry)

        assert len(result) == 2
        ep1 = next(e for e in result if e["episode_id"] == "ep1")
        ep2 = next(e for e in result if e["episode_id"] == "ep2")
        assert ep1["match_count"] == 5
        assert ep2["match_count"] == 3


# -- publish integration tests (with fake R2) --


@pytest.mark.unit
class TestPublish:
    def test_uploads_episode_json(self) -> None:
        client = FakeR2Client()
        analysis = _make_analysis()

        publish(analysis, client)

        key = "episodes/motd_2025-26_2025-11-01.json"
        assert key in client.objects
        uploaded = json.loads(client.objects[key])
        assert uploaded["episode_id"] == "motd_2025-26_2025-11-01"
        assert len(uploaded["matches"]) == 2

    def test_creates_index_on_first_publish(self) -> None:
        client = FakeR2Client()
        analysis = _make_analysis()

        publish(analysis, client)

        index_data = json.loads(client.objects["episodes/index.json"])
        assert len(index_data["episodes"]) == 1
        assert index_data["episodes"][0]["episode_id"] == "motd_2025-26_2025-11-01"

    def test_updates_existing_index(self) -> None:
        client = FakeR2Client()

        # Publish first episode
        publish(_make_analysis(episode_id="motd_2025-26_2025-11-01"), client)
        # Publish second episode
        publish(
            _make_analysis(
                episode_id="motd_2025-26_2025-11-08",
                broadcast_date="2025-11-08",
            ),
            client,
        )

        index_data = json.loads(client.objects["episodes/index.json"])
        assert len(index_data["episodes"]) == 2

    def test_reprocess_updates_not_duplicates(self) -> None:
        client = FakeR2Client()

        # Publish same episode twice with different match count
        publish(_make_analysis(num_matches=2), client)
        publish(_make_analysis(num_matches=5), client)

        index_data = json.loads(client.objects["episodes/index.json"])
        assert len(index_data["episodes"]) == 1
        assert index_data["episodes"][0]["match_count"] == 5

        # Episode JSON should also be updated
        ep_data = json.loads(client.objects["episodes/motd_2025-26_2025-11-01.json"])
        assert len(ep_data["matches"]) == 5

    def test_corrupted_index_rebuilds_from_scratch(self) -> None:
        client = FakeR2Client()
        # Pre-seed a corrupted index
        client.objects["episodes/index.json"] = b"not valid json {{"

        analysis = _make_analysis()
        publish(analysis, client)

        index_data = json.loads(client.objects["episodes/index.json"])
        assert len(index_data["episodes"]) == 1
        assert index_data["episodes"][0]["episode_id"] == "motd_2025-26_2025-11-01"

    def test_returns_episode_url(self) -> None:
        client = FakeR2Client()
        analysis = _make_analysis()

        url = publish(analysis, client)

        assert url == "episodes/motd_2025-26_2025-11-01.json"
