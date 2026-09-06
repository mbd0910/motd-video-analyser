"""Run the analysis prompt against the live API and print what came back.

Reaches past `motd analyse` to show the parts it discards — thinking, token counts,
the raw reply — which is what you need when a prompt or schema change has to be
judged rather than just run. One billed API call per match per effort level.

    uv run python scripts/probe_analysis.py EPISODE_ID [EFFORT ...]
"""

from __future__ import annotations

import json
import sys

import anthropic
from anthropic.types import OutputConfigParam
from dotenv import find_dotenv, load_dotenv

from motd.analyser import (
    MAX_TOKENS,
    SEGMENT_KEYS,
    _build_context,
    _build_schema,
    _build_task,
    _content_blocks,
    _normalise,
    fixture_label,
)
from motd.analyser import Prompt as AnalysisPrompt
from motd.episode import Episode
from motd.fixtures import FileFixtureProvider, fixtures_path_for_season
from motd.models import Transcript


def main(episode_id: str, efforts: list[str]) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ep = Episode.from_id(episode_id)
    if not ep.transcript_path.exists():
        print(f"No transcript at {ep.transcript_path}", file=sys.stderr)
        return 1

    transcript = Transcript.model_validate_json(ep.transcript_path.read_text())
    candidates = FileFixtureProvider(
        fixtures_path_for_season(ep.season)
    ).get_candidates(ep.broadcast_date)
    if not candidates:
        print(f"No candidate fixtures for {ep.broadcast_date}", file=sys.stderr)
        return 1

    context = _build_context(
        transcript, candidates, episode_id, ep.broadcast_date, ep.season
    )
    haystack = _normalise(" ".join(seg.text for seg in transcript.segments))
    schema = _build_schema()
    client = anthropic.Anthropic()

    for effort in efforts:
        output_config: OutputConfigParam = {
            "effort": effort,  # type: ignore[typeddict-item]  # argv is unvalidated
            "format": {"type": "json_schema", "schema": schema},
        }
        print(f"\n{'=' * 78}\n{episode_id}  effort={effort}")
        located = []
        for fixture in candidates:
            prompt = AnalysisPrompt(context=context, task=_build_task(fixture))
            with client.messages.stream(
                model="claude-opus-5",
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive", "display": "summarized"},
                output_config=output_config,
                # Caching on: every match after the first reads the same transcript,
                # which is the point of splitting the prompt where it is split.
                messages=[{"role": "user", "content": _content_blocks(prompt, "5m")}],
            ) as stream:
                response = stream.get_final_message()

            thinking = "".join(b.thinking for b in response.content if b.type == "thinking")
            text = next((b.text for b in response.content if b.type == "text"), "")
            label = fixture_label(fixture)
            slug = f"{fixture.home_code}-{fixture.away_code}"
            (ep.cache_dir / f"probe_{effort}_{slug}.json").write_text(text)
            (ep.cache_dir / f"probe_{effort}_{slug}.thinking.txt").write_text(thinking)
            located.append((label, _report(text, haystack, response.usage)))

        print(f"\n  running order ({sum(1 for _, s in located if s is not None)} located):")
        for position, (label, start) in enumerate(
            sorted((pair for pair in located if pair[1] is not None), key=lambda kv: kv[1]), 1
        ):
            print(f"   {position}. {start}  {label}")
        for label, start in located:
            if start is None:
                print(f"   -- {label}  NOT LOCATED")

    return 0


def _report(text: str, haystack: str, usage: object) -> str | None:
    """Print one match's reply and return the timestamp it starts at, if any."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  unparseable: {exc}\n{text[:500]}")
        return None

    spans = {
        key: data.get(key) or {}
        for key in SEGMENT_KEYS
        if (data.get(key) or {}).get("start") or (data.get(key) or {}).get("end")
    }
    quote = _normalise(str(data.get("handover", "")))
    cited = "no quote" if not quote else ("verified" if quote in haystack else "NOT IN TRANSCRIPT")
    timings = "  ".join(
        f"{key}={span.get('start') or '-'}-{span.get('end') or '-'}"
        for key, span in spans.items()
    )
    print(
        f"  out={usage.output_tokens} cache_read={usage.cache_read_input_tokens}  "  # type: ignore[attr-defined]
        f"quote={cited}\n    {timings or 'not located'}"
    )
    if data.get("notes"):
        print(f"    notes: {data['notes']}")
    for key in SEGMENT_KEYS:
        span = spans.get(key)
        if span and span.get("start"):
            return str(span["start"])
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:] or ["xhigh"]))
