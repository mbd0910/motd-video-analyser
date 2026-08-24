"""Tests for FPL fixture sync — payload mapping only, no network calls."""

import json
from pathlib import Path

import pytest

from motd.clubs import ClubDirectory
from motd.fpl import FplError, _build_fixture, _team_codes, _verify_club_codes

BOOTSTRAP = {
    "teams": [
        {"id": 1, "code": 3, "short_name": "ARS", "name": "Arsenal"},
        {"id": 7, "code": 1, "short_name": "MUN", "name": "Man Utd"},
        {"id": 12, "code": 9, "short_name": "COV", "name": "Coventry City"},
    ]
}


@pytest.fixture
def clubs(project_root: Path) -> ClubDirectory:
    return ClubDirectory.load(project_root / "data/teams/premier_league.json")


def raw_fixture(**overrides: object) -> dict:
    base = {
        "code": 2645195,
        "id": 1,
        "event": 1,
        "team_h": 1,
        "team_a": 7,
        "team_h_score": 3,
        "team_a_score": 0,
        "kickoff_time": "2026-08-21T19:00:00Z",
        "finished": True,
        "finished_provisional": True,
    }
    return {**base, **overrides}


class TestBuildFixture:
    def test_maps_fpl_payload_to_canonical_names_and_venue(self, clubs: ClubDirectory) -> None:
        f = _build_fixture(raw_fixture(), _team_codes(BOOTSTRAP), clubs)
        assert f["home_team"] == "Arsenal"
        assert f["away_team"] == "Manchester United"
        assert f["venue"] == "Emirates Stadium"
        assert f["gameweek"] == 1
        assert f["fpl_code"] == 2645195
        assert f["home_code"] == "ARS"
        assert f["away_code"] == "MUN"
        assert f["final_score"] == {"home": 3, "away": 0}

    def test_converts_utc_kickoff_to_uk_local_time(self, clubs: ClubDirectory) -> None:
        """19:00Z in August is a 20:00 BST kickoff — storing UTC would misdate late games."""
        f = _build_fixture(raw_fixture(), _team_codes(BOOTSTRAP), clubs)
        assert f["date"] == "2026-08-21"
        assert f["kickoff"] == "20:00"

    def test_late_kickoff_keeps_uk_calendar_date(self, clubs: ClubDirectory) -> None:
        f = _build_fixture(
            raw_fixture(kickoff_time="2026-12-26T23:30:00Z"), _team_codes(BOOTSTRAP), clubs
        )
        assert f["date"] == "2026-12-26"
        assert f["kickoff"] == "23:30"

    def test_match_id_is_derived_from_date_and_codes(self, clubs: ClubDirectory) -> None:
        f = _build_fixture(raw_fixture(), _team_codes(BOOTSTRAP), clubs)
        assert f["match_id"] == "2026-08-21-ARS-MUN"

    def test_unplayed_fixture_has_no_score(self, clubs: ClubDirectory) -> None:
        f = _build_fixture(
            raw_fixture(
                finished=False,
                finished_provisional=False,
                team_h_score=None,
                team_a_score=None,
            ),
            _team_codes(BOOTSTRAP),
            clubs,
        )
        assert f["played"] is False
        assert f["final_score"] is None

    def test_provisional_finish_counts_as_played(self, clubs: ClubDirectory) -> None:
        """finished waits on bonus points; the match itself is over and scored."""
        f = _build_fixture(
            raw_fixture(finished=False, finished_provisional=True), _team_codes(BOOTSTRAP), clubs
        )
        assert f["played"] is True
        assert f["final_score"] == {"home": 3, "away": 0}

    def test_unknown_club_code_is_rejected(self, clubs: ClubDirectory) -> None:
        codes = {**_team_codes(BOOTSTRAP), 99: "XYZ"}
        with pytest.raises(KeyError, match="XYZ"):
            _build_fixture(raw_fixture(team_a=99), codes, clubs)

    def test_missing_kickoff_time_is_rejected(self, clubs: ClubDirectory) -> None:
        with pytest.raises(FplError, match="no kickoff time"):
            _build_fixture(raw_fixture(kickoff_time=None), _team_codes(BOOTSTRAP), clubs)


class TestTeamCodes:
    def test_malformed_bootstrap_is_rejected(self) -> None:
        with pytest.raises(FplError, match="bootstrap-static"):
            _team_codes({"teams": [{"id": 1}]})


class TestVerifyClubCodes:
    """The directory's club ids must agree with the live payload before a sync writes."""

    def test_matching_codes_pass(self, clubs: ClubDirectory) -> None:
        _verify_club_codes(BOOTSTRAP, clubs)

    def test_disagreeing_code_is_rejected(self, clubs: ClubDirectory) -> None:
        drifted = {"teams": [{"id": 1, "code": 999, "short_name": "ARS", "name": "Arsenal"}]}
        with pytest.raises(FplError, match="Arsenal has fpl_code 3 but FPL reports 999"):
            _verify_club_codes(drifted, clubs)

    def test_club_without_a_code_names_the_value_to_add(self, clubs: ClubDirectory) -> None:
        """Burnley is kept for history and has no code — a promotion looks the same."""
        promoted = {"teams": [{"id": 1, "code": 90, "short_name": "BUR", "name": "Burnley"}]}
        with pytest.raises(FplError, match='Add "fpl_code": 90'):
            _verify_club_codes(promoted, clubs)


class TestClubDirectory:
    def test_resolves_every_alternate_code(self, clubs: ClubDirectory) -> None:
        assert clubs.by_code("MUN").full == "Manchester United"
        assert clubs.by_code("MNU").full == "Manchester United"

    def test_unknown_code_names_the_file_to_fix(self, clubs: ClubDirectory) -> None:
        with pytest.raises(KeyError, match="premier_league.json"):
            clubs.by_code("ZZZ")

    def test_missing_file_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ClubDirectory.load(tmp_path / "nope.json")

    def test_directory_covers_synced_fixtures(self, project_root: Path) -> None:
        """A promoted club missing here would silently break the next sync."""
        directory = ClubDirectory.load(project_root / "data/teams/premier_league.json")
        path = project_root / "data/fixtures/premier_league_2026_27.json"
        teams = json.loads(path.read_text())["fixtures"]
        assert teams, "expected synced fixtures"
        for fixture in teams:
            assert fixture["venue"], fixture["match_id"]
            assert directory.by_code(fixture["home_code"]).fpl_code
        assert {"COV", "HUL", "IPS"} <= directory.codes()
