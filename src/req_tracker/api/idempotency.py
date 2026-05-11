"""Idempotency helpers for command APIs."""

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel

from req_tracker.api.state import RuntimeState
from req_tracker.debug.hash import stable_hash


@dataclass(frozen=True)
class IdempotencyContext:
    """Resolved idempotency metadata for one command request."""

    key: str | None
    record_id: str | None
    request_hash: str
    cached_response: dict[str, Any] | None = None


def explicit_model_payload(model: BaseModel) -> dict[str, Any]:
    """Return only fields explicitly supplied by the caller."""
    return model.model_dump(include=model.model_fields_set, mode="json")


def prepare_idempotency(
    *,
    request: Request,
    runtime: RuntimeState,
    command: str,
    payload: Any,
) -> IdempotencyContext:
    """Resolve idempotency state and return cached response or raise on conflict."""
    request_hash = stable_hash(payload)
    key = idempotency_key(request)
    if key is None:
        return IdempotencyContext(
            key=None,
            record_id=None,
            request_hash=request_hash,
        )
    record_id = idempotency_record_id(command, key)
    existing = runtime.idempotency_results.get(record_id)
    if existing is None:
        return IdempotencyContext(
            key=key,
            record_id=record_id,
            request_hash=request_hash,
        )
    if existing.get("request_hash") != request_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "idempotency key reused with different request",
                "idempotency_key": key,
            },
        )
    response = existing.get("response")
    if not isinstance(response, dict):
        raise HTTPException(status_code=500, detail="invalid idempotency record")
    return IdempotencyContext(
        key=key,
        record_id=record_id,
        request_hash=request_hash,
        cached_response=response,
    )


def record_idempotency_response(
    *,
    runtime: RuntimeState,
    context: IdempotencyContext,
    command: str,
    project_key: str | None,
    response: dict[str, Any],
) -> None:
    """Persist a command response when an idempotency key was supplied."""
    if context.key is None or context.record_id is None:
        return
    runtime.record_idempotency_result(
        record_id=context.record_id,
        idempotency_key=context.key,
        command=command,
        project_key=project_key,
        request_hash=context.request_hash,
        response=response,
    )


def idempotency_key(request: Request) -> str | None:
    """Read normalized idempotency key from supported headers."""
    key = request.headers.get("idempotency-key") or request.headers.get("x-idempotency-key")
    if key is None:
        return None
    normalized = key.strip()
    return normalized or None


def idempotency_record_id(command: str, key: str) -> str:
    """Return a stable idempotency record identifier."""
    return f"{command}:{key}"
