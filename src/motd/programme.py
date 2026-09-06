"""BBC programme metadata — the broadcaster's own record of an episode.

Two sources, because neither is complete. `/programmes/{pid}.json` is a permanent
catalogue that outlives the iPlayer availability window and carries the broadcast
date, synopses and version pid; the iPlayer business layer carries the content
window and the availability deadline but is served only while the episode is up.
Credits are scraped from the `/programmes` page, which is the only place they appear.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from motd.episode import season_for_date
from motd.models import ContentWindow, Credit, EpisodeMetadata

logger = logging.getLogger(__name__)

METADATA_DIR = Path("data/metadata")

PROGRAMMES_URL = "https://www.bbc.co.uk/programmes/{pid}"
IBL_EPISODE_URL = "https://ibl.api.bbci.co.uk/ibl/v1/episodes/{pid}"

_USER_AGENT = "motd-analyser (+https://github.com/mbd0910/motd-video-analyser)"
_TIMEOUT_SECONDS = 30

_PID_RE = re.compile(r"\b([bmp]0[a-z0-9]{6})\b")


class ProgrammeError(Exception):
    """Raised when BBC metadata cannot be fetched or is unusable."""


def metadata_path_for_episode(episode_id: str) -> Path:
    return METADATA_DIR / f"{episode_id}.json"


def extract_pid(url_or_id: str) -> str:
    """Pull the programme pid out of an iPlayer URL, or validate a bare pid.

    Raises:
        ProgrammeError: If no pid-shaped token is present.
    """
    match = _PID_RE.search(url_or_id)
    if not match:
        raise ProgrammeError(
            f"No BBC programme id found in {url_or_id!r}. Expected a pid like m0031b9y "
            "or an iPlayer URL containing one."
        )
    return match.group(1)


def _get(url: str, *, as_json: bool) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ProgrammeError(f"BBC returned {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProgrammeError(f"Could not reach BBC at {url}: {exc}") from exc

    if not as_json:
        return body.decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProgrammeError(f"BBC returned malformed JSON for {url}") from exc


class _CreditsParser(HTMLParser):
    """Scrapes the role/contributor cells out of a `/programmes` credits table.

    Anchored on the `id="credits"` container rather than the "Credits" heading above
    it, and stops at the end of the one table inside — an id survives a redesign of
    the surrounding markup, and does not depend on the page being in English.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_credits = False
        self._done = False
        self._in_cell = False
        self._cell: list[str] = []
        self.cells: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        if not self._in_credits:
            self._in_credits = any(name == "id" and value == "credits" for name, value in attrs)
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if self._done or not self._in_credits:
            return
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            text = " ".join("".join(self._cell).split())
            if text:
                self.cells.append(text)
        elif tag == "table":
            self._done = True

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)


def parse_credits(page_html: str) -> list[Credit]:
    """Extract the credits table from a `/programmes` episode page.

    Returns an empty list when the page carries no credits — some episodes genuinely
    have none, and an episode's perishable artefacts are worth capturing regardless.
    """
    parser = _CreditsParser()
    parser.feed(page_html)
    cells = parser.cells

    # The table leads with its own "Role"/"Contributor" header row.
    if cells[:2] == ["Role", "Contributor"]:
        cells = cells[2:]
    if len(cells) % 2:
        logger.warning("Credits table has an odd cell count (%d) — dropping the tail", len(cells))
        cells = cells[:-1]

    return [
        Credit(role=role, name=name)
        for role, name in zip(cells[0::2], cells[1::2], strict=True)
    ]


def _broadcast_date(first_broadcast: str) -> str:
    """The calendar date an episode aired, in UK local time.

    `/programmes` stamps the offset (…+01:00), so the date component is already local.
    The iPlayer layer reports the same instant in UTC, which lands a late-night
    broadcast on the previous day — so this reads the `/programmes` field only.
    """
    if len(first_broadcast) < 10:
        raise ProgrammeError(f"Unusable first_broadcast_date: {first_broadcast!r}")
    return first_broadcast[:10]


def _content_window(ibl_version: dict[str, Any]) -> ContentWindow | None:
    """The programme proper, inside the file: after the trailer, before the credits.

    iPlayer emits these as playback events so its own client knows when an episode has
    genuinely been watched. Absent on some versions, hence optional.
    """
    offsets = {
        event.get("name"): event.get("offset")
        for event in ibl_version.get("events", [])
        if event.get("system") == "uas"
    }
    start, end = offsets.get("started"), offsets.get("ended")
    if start is None or end is None or end <= start:
        return None
    return ContentWindow(start_seconds=float(start), end_seconds=float(end))


def fetch(url_or_id: str) -> EpisodeMetadata:
    """Fetch BBC's record of an episode.

    The `/programmes` half is required; the iPlayer half is best-effort, because it
    stops answering once the episode's availability window closes while the rest
    stays fetchable indefinitely.

    Raises:
        ProgrammeError: If the programme pid is unusable or `/programmes` fails.
    """
    pid = extract_pid(url_or_id)

    payload = _get(PROGRAMMES_URL.format(pid=pid) + ".json", as_json=True)
    try:
        programme = payload["programme"]
        versions = programme["versions"]
        first_broadcast = programme["first_broadcast_date"]
    except (KeyError, TypeError) as exc:
        raise ProgrammeError(f"Unexpected /programmes shape for {pid}: {exc}") from exc

    if not versions:
        raise ProgrammeError(f"{pid} has no versions — it may not be a broadcast episode")

    broadcast_date = _broadcast_date(first_broadcast)
    season = season_for_date(broadcast_date)
    canonical = versions[0]

    page_html = _get(PROGRAMMES_URL.format(pid=pid), as_json=False)
    credits = parse_credits(page_html)
    if not credits:
        logger.warning("%s: /programmes page carries no credits table", pid)

    editorial_title, editorial_synopsis, content_window, available_until = None, None, None, None
    try:
        ibl = _get(IBL_EPISODE_URL.format(pid=pid), as_json=True)
        episode = ibl["episodes"][0]
        editorial_title = episode.get("editorial_title")
        editorial_synopsis = episode.get("synopses", {}).get("editorial")
        ibl_version = episode["versions"][0]
        content_window = _content_window(ibl_version)
        available_until = ibl_version.get("availability", {}).get("end")
    except (ProgrammeError, KeyError, IndexError, TypeError) as exc:
        logger.info("%s: no iPlayer record (episode likely expired): %s", pid, exc)

    return EpisodeMetadata(
        episode_id=f"motd_{season}_{broadcast_date}",
        broadcast_date=broadcast_date,
        season=season,
        programme_pid=pid,
        version_pid=canonical["pid"],
        title=programme.get("display_title", {}).get("title") or programme["title"],
        subtitle=programme["title"],
        editorial_title=editorial_title,
        first_broadcast=first_broadcast,
        duration_seconds=canonical["duration"],
        content_window=content_window,
        synopsis_short=programme.get("short_synopsis", ""),
        synopsis_medium=programme.get("medium_synopsis", ""),
        synopsis_long=programme.get("long_synopsis", ""),
        synopsis_editorial=editorial_synopsis,
        credits=credits,
        available_until=available_until,
        image_pid=(programme.get("image") or {}).get("pid"),
        fetched_at=datetime.now(UTC).isoformat(),
    )


def load(episode_id: str, metadata_dir: Path | None = None) -> EpisodeMetadata | None:
    """The stored metadata for an episode, or None if it has never been fetched."""
    path = (metadata_dir or METADATA_DIR) / f"{episode_id}.json"
    if not path.exists():
        return None
    try:
        return EpisodeMetadata.model_validate_json(path.read_text())
    except ValueError as exc:
        raise ProgrammeError(f"Malformed metadata in {path}: {exc}") from exc


def save(metadata: EpisodeMetadata, metadata_dir: Path | None = None) -> Path:
    """Write an episode's metadata to its committed path."""
    path = (metadata_dir or METADATA_DIR) / f"{metadata.episode_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata.model_dump_json(indent=2))
    return path
