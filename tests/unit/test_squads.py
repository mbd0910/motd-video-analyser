"""Tests for the squad lookup."""

import json

import pytest

from motd.squads import MIN_NAME_CHARS, SquadError, SquadIndex, squads_path_for_season

SQUADS = {
    "ARS": ["Saka", "Ødegaard", "Rice"],
    "CHE": ["Palmer", "Rice", "Cole"],
    "BRE": ["Janelt", "Lewis-Potter"],
}


def index() -> SquadIndex:
    return SquadIndex.from_squads(SQUADS)


class TestSquadsPath:
    def test_season_label_becomes_a_filename(self) -> None:
        assert squads_path_for_season("2026-27").name == "premier_league_2026_27.json"


class TestClubsNamedIn:
    def test_a_player_implicates_their_club(self) -> None:
        assert index().clubs_named_in("brilliant goal from Saka!") == {"ARS"}

    def test_commentary_naming_both_sides_implicates_both(self) -> None:
        named = index().clubs_named_in("Janelt squares it, Lewis-Potter finishes")
        assert named == {"BRE"}

    def test_a_surname_two_clubs_share_implicates_both(self) -> None:
        # The caller is asking whether a given match was on screen, and an ambiguous
        # hit still answers that — it is never the only name in a match's coverage.
        assert index().clubs_named_in("Rice wins it back") == {"ARS", "CHE"}

    def test_hyphenated_names_are_found(self) -> None:
        assert index().clubs_named_in("Lewis-Potter again") == {"BRE"}

    def test_a_name_spelled_without_its_diacritics_still_matches(self) -> None:
        # How the subtitles write it is not how FPL writes it, either way round.
        assert index().clubs_named_in("Ødegaard picks it up") == {"ARS"}
        assert index().clubs_named_in("Odegaard picks it up") == {"ARS"}
        folded = SquadIndex.from_squads({"NEW": ["Guimarães"], "MUN": ["Højlund"]})
        assert folded.clubs_named_in("Guimaraes drives forward") == {"NEW"}
        assert folded.clubs_named_in("Hojlund heads it in") == {"MUN"}

    def test_case_does_not_matter(self) -> None:
        assert index().clubs_named_in("SAKA!") == {"ARS"}

    def test_text_naming_nobody_implicates_nobody(self) -> None:
        assert index().clubs_named_in("Back to the studio after the break.") == set()

    def test_short_names_are_left_out_of_the_index(self) -> None:
        # "Cole" is four characters and stays; anything shorter collides with ordinary
        # words often enough that a hit would mean nothing.
        assert index().clubs_named_in("Cole") == {"CHE"}
        short = SquadIndex.from_squads({"ARS": ["Ely", "Saka"]})
        assert short.clubs_named_in("Ely") == set()
        assert MIN_NAME_CHARS == 4


class TestLoad:
    def test_a_missing_file_names_the_command_that_writes_it(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("motd.squads.SQUADS_DIR", tmp_path)
        with pytest.raises(SquadError, match="fixtures sync"):
            SquadIndex.load("2026-27")

    def test_a_file_that_is_not_squads_raises(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("motd.squads.SQUADS_DIR", tmp_path)
        (tmp_path / "premier_league_2026_27.json").write_text('{"season": "2026-27"}')
        with pytest.raises(SquadError, match="Unusable squads file"):
            SquadIndex.load("2026-27")

    def test_a_squads_file_loads(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("motd.squads.SQUADS_DIR", tmp_path)
        (tmp_path / "premier_league_2026_27.json").write_text(
            json.dumps({"season": "2026-27", "squads": SQUADS})
        )
        assert SquadIndex.load("2026-27").clubs_named_in("Saka") == {"ARS"}

    def test_squads_naming_nobody_raise_rather_than_pass_everything(self) -> None:
        with pytest.raises(SquadError, match="names no players"):
            SquadIndex.from_squads({"ARS": [], "CHE": []})
