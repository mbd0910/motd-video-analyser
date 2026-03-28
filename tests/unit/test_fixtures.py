"""Tests for fixture loading."""

import json
from pathlib import Path

import pytest

from motd.fixtures import FileFixtureProvider
from motd.models import Fixture


@pytest.fixture
def fixtures_file(tmp_path: Path) -> Path:
    data = {
        "season": "2025-26",
        "competition": "Premier League",
        "fixtures": [
            {
                "match_id": "2025-11-01-brighton-leeds",
                "date": "2025-11-01",
                "home_team": "Brighton & Hove Albion",
                "away_team": "Leeds United",
                "kickoff": "15:00",
                "final_score": {"home": 2, "away": 1},
                "venue": "Amex Stadium",
            },
            {
                "match_id": "2025-11-01-arsenal-chelsea",
                "date": "2025-11-01",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "kickoff": "17:30",
                "final_score": {"home": 3, "away": 0},
                "venue": "Emirates Stadium",
            },
            {
                "match_id": "2025-11-08-tottenham-manutd",
                "date": "2025-11-08",
                "home_team": "Tottenham Hotspur",
                "away_team": "Manchester United",
                "kickoff": "12:30",
                "final_score": {"home": 1, "away": 1},
                "venue": "Tottenham Hotspur Stadium",
            },
        ],
    }
    path = tmp_path / "fixtures.json"
    path.write_text(json.dumps(data))
    return path


class TestFileFixtureProvider:
    def test_get_fixtures_for_date(self, fixtures_file: Path) -> None:
        provider = FileFixtureProvider(fixtures_file)
        fixtures = provider.get_fixtures_for_date("2025-11-01")
        assert len(fixtures) == 2
        assert all(isinstance(f, Fixture) for f in fixtures)
        assert fixtures[0].home_team == "Brighton & Hove Albion"

    def test_no_fixtures_for_date(self, fixtures_file: Path) -> None:
        provider = FileFixtureProvider(fixtures_file)
        fixtures = provider.get_fixtures_for_date("2025-12-25")
        assert fixtures == []

    def test_get_all_fixtures(self, fixtures_file: Path) -> None:
        provider = FileFixtureProvider(fixtures_file)
        fixtures = provider.get_all_fixtures()
        assert len(fixtures) == 3

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        provider = FileFixtureProvider(tmp_path / "nope.json")
        with pytest.raises(FileNotFoundError):
            provider.get_all_fixtures()

    def test_fixture_missing_required_field_raises(self, tmp_path: Path) -> None:
        data = {
            "fixtures": [
                {
                    "date": "2025-11-01",
                    "home_team": "A",
                    "away_team": "B",
                    # missing match_id
                },
            ],
        }
        path = tmp_path / "fixtures.json"
        path.write_text(json.dumps(data))
        provider = FileFixtureProvider(path)
        with pytest.raises(ValueError, match="missing required field.*match_id"):
            provider.get_all_fixtures()

    def test_fixture_without_score(self, tmp_path: Path) -> None:
        data = {
            "fixtures": [
                {
                    "match_id": "2025-11-01-a-b",
                    "date": "2025-11-01",
                    "home_team": "A",
                    "away_team": "B",
                    "venue": "V",
                },
            ],
        }
        path = tmp_path / "fixtures.json"
        path.write_text(json.dumps(data))
        provider = FileFixtureProvider(path)
        fixtures = provider.get_all_fixtures()
        assert len(fixtures) == 1
        assert fixtures[0].score is None
