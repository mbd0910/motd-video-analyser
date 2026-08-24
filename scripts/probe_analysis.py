"""Run the analysis prompt against the live API and print what came back.

Reaches past `motd analyse` to show the parts it discards — thinking, token counts,
the raw reply — which is what you need when a prompt or schema change has to be
judged rather than just run. Makes one billed API call per effort level.

    uv run python scripts/probe_analysis.py EPISODE_ID [EFFORT ...]
"""

from __future__ import annotations

import json
import sys

import anthropic
from anthropic.types import OutputConfigParam
from dotenv import find_dotenv, load_dotenv

from motd.analyser import MAX_TOKENS, _build_prompt, _build_schema, _content_blocks, fixture_label
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

    prompt = _build_prompt(transcript, candidates, episode_id, ep.broadcast_date, ep.season)
    schema = _build_schema(sorted(fixture_label(f) for f in candidates))
    by_label = {fixture_label(f): f for f in candidates}
    client = anthropic.Anthropic()

    for effort in efforts:
        output_config: OutputConfigParam = {
            "effort": effort,  # type: ignore[typeddict-item]  # argv is unvalidated
            "format": {"type": "json_schema", "schema": schema},
        }
        with client.messages.stream(
            model="claude-opus-5",
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config=output_config,
            # Caching off: changing effort invalidates the prefix, so a sweep never hits.
            messages=[{"role": "user", "content": _content_blocks(prompt, None)}],
        ) as stream:
            response = stream.get_final_message()

        thinking = "".join(b.thinking for b in response.content if b.type == "thinking")
        text = next((b.text for b in response.content if b.type == "text"), "")
        (ep.cache_dir / f"probe_{effort}.json").write_text(text)
        (ep.cache_dir / f"probe_{effort}.thinking.txt").write_text(thinking)

        usage = response.usage
        print(f"\n{'=' * 78}")
        print(
            f"{episode_id}  effort={effort}  stop={response.stop_reason}  "
            f"in={usage.input_tokens} out={usage.output_tokens} thinking={len(thinking)} chars"
        )
        _report(text, by_label, len(candidates))

    return 0


def _report(text: str, by_label: dict, candidate_count: int) -> None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  unparseable: {exc}\n{text[:500]}")
        return

    # Key order is the point of the walkthrough field, so show it rather than assume it.
    print(f"  emitted keys: {list(data)}")
    picks = data.get("running_order", [])
    print(f"  matches: {len(picks)} of {candidate_count} candidates")
    def span(seg: dict, key: str) -> str:
        value = seg.get(key) or {}
        start, end = value.get("start"), value.get("end")
        return f"{start}-{end}" if start or end else "-"

    for pick in picks:
        seg = pick.get("segments", {})
        label = pick.get("match", "?")
        unknown = "" if label in by_label else "  <-- NOT A CANDIDATE"
        print(
            f"   {pick.get('order')}. {label:<44} "
            f"{span(seg, 'studio_intro'):<13} {span(seg, 'highlights'):<15} "
            f"{span(seg, 'studio_analysis'):<15}{unknown}"
        )
        if pick.get("notes"):
            print(f"      notes: {pick['notes']}")
    if walkthrough := data.get("walkthrough"):
        print(f"  walkthrough:\n    {walkthrough}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:] or ["xhigh"]))
