"""Tests for studio roster loading and the publish-time join."""

import json

import pytest
from pydantic import ValidationError

from motd.models import (
    Credit,
    EpisodeAnalysis,
    EpisodeMetadata,
    EpisodeRoster,
    MatchCoverage,
    PublishedEpisode,
    RosterOverride,
)
from motd.roster import RosterBook, RosterError, from_credits, roster_path_for_season

VALID = {
    "season": "2026-27",
    "episodes": {
        "motd_2026-27_2026-08-22": {
            "presenter": "Mark Chapman",
            "pundits": ["Alan Shearer", "Wayne Rooney"],
        },
        "motd_2026-27_2026-08-23": {
            "presenter": "Gabby Logan",
            "pundits": ["Danny Murphy", "Joe Hart"],
            "guests": ["Dean Holden"],
        },
    },
}


def write_roster(tmp_path, payload):
    path = tmp_path / "motd_2026_27.json"
    path.write_text(json.dumps(payload))
    return path


class TestEpisodeRoster:
    def test_pundits_and_guests_are_optional(self) -> None:
        roster = EpisodeRoster(presenter="Mark Chapman")
        assert roster.pundits == []
        assert roster.guests == []

    def test_presenter_is_required(self) -> None:
        with pytest.raises(ValidationError):
            EpisodeRoster.model_validate({"pundits": ["Alan Shearer"]})

    def test_blank_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EpisodeRoster(presenter="Mark Chapman", pundits=["  "])

    def test_same_person_twice_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EpisodeRoster(presenter="Mark Chapman", pundits=["Alan Shearer", "Alan Shearer"])

    def test_presenter_cannot_also_be_a_pundit(self) -> None:
        with pytest.raises(ValidationError):
            EpisodeRoster(presenter="Mark Chapman", pundits=["Mark Chapman"])


class TestRosterBook:
    def test_loads_and_looks_up_by_episode(self, tmp_path) -> None:
        book = RosterBook.load(write_roster(tmp_path, VALID))
        entry = book.get("motd_2026-27_2026-08-22")
        assert entry is not None
        assert entry.presenter == "Mark Chapman"
        assert entry.pundits == ["Alan Shearer", "Wayne Rooney"]
        assert book.get("motd_2026-27_2026-09-05") is None

    def test_episode_ids_are_sorted(self, tmp_path) -> None:
        book = RosterBook.load(write_roster(tmp_path, VALID))
        assert book.episode_ids() == [
            "motd_2026-27_2026-08-22",
            "motd_2026-27_2026-08-23",
        ]

    def test_missing_file_is_an_error(self, tmp_path) -> None:
        with pytest.raises(RosterError, match="not found"):
            RosterBook.load(tmp_path / "absent.json")

    def test_malformed_json_is_an_error(self, tmp_path) -> None:
        path = tmp_path / "motd_2026_27.json"
        path.write_text("{not json")
        with pytest.raises(RosterError, match="Malformed JSON"):
            RosterBook.load(path)

    def test_missing_top_level_keys_rejected(self, tmp_path) -> None:
        with pytest.raises(RosterError, match="'season' and 'episodes'"):
            RosterBook.load(write_roster(tmp_path, {"episodes": {}}))

    def test_unparseable_episode_id_rejected(self, tmp_path) -> None:
        payload = {"season": "2026-27", "episodes": {"22 August": {"presenter": "X"}}}
        with pytest.raises(RosterError, match="Invalid episode_id"):
            RosterBook.load(write_roster(tmp_path, payload))

    def test_episode_from_another_season_rejected(self, tmp_path) -> None:
        payload = {
            "season": "2026-27",
            "episodes": {"motd_2025-26_2025-11-01": {"presenter": "Mark Chapman"}},
        }
        with pytest.raises(RosterError, match="file declares"):
            RosterBook.load(write_roster(tmp_path, payload))

    def test_invalid_entry_names_the_episode(self, tmp_path) -> None:
        payload = {
            "season": "2026-27",
            "episodes": {"motd_2026-27_2026-08-22": {"pundits": "Alan Shearer"}},
        }
        with pytest.raises(RosterError, match="motd_2026-27_2026-08-22"):
            RosterBook.load(write_roster(tmp_path, payload))

    def test_guests_only_entry_is_valid(self, tmp_path) -> None:
        """The common case now BBC supplies the rest: a guest they never credit."""
        payload = {
            "season": "2026-27",
            "episodes": {"motd_2026-27_2026-08-23": {"guests": ["Dean Holden"]}},
        }
        book = RosterBook.load(write_roster(tmp_path, payload))
        entry = book.get("motd_2026-27_2026-08-23")
        assert entry is not None
        assert entry.guests == ["Dean Holden"]
        assert entry.presenter is None


def _metadata(credits: list[tuple[str, str]]) -> EpisodeMetadata:
    return EpisodeMetadata(
        episode_id="motd_2026-27_2026-08-23",
        broadcast_date="2026-08-23",
        season="2026-27",
        programme_pid="m0030qgb",
        version_pid="m0030qga",
        title="Match of the Day",
        subtitle="23/08/2026",
        first_broadcast="2026-08-23T22:30:00+01:00",
        duration_seconds=3540,
        credits=[Credit(role=role, name=name) for role, name in credits],
        fetched_at="2026-08-24T09:00:00+00:00",
    )


BBC_CREDITS = [
    ("Presenter", "Gabby Logan"),
    ("Expert", "Danny Murphy"),
    ("Expert", "Joe Hart"),
    ("Editor", "Andy Fraser"),
    ("Producer", "Ian Finch"),
]


class TestRosterFromCredits:
    """Deriving a roster from BBC's credits, overlaid with the hand-entered file."""

    def test_expert_becomes_pundit_and_editor_is_carried(self) -> None:
        roster = from_credits(_metadata(BBC_CREDITS))
        assert roster is not None
        assert roster.presenter == "Gabby Logan"
        assert roster.pundits == ["Danny Murphy", "Joe Hart"]
        assert roster.editor == "Andy Fraser"

    def test_producer_is_not_a_pundit(self) -> None:
        roster = from_credits(_metadata(BBC_CREDITS))
        assert roster is not None
        assert "Ian Finch" not in roster.pundits

    def test_guests_come_only_from_the_hand_entered_file(self) -> None:
        """BBC credits no guests at all, so nothing derived can supply one."""
        assert from_credits(_metadata(BBC_CREDITS)).guests == []
        roster = from_credits(
            _metadata(BBC_CREDITS), RosterOverride(guests=["Dean Holden"])
        )
        assert roster is not None
        assert roster.guests == ["Dean Holden"]

    def test_override_replaces_a_wrong_credit(self) -> None:
        roster = from_credits(
            _metadata(BBC_CREDITS),
            RosterOverride(presenter="Mark Chapman", pundits=["Alan Shearer"]),
        )
        assert roster is not None
        assert roster.presenter == "Mark Chapman"
        assert roster.pundits == ["Alan Shearer"]

    def test_no_presenter_credited_yields_no_roster(self) -> None:
        assert from_credits(_metadata([("Editor", "Andy Fraser")])) is None

    def test_a_presenter_also_credited_as_expert_is_not_doubled(self) -> None:
        """EpisodeRoster rejects a repeated name, so the derivation must not create one."""
        roster = from_credits(
            _metadata([("Presenter", "Gabby Logan"), ("Expert", "Gabby Logan")])
        )
        assert roster is not None
        assert roster.pundits == []


class TestRosterPath:
    def test_season_label_becomes_underscores(self) -> None:
        assert roster_path_for_season("2026-27").name == "motd_2026_27.json"


class TestPublishedEpisode:
    def make_analysis(self) -> EpisodeAnalysis:
        return EpisodeAnalysis(
            episode_id="motd_2026-27_2026-08-22",
            broadcast_date="2026-08-22",
            season="2026-27",
            gameweek=1,
            matches=[MatchCoverage(fpl_code=2645203, order=1)],
        )

    def test_compose_carries_the_analysis_through(self) -> None:
        roster = EpisodeRoster(presenter="Mark Chapman", pundits=["Alan Shearer"])
        published = PublishedEpisode.compose(self.make_analysis(), roster)
        assert published.episode_id == "motd_2026-27_2026-08-22"
        assert published.matches[0].fpl_code == 2645203
        assert published.roster is not None
        assert published.roster.presenter == "Mark Chapman"

    def test_compose_without_a_roster(self) -> None:
        published = PublishedEpisode.compose(self.make_analysis(), None)
        assert published.roster is None

    def test_stored_analysis_has_no_roster_field(self) -> None:
        assert "roster" not in EpisodeAnalysis.model_fields


class TestSeasonRosterFile:
    """The committed file is data, so a typo in it should fail the suite."""

    def test_committed_file_loads(self, project_root) -> None:
        path = project_root / "data" / "rosters" / "motd_2026_27.json"
        book = RosterBook.load(path)
        assert book.season == "2026-27"
        assert book.episode_ids()
