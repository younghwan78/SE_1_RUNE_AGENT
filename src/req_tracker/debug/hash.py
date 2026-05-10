"""Stable hashing helpers for traces and artifacts."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for supported values."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    """Return a sha256 hash for JSON-serializable values."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

