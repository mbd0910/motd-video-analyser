"""Tests for BBC programme metadata — pid resolution, credits scraping, storage."""

import pytest

from motd.models import ContentWindow, Credit, EpisodeMetadata
from motd.programme import (
    ProgrammeError,
    _broadcast_date,
    _content_window,
    extract_pid,
    load,
    metadata_path_for_episode,
    parse_credits,
    save,
)

# Trimmed from a real /programmes page: the id-bearing container, a visually-hidden
# header row, and cells whose text sits inside a span with whitespace either side.
CREDITS_HTML = """
<div class="component component--box" id="credits">
  <div class="component__header"><h2>Credits</h2></div>
  <div class="component__body">
    <table class="table table--slatted-vertical">
      <thead class="visually-hidden"><tr><th>Role</th><th>Contributor</th></tr></thead>
      <tbody>
        <tr>
          <td class="br-subtle-bg-onborder">
              <span>Presenter</span>
          </td>
          <td class="br-subtle-bg-onborder">
              <span>Gabby Logan</span>
          </td>
        </tr>
        <tr>
          <td><span>Expert</span></td>
          <td><span>Danny Murphy</span></td>
        </tr>
        <tr>
          <td><span>Editor</span></td>
          <td><span>Richard Hughes</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
<div id="broadcasts">
  <table><tbody><tr><td><span>BBC One</span></td><td><span>22:30</span></td></tr></tbody></table>
</div>
"""


class TestExtractPid:
    def test_pulls_the_pid_out_of_an_iplayer_url(self) -> None:
        url = "https://www.bbc.co.uk/iplayer/episode/m0031b9y/match-of-the-day-05092026"
        assert extract_pid(url) == "m0031b9y"

    def test_accepts_a_bare_pid(self) -> None:
        assert extract_pid("m0031b9y") == "m0031b9y"

    def test_accepts_a_programmes_url(self) -> None:
        assert extract_pid("https://www.bbc.co.uk/programmes/b007t9y1") == "b007t9y1"

    def test_rejects_a_string_with_no_pid(self) -> None:
        with pytest.raises(ProgrammeError, match="No BBC programme id"):
            extract_pid("match-of-the-day")


class TestParseCredits:
    def test_reads_role_and_contributor_pairs(self) -> None:
        credits = parse_credits(CREDITS_HTML)
        assert [(c.role, c.name) for c in credits] == [
            ("Presenter", "Gabby Logan"),
            ("Expert", "Danny Murphy"),
            ("Editor", "Richard Hughes"),
        ]

    def test_stops_at_the_end_of_the_credits_table(self) -> None:
        """The broadcasts table that follows must not be read as more credits."""
        assert all(c.name != "BBC One" for c in parse_credits(CREDITS_HTML))

    def test_a_page_without_credits_yields_none(self) -> None:
        assert parse_credits("<html><body><p>No credits here.</p></body></html>") == []

    def test_an_odd_cell_count_drops_the_tail_rather_than_pairing_wrongly(self) -> None:
        html = """
        <div id="credits"><table><tbody>
          <tr><td>Presenter</td><td>Gabby Logan</td></tr>
          <tr><td>Expert</td></tr>
        </tbody></table></div>
        """
        assert [(c.role, c.name) for c in parse_credits(html)] == [
            ("Presenter", "Gabby Logan")
        ]


class TestBroadcastDate:
    def test_takes_the_local_date_not_the_utc_one(self) -> None:
        """BBC stamps the offset; a late-night show would slip a day if read as UTC."""
        assert _broadcast_date("2026-09-05T22:30:00+01:00") == "2026-09-05"

    def test_rejects_a_truncated_timestamp(self) -> None:
        with pytest.raises(ProgrammeError, match="Unusable first_broadcast_date"):
            _broadcast_date("2026-09")


class TestContentWindow:
    def test_reads_the_uas_playback_events(self) -> None:
        window = _content_window({"events": [
            {"name": "started", "offset": 30, "system": "uas"},
            {"name": "ended", "offset": 5225, "system": "uas"},
        ]})
        assert window == ContentWindow(start_seconds=30.0, end_seconds=5225.0)
        assert window.duration_seconds == 5195.0

    def test_ignores_events_from_other_systems(self) -> None:
        """Optimizely and dax emit their own offsets against different definitions."""
        assert _content_window({"events": [
            {"name": "started", "offset": 30, "system": "optimizely"},
            {"name": "ended", "offset": 4811, "system": "dax"},
        ]}) is None

    def test_absent_events_yield_no_window(self) -> None:
        assert _content_window({}) is None

    def test_a_backwards_window_is_refused(self) -> None:
        assert _content_window({"events": [
            {"name": "started", "offset": 500, "system": "uas"},
            {"name": "ended", "offset": 30, "system": "uas"},
        ]}) is None


def _record(**overrides) -> EpisodeMetadata:
    fields = {
        "episode_id": "motd_2026-27_2026-09-05",
        "broadcast_date": "2026-09-05",
        "season": "2026-27",
        "programme_pid": "m0031b9y",
        "version_pid": "m0031b9x",
        "title": "Match of the Day",
        "subtitle": "05/09/2026",
        "first_broadcast": "2026-09-05T22:30:00+01:00",
        "duration_seconds": 5340,
        "credits": [
            Credit(role="Presenter", name="Gabby Logan"),
            Credit(role="Expert", name="Danny Murphy"),
        ],
        "fetched_at": "2026-09-06T09:00:00+00:00",
    }
    return EpisodeMetadata(**{**fields, **overrides})


class TestStorage:
    def test_save_then_load_round_trips(self, tmp_path) -> None:
        save(_record(), metadata_dir=tmp_path)
        loaded = load("motd_2026-27_2026-09-05", metadata_dir=tmp_path)
        assert loaded is not None
        assert loaded.version_pid == "m0031b9x"
        assert loaded.named_for_role("Presenter") == ["Gabby Logan"]

    def test_load_of_an_unfetched_episode_is_none(self, tmp_path) -> None:
        assert load("motd_2026-27_2026-09-05", metadata_dir=tmp_path) is None

    def test_malformed_stored_metadata_is_an_error(self, tmp_path) -> None:
        (tmp_path / "motd_2026-27_2026-09-05.json").write_text("{not json")
        with pytest.raises(ProgrammeError, match="Malformed metadata"):
            load("motd_2026-27_2026-09-05", metadata_dir=tmp_path)

    def test_path_is_keyed_on_episode_id(self) -> None:
        path = metadata_path_for_episode("motd_2026-27_2026-09-05")
        assert path.name == "motd_2026-27_2026-09-05.json"


class TestNamedForRole:
    def test_role_match_is_case_insensitive(self) -> None:
        assert _record().named_for_role("presenter") == ["Gabby Logan"]

    def test_an_uncredited_role_is_empty(self) -> None:
        assert _record().named_for_role("Editor") == []
