"""Admin APIs for controlled registry activation."""

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from req_tracker.api.idempotency import (
    explicit_model_payload,
    prepare_idempotency,
    record_idempotency_response,
)
from req_tracker.api.security import require_role
from req_tracker.model_gateway.models import ModelProfile, PromptVersion
from req_tracker.model_gateway.registry import ModelRegistry, ModelRegistryError

router = APIRouter(tags=["admin"])


class RegistryActivationRequest(BaseModel):
    """Required gates for activating a reviewed model registry item."""

    activated_by: str = "local"
    eval_passed: bool = False
    reviewer_approved: bool = False
    canary_passed: bool = False
    reason_code: str | None = None
    comment: str | None = None


@router.post("/admin/model-profiles/{model_profile_id}/activate")
def activate_model_profile(
    request: Request,
    model_profile_id: str,
    payload: RegistryActivationRequest,
) -> dict[str, Any]:
    """Record a controlled model profile activation decision."""
    user = require_role(request, "admin")
    runtime = request.app.state.runtime
    registry = _registry(request)
    try:
        profile = registry.get_profile(model_profile_id)
    except ModelRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _require_activation_gates(payload)
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="admin.model_profile.activate",
        payload={
            "model_profile_id": model_profile_id,
            "activation": explicit_model_payload(payload),
        },
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
    activation = _activation_record(
        activation_type="model_profile",
        item_id=model_profile_id,
        activated_by=payload.activated_by or user.user_id,
        payload=payload,
        item=profile,
    )
    runtime.record_registry_activation(
        activation_id=activation["activation_id"],
        activation=activation,
    )
    runtime.audit.record(
        action="model_profile_activated",
        actor_id=payload.activated_by or user.user_id,
        actor_role=user.role,
        target_type="model_profile",
        target_id=model_profile_id,
        reason_code=payload.reason_code,
        metadata={
            "provider": profile.provider,
            "model_name": profile.model_name,
            "endpoint_alias": profile.endpoint_alias,
            "comment": payload.comment,
        },
    )
    runtime.persist_approval_state()
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="admin.model_profile.activate",
        project_key=None,
        response=activation,
    )
    return activation


@router.post("/admin/prompt-versions/{prompt_version_id}/activate")
def activate_prompt_version(
    request: Request,
    prompt_version_id: str,
    payload: RegistryActivationRequest,
) -> dict[str, Any]:
    """Record a controlled prompt version activation decision."""
    user = require_role(request, "admin")
    runtime = request.app.state.runtime
    registry = _registry(request)
    try:
        prompt = registry.get_prompt(prompt_version_id)
    except ModelRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if prompt.status not in {"active", "canary"}:
        raise HTTPException(
            status_code=409,
            detail="prompt version must be canary or active before activation",
        )
    _require_activation_gates(payload)
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="admin.prompt_version.activate",
        payload={
            "prompt_version_id": prompt_version_id,
            "activation": explicit_model_payload(payload),
        },
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
    activation = _activation_record(
        activation_type="prompt_version",
        item_id=prompt_version_id,
        activated_by=payload.activated_by or user.user_id,
        payload=payload,
        item=prompt,
    )
    activation["task_name"] = prompt.task_name
    runtime.record_registry_activation(
        activation_id=activation["activation_id"],
        activation=activation,
    )
    runtime.audit.record(
        action="prompt_version_activated",
        actor_id=payload.activated_by or user.user_id,
        actor_role=user.role,
        target_type="prompt_version",
        target_id=prompt_version_id,
        reason_code=payload.reason_code,
        metadata={
            "task_name": prompt.task_name,
            "schema_version_ref": prompt.schema_version_ref,
            "retrieval_policy_id": prompt.retrieval_policy_id,
            "comment": payload.comment,
        },
    )
    runtime.persist_approval_state()
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="admin.prompt_version.activate",
        project_key=None,
        response=activation,
    )
    return activation


def _registry(request: Request) -> ModelRegistry:
    settings = request.app.state.settings
    return ModelRegistry.from_json_files(
        profiles_path=Path(settings.model_profiles_path),
        prompts_path=Path(settings.prompt_versions_path),
    )


def _require_activation_gates(payload: RegistryActivationRequest) -> None:
    missing = [
        name
        for name in ("eval_passed", "reviewer_approved", "canary_passed")
        if not getattr(payload, name)
    ]
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "activation gates are not satisfied",
                "missing_gates": missing,
            },
        )


def _activation_record(
    *,
    activation_type: Literal["model_profile", "prompt_version"],
    item_id: str,
    activated_by: str,
    payload: RegistryActivationRequest,
    item: ModelProfile | PromptVersion,
) -> dict[str, Any]:
    return {
        "activation_id": f"{activation_type}:{item_id}",
        "activation_type": activation_type,
        "item_id": item_id,
        "status": "active",
        "activated_by": activated_by,
        "eval_passed": payload.eval_passed,
        "reviewer_approved": payload.reviewer_approved,
        "canary_passed": payload.canary_passed,
        "reason_code": payload.reason_code,
        "comment": payload.comment,
        "item": item.model_dump(mode="json"),
    }
