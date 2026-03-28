"""Cache management for episode pipeline artefacts.

Provides get_or_compute (cache-or-run) and load (read-only) functions
that hide serialisation, existence checks, and force-overwrite logic.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_or_compute(
    path: Path,
    model_type: type[T],
    compute: Callable[[], T],
    *,
    force: bool = False,
) -> tuple[T, bool]:
    """Return cached artefact or compute and cache it.

    Args:
        path: Cache file path.
        model_type: Pydantic model class for deserialisation.
        compute: Zero-arg callable invoked on cache miss or force=True.
        force: If True, always call compute and overwrite.

    Returns:
        (result, was_computed) — the model instance, and whether compute ran.
    """
    if path.exists() and not force:
        logger.info("Cache hit: %s", path)
        return model_type.model_validate_json(path.read_text()), False

    logger.info("Cache miss: %s (force=%s)", path, force)
    result = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2))
    logger.info("Cached: %s", path)
    return result, True


def load(path: Path, model_type: type[T]) -> T | None:  # noqa: UP047
    """Load from cache without computing. Returns None on miss."""
    if not path.exists():
        return None
    return model_type.model_validate_json(path.read_text())
