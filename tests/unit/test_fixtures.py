"""Tests for fixture loading."""

import json
from pathlib import Path

import pytest

from motd.fixtures import (
    FileFixtureProvider,
    candidates_for_broadcast,
    fixtures_path_for_season,
)
from motd.models import Fixture


@pytest.fixture
def fixtures_file(tmp_path: Path) -> Path:
    data = {
        "season": "2025-26",
        "competition": "Premier League",
        "fixtures": [
            {
                "fpl_code": 2645196,
                "match_id": "2025-11-01-BHA-LEE",
                "date": "2025-11-01",
                "home_team": "Brighton & Hove Albion",
                "away_team": "Leeds United",
                "home_code": "BHA",
                "away_code": "LEE",
                "kickoff": "15:00",
                "final_score": {"home": 2, "away": 1},
                "venue": "Amex Stadium",
            },
            {
                "fpl_code": 2645195,
                "match_id": "2025-11-01-ARS-CHE",
                "date": "2025-11-01",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_code": "ARS",
                "away_code": "CHE",
                "kickoff": "17:30",
                "final_score": {"home": 3, "away": 0},
                "venue": "Emirates Stadium",
            },
            {
                "fpl_code": 2645210,
                "match_id": "2025-11-08-TOT-MUN",
                "date": "2025-11-08",
                "home_team": "Tottenham Hotspur",
                "away_team": "Manchester United",
                "home_code": "TOT",
                "away_code": "MUN",
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

    @pytest.mark.parametrize("missing_field,remaining", [
        ("fpl_code", {"match_id": "x", "date": "2025-11-01", "home_team": "A",
                      "away_team": "B", "home_code": "A", "away_code": "B"}),
        ("match_id", {"fpl_code": 1, "date": "2025-11-01", "home_team": "A",
                      "away_team": "B", "home_code": "A", "away_code": "B"}),
        ("date", {"fpl_code": 1, "match_id": "x", "home_team": "A",
                  "away_team": "B", "home_code": "A", "away_code": "B"}),
        ("home_team", {"fpl_code": 1, "match_id": "x", "date": "2025-11-01",
                       "away_team": "B", "home_code": "A", "away_code": "B"}),
        ("away_team", {"fpl_code": 1, "match_id": "x", "date": "2025-11-01",
                       "home_team": "A", "home_code": "A", "away_code": "B"}),
        ("home_code", {"fpl_code": 1, "match_id": "x", "date": "2025-11-01",
                       "home_team": "A", "away_team": "B", "away_code": "B"}),
    ])
    def test_fixture_missing_required_field_raises(
        self, tmp_path: Path, missing_field: str, remaining: dict
    ) -> None:
        data = {"fixtures": [remaining]}
        path = tmp_path / "fixtures.json"
        path.write_text(json.dumps(data))
        provider = FileFixtureProvider(path)
        with pytest.raises(ValueError, match=f"missing required field.*{missing_field}"):
            provider.get_all_fixtures()

    @pytest.mark.parametrize("bad_score", [
        {"home": 2},              # missing "away"
        {"away": 1},              # missing "home"
        "not-a-dict",             # wrong type entirely
    ])
    def test_fixture_malformed_score_raises(
        self, tmp_path: Path, bad_score: object
    ) -> None:
        data = {
            "fixtures": [
                {
                    "fpl_code": 1,
                    "match_id": "x",
                    "date": "2025-11-01",
                    "home_team": "A",
                    "away_team": "B",
                    "home_code": "A",
                    "away_code": "B",
                    "final_score": bad_score,
                },
            ],
        }
        path = tmp_path / "fixtures.json"
        path.write_text(json.dumps(data))
        provider = FileFixtureProvider(path)
        with pytest.raises(ValueError, match="malformed final_score"):
            provider.get_all_fixtures()

    def test_fixture_without_score(self, tmp_path: Path) -> None:
        data = {
            "fixtures": [
                {
                    "fpl_code": 1,
                    "match_id": "2025-11-01-a-b",
                    "date": "2025-11-01",
                    "home_team": "A",
                    "away_team": "B",
                    "home_code": "A",
                    "away_code": "B",
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


class TestSeasonPaths:
    def test_season_label_maps_to_fixtures_file(self) -> None:
        assert fixtures_path_for_season("2026-27").name == "premier_league_2026_27.json"


@pytest.fixture
def gameweek_file(tmp_path: Path) -> Path:
    data = {
        "season": "2026-27",
        "fixtures": [
            {
                "fpl_code": 2645195,
                "match_id": "2026-08-21-ARS-MUN",
                "date": "2026-08-21",
                "gameweek": 1,
                "kickoff": "20:00",
                "home_team": "Arsenal",
                "away_team": "Manchester United",
                "home_code": "ARS",
                "away_code": "MUN",
                "venue": "Emirates Stadium",
                "final_score": {"home": 3, "away": 0},
                "played": True,
            },
            {
                "fpl_code": 2645196,
                "match_id": "2026-08-22-HUL-COV",
                "date": "2026-08-22",
                "gameweek": 1,
                "kickoff": "12:30",
                "home_team": "Hull City",
                "away_team": "Coventry City",
                "home_code": "HUL",
                "away_code": "COV",
                "venue": "MKM Stadium",
                "final_score": None,
                "played": False,
            },
            {
                "fpl_code": 2645197,
                "match_id": "2026-08-23-BHA-AVL",
                "date": "2026-08-23",
                "gameweek": 1,
                "kickoff": "14:00",
                "home_team": "Brighton & Hove Albion",
                "away_team": "Aston Villa",
                "home_code": "BHA",
                "away_code": "AVL",
                "venue": "Amex Stadium",
                "final_score": None,
                "played": False,
            },
            {
                "fpl_code": 2645210,
                "match_id": "2026-08-29-LIV-CHE",
                "date": "2026-08-29",
                "gameweek": 2,
                "kickoff": "15:00",
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "home_code": "LIV",
                "away_code": "CHE",
                "venue": "Anfield",
                "final_score": None,
                "played": False,
            },
        ],
    }
    path = tmp_path / "fixtures.json"
    path.write_text(json.dumps(data))
    return path



class TestSyncedFixtureFields:
    def test_gameweek_loads_as_a_plain_field(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        assert provider.get_fixtures_for_date("2026-08-21")[0].gameweek == 1

    def test_unplayed_fixture_loads_without_score(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        fixture = provider.get_fixtures_for_date("2026-08-22")[0]
        assert fixture.score is None
        assert fixture.played is False
        assert fixture.kickoff == "12:30"

    def test_legacy_file_without_played_flag_infers_it_from_score(
        self, fixtures_file: Path
    ) -> None:
        provider = FileFixtureProvider(fixtures_file)
        fixture = provider.get_fixtures_for_date("2025-11-01")[0]
        assert fixture.played is True
        assert fixture.gameweek is None


class TestCandidateWindow:
    """The window is the gameweek, not the day — see FixtureProvider.get_candidates."""

    def test_saturday_picks_up_fridays_game(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        labels = [f.match_id for f in provider.get_candidates("2026-08-22")]
        assert labels == ["2026-08-21-ARS-MUN", "2026-08-22-HUL-COV"]

    def test_sunday_keeps_saturdays_games_as_candidates_for_the_round_up(
        self, gameweek_file: Path
    ) -> None:
        provider = FileFixtureProvider(gameweek_file)
        labels = [f.match_id for f in provider.get_candidates("2026-08-23")]
        assert labels == [
            "2026-08-21-ARS-MUN",
            "2026-08-22-HUL-COV",
            "2026-08-23-BHA-AVL",
        ]

    def test_later_gameweeks_are_excluded(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        codes = {f.gameweek for f in provider.get_candidates("2026-08-23")}
        assert codes == {1}

    def test_candidates_are_ordered_by_kickoff(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        candidates = provider.get_candidates("2026-08-23")
        assert candidates == sorted(candidates, key=lambda f: (f.date, f.kickoff or ""))

    def test_a_date_with_no_fixtures_has_no_candidates(self, gameweek_file: Path) -> None:
        provider = FileFixtureProvider(gameweek_file)
        assert provider.get_candidates("2026-12-25") == []

    def test_file_without_gameweeks_falls_back_to_the_day(
        self, fixtures_file: Path
    ) -> None:
        provider = FileFixtureProvider(fixtures_file)
        candidates = provider.get_candidates("2025-11-01")
        assert [f.match_id for f in candidates] == [
            "2025-11-01-BHA-LEE",
            "2025-11-01-ARS-CHE",
        ]

    def test_candidates_for_broadcast_is_pure(self, gameweek_file: Path) -> None:
        fixtures = FileFixtureProvider(gameweek_file).get_all_fixtures()
        assert len(candidates_for_broadcast(fixtures, "2026-08-22")) == 2
