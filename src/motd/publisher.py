"""Publisher module — uploads analysis JSON to Cloudflare R2.

Serialises EpisodeAnalysis to JSON, uploads to a predictable R2 path,
and maintains an episode index file.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import boto3

from motd.models import EpisodeAnalysis

logger = logging.getLogger(__name__)

EPISODES_PREFIX = "episodes"
INDEX_KEY = f"{EPISODES_PREFIX}/index.json"


class R2Client(Protocol):
    """Protocol for R2/S3-compatible object storage."""

    def upload(self, key: str, data: bytes, content_type: str = "application/json") -> None: ...
    def download(self, key: str) -> bytes | None: ...


class CloudflareR2Client:
    """Cloudflare R2 client using boto3 S3-compatible API."""

    def __init__(
        self,
        bucket: str | None = None,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self.bucket = bucket or os.environ["R2_BUCKET"]
        account_id = account_id or os.environ["R2_ACCOUNT_ID"]
        access_key_id = access_key_id or os.environ["R2_ACCESS_KEY_ID"]
        secret_access_key = secret_access_key or os.environ["R2_SECRET_ACCESS_KEY"]

        self._s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def upload(self, key: str, data: bytes, content_type: str = "application/json") -> None:
        self._s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def download(self, key: str) -> bytes | None:
        try:
            response = self._s3.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()  # type: ignore[no-any-return]
        except self._s3.exceptions.NoSuchKey:
            return None


def _build_index_entry(analysis: EpisodeAnalysis) -> dict[str, object]:
    """Build an index entry from an episode analysis."""
    return {
        "episode_id": analysis.episode_id,
        "broadcast_date": analysis.broadcast_date,
        "season": analysis.season,
        "match_count": len(analysis.matches),
    }


def _update_index(
    existing: list[dict[str, object]],
    entry: dict[str, object],
) -> list[dict[str, object]]:
    """Upsert an entry into the episode index (no duplicates)."""
    result = [e for e in existing if e["episode_id"] != entry["episode_id"]]
    result.append(entry)
    return result


def publish(analysis: EpisodeAnalysis, client: R2Client | None = None) -> str:
    """Publish an episode analysis to Cloudflare R2.

    Args:
        analysis: Validated episode analysis to publish.
        client: R2 client (defaults to CloudflareR2Client from env vars).

    Returns:
        Key path of the published analysis JSON.
    """
    if client is None:
        client = CloudflareR2Client()

    episode_key = f"{EPISODES_PREFIX}/{analysis.episode_id}.json"

    # Upload episode JSON
    episode_json = analysis.model_dump_json(indent=2).encode()
    logger.info("Uploading %s (%d bytes)", episode_key, len(episode_json))
    client.upload(episode_key, episode_json)

    # Read-modify-write the index
    existing_index: list[dict[str, object]] = []
    index_data = client.download(INDEX_KEY)
    if index_data is not None:
        try:
            parsed = json.loads(index_data)
            existing_index = parsed.get("episodes", [])
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupted index.json in R2 — rebuilding from scratch")
            existing_index = []

    entry = _build_index_entry(analysis)
    updated_index = _update_index(existing_index, entry)

    index_json = json.dumps({"episodes": updated_index}, indent=2).encode()
    logger.info("Updating index (%d episodes)", len(updated_index))
    client.upload(INDEX_KEY, index_json)

    return episode_key
