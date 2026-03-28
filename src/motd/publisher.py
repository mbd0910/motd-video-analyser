"""Publisher module — uploads analysis JSON to Cloudflare R2.

Serialises EpisodeAnalysis to JSON, uploads to a predictable R2 path,
and maintains an episode index file.
"""

from __future__ import annotations

from motd.models import EpisodeAnalysis


def publish(analysis: EpisodeAnalysis) -> str:
    """Publish an episode analysis to Cloudflare R2.

    Args:
        analysis: Validated episode analysis to publish.

    Returns:
        Public URL of the published analysis JSON.
    """
    raise NotImplementedError("Publisher not yet implemented — see issue #21")
