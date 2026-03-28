"""Pipeline orchestrator — sequences all stages of the MOTD analysis pipeline.

Stages: Download (optional) → Transcribe → Analyse → Publish
"""

from __future__ import annotations


def run(
    video_path: str | None = None,
    url: str | None = None,
    episode_id: str | None = None,
    skip_to: str | None = None,
) -> None:
    """Run the full analysis pipeline.

    Args:
        video_path: Path to a local video file (skip download).
        url: BBC iPlayer URL (triggers download first).
        episode_id: Episode ID for re-running specific stages.
        skip_to: Stage to skip to (e.g. "analyse").
    """
    raise NotImplementedError("Pipeline not yet implemented — see issue #24")
