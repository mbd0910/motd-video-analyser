"""Fixture sync from the Fantasy Premier League public API.

FPL serves only the season in progress — there is no archive endpoint and no
season parameter, so earlier seasons cannot be regenerated from here.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from motd.clubs import ClubDirectory
from motd.episode import season_for_date

FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"
BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

BROADCAST_TZ = ZoneInfo("Europe/London")

# FPL rejects the default urllib agent.
_USER_AGENT = "motd-analyser (+https://github.com/mbd0910/motd-video-analyser)"
_TIMEOUT_SECONDS = 30


class FplError(Exception):
    """Raised when the FPL API cannot be reached or returns unusable data."""


def _get(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise FplError(f"FPL API returned {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise FplError(f"Could not reach FPL API at {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise FplError(f"FPL API returned malformed JSON for {url}") from exc


def _team_codes(bootstrap: dict[str, Any]) -> dict[int, str]:
    try:
        return {team["id"]: team["short_name"] for team in bootstrap["teams"]}
    except (KeyError, TypeError) as exc:
        raise FplError(f"Unexpected bootstrap-static shape: {exc}") from exc


def _build_fixture(
    raw: dict[str, Any],
    team_codes: dict[int, str],
    clubs: ClubDirectory,
) -> dict[str, Any]:
    try:
        home_code = team_codes[raw["team_h"]]
        away_code = team_codes[raw["team_a"]]
        kickoff_utc = raw["kickoff_time"]
    except KeyError as exc:
        raise FplError(f"Fixture missing required field {exc}: {raw}") from exc

    if kickoff_utc is None:
        raise FplError(f"Fixture {raw.get('id')} has no kickoff time yet")

    home = clubs.by_code(home_code)
    away = clubs.by_code(away_code)
    local = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00")).astimezone(BROADCAST_TZ)
    date = local.strftime("%Y-%m-%d")

    # finished_provisional flips when the match ends; finished waits on bonus points.
    played = bool(raw.get("finished_provisional") or raw.get("finished"))
    score = None
    if played and raw.get("team_h_score") is not None:
        score = {"home": raw["team_h_score"], "away": raw["team_a_score"]}

    return {
        "match_id": f"{date}-{home_code}-{away_code}",
        "fpl_code": raw.get("code"),
        "gameweek": raw.get("event"),
        "date": date,
        "kickoff": local.strftime("%H:%M"),
        "home_team": home.full,
        "away_team": away.full,
        "venue": home.venue.stadium,
        "final_score": score,
        "played": played,
    }


def fetch_fixtures(clubs: ClubDirectory) -> dict[str, Any]:
    """Fetch the current season's fixtures and shape them into the on-disk document."""
    bootstrap = _get(BOOTSTRAP_URL)
    raw_fixtures = _get(FIXTURES_URL)
    if not raw_fixtures:
        raise FplError("FPL API returned no fixtures")

    team_codes = _team_codes(bootstrap)
    fixtures = [
        _build_fixture(raw, team_codes, clubs)
        for raw in raw_fixtures
        if raw.get("kickoff_time")
    ]
    fixtures.sort(key=lambda f: (f["date"], f["kickoff"], f["match_id"]))

    return {
        "season": season_for_date(fixtures[0]["date"]),
        "competition": "Premier League",
        "source": FIXTURES_URL,
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixtures": fixtures,
    }


def write_fixtures(document: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
