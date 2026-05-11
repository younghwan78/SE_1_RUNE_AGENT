"""Local artifact store used by debug traces and replay."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from req_tracker.debug.hash import stable_hash
from req_tracker.debug.models import StageArtifactRef


class ArtifactAccessError(PermissionError):
    """Raised when an artifact reference is outside the configured store root."""


class LocalArtifactStore:
    """Persist JSON artifacts under a local root directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write_json(self, run_id: str, name: str, payload: Any) -> StageArtifactRef:
        """Write a JSON payload and return its reference."""
        normalized = self._to_jsonable(payload)
        content_hash = stable_hash(normalized)
        path = self.root / "runs" / run_id / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return StageArtifactRef(
            artifact_ref=str(path.as_posix()),
            content_hash=content_hash,
            media_type="application/json",
        )

    def read_json(self, artifact_ref: str) -> Any:
        """Read a JSON artifact by reference."""
        path = self._resolve_ref(artifact_ref)
        return json.loads(path.read_text(encoding="utf-8"))

    def _resolve_ref(self, artifact_ref: str) -> Path:
        """Resolve an artifact reference and ensure it stays under the store root."""
        root = self.root.resolve()
        path = Path(artifact_ref).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ArtifactAccessError("artifact ref is outside artifact store root") from exc
        return path

    @staticmethod
    def _to_jsonable(payload: Any) -> Any:
        if isinstance(payload, BaseModel):
            return payload.model_dump(mode="json")
        if isinstance(payload, list):
            return [LocalArtifactStore._to_jsonable(item) for item in payload]
        if isinstance(payload, dict):
            return {
                str(key): LocalArtifactStore._to_jsonable(value)
                for key, value in payload.items()
            }
        return payload
