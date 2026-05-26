"""Runtime construction helpers for SoC query services."""

import shlex
from collections.abc import Sequence
from pathlib import Path

from req_tracker.config.settings import Settings
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.registry import ModelRegistry
from req_tracker.query.reranking import (
    CrossEncoderSocReranker,
    GatewaySocReranker,
    LexicalSocReranker,
    SocReranker,
)
from req_tracker.query.retrieval import PostgresHybridSocRetrievalBackend, SocRetrievalBackend
from req_tracker.query.soc_orchestration import (
    GatewaySocAnswerAssembler,
    GatewaySocQueryToolPlanner,
    SocAnswerAssembler,
    SocQueryToolPlanner,
)
from req_tracker.query.soc_planner import GatewaySocSlicePlanner, SocSlicePlanner

_DISABLED_PLANNER_MODES = {"", "deterministic", "disabled", "off", "none"}
_GATEWAY_PLANNER_MODES = {"gateway", "model_gateway", "claude_code", "claude_code_subprocess"}


def create_soc_slice_planner(
    *,
    settings: Settings,
    traces: InMemoryTraceRepository,
    artifact_store: LocalArtifactStore,
) -> SocSlicePlanner | None:
    """Create the optional runtime SocSlice planner from settings and registry files."""
    mode = settings.soc_query_planner_mode.strip().lower()
    if mode in _DISABLED_PLANNER_MODES:
        return None
    if mode not in _GATEWAY_PLANNER_MODES:
        raise ValueError(f"unsupported SOC_QUERY_PLANNER_MODE: {settings.soc_query_planner_mode}")

    registry = ModelRegistry.from_json_files(
        profiles_path=Path(settings.model_profiles_path),
        prompts_path=Path(settings.prompt_versions_path),
    )
    profile = registry.get_profile(settings.soc_query_planner_model_profile_id)
    prompt = registry.active_prompt_for_task("soc_slice_planning")
    provider = provider_for_profile(
        profile,
        endpoint_url=settings.model_gateway_endpoint_url,
        api_key=settings.model_gateway_api_key,
        claude_command=_claude_command(settings.model_gateway_claude_command),
    )
    client = ModelGatewayClient(
        provider=provider,
        profile=profile,
        prompt=prompt,
        trace_repo=traces,
        artifact_store=artifact_store,
    )
    return GatewaySocSlicePlanner(
        client=client,
        model_profile_id=profile.model_profile_id,
        prompt_version_id=prompt.prompt_version_id,
    )


def create_soc_query_tool_planner(
    *,
    settings: Settings,
    traces: InMemoryTraceRepository,
    artifact_store: LocalArtifactStore,
) -> SocQueryToolPlanner | None:
    """Create the optional runtime query tool planner from settings."""
    client_parts = _gateway_client_for_task(
        settings=settings,
        traces=traces,
        artifact_store=artifact_store,
        mode=settings.soc_query_tool_planner_mode,
        model_profile_id=settings.soc_query_tool_planner_model_profile_id,
        task_name="soc_query_tool_planning",
    )
    if client_parts is None:
        return None
    client, profile_id, prompt_id = client_parts
    return GatewaySocQueryToolPlanner(
        client=client,
        model_profile_id=profile_id,
        prompt_version_id=prompt_id,
    )


def create_soc_answer_assembler(
    *,
    settings: Settings,
    traces: InMemoryTraceRepository,
    artifact_store: LocalArtifactStore,
) -> SocAnswerAssembler | None:
    """Create the optional runtime answer assembler from settings."""
    client_parts = _gateway_client_for_task(
        settings=settings,
        traces=traces,
        artifact_store=artifact_store,
        mode=settings.soc_answer_assembler_mode,
        model_profile_id=settings.soc_answer_assembler_model_profile_id,
        task_name="soc_answer_assembly",
    )
    if client_parts is None:
        return None
    client, profile_id, prompt_id = client_parts
    return GatewaySocAnswerAssembler(
        client=client,
        model_profile_id=profile_id,
        prompt_version_id=prompt_id,
    )


def create_soc_reranker(
    *,
    settings: Settings,
    traces: InMemoryTraceRepository,
    artifact_store: LocalArtifactStore,
) -> SocReranker | None:
    """Create the runtime reranker from settings."""
    mode = settings.soc_reranker_mode.strip().lower()
    if mode in {"", "disabled", "off", "none"}:
        return None
    if mode == "deterministic":
        return LexicalSocReranker()
    if mode in {"cross_encoder", "local_cross_encoder", "bge_reranker"}:
        return CrossEncoderSocReranker(model_name=settings.soc_cross_encoder_model_name)
    client_parts = _gateway_client_for_task(
        settings=settings,
        traces=traces,
        artifact_store=artifact_store,
        mode=mode,
        model_profile_id=settings.soc_reranker_model_profile_id,
        task_name="soc_rerank",
    )
    if client_parts is None:
        return None
    client, profile_id, prompt_id = client_parts
    return GatewaySocReranker(
        client=client,
        model_profile_id=profile_id,
        prompt_version_id=prompt_id,
    )


def create_soc_retrieval_backend(*, settings: Settings) -> SocRetrievalBackend | None:
    """Create the optional storage-backed SoC retrieval backend."""
    mode = settings.soc_retrieval_backend.strip().lower()
    if mode in {"", "fixture", "fixture_seed", "deterministic", "disabled", "off", "none"}:
        return None
    if mode in {"postgres", "postgres_hybrid", "postgres_age_pgvector_fts"}:
        return PostgresHybridSocRetrievalBackend(dsn=settings.postgres_dsn)
    raise ValueError(f"unsupported SOC_RETRIEVAL_BACKEND: {settings.soc_retrieval_backend}")


def _gateway_client_for_task(
    *,
    settings: Settings,
    traces: InMemoryTraceRepository,
    artifact_store: LocalArtifactStore,
    mode: str,
    model_profile_id: str,
    task_name: str,
) -> tuple[ModelGatewayClient, str, str] | None:
    resolved_mode = mode.strip().lower()
    if resolved_mode in _DISABLED_PLANNER_MODES:
        return None
    if resolved_mode not in _GATEWAY_PLANNER_MODES:
        raise ValueError(f"unsupported model gateway mode for SoC query: {mode}")
    registry = ModelRegistry.from_json_files(
        profiles_path=Path(settings.model_profiles_path),
        prompts_path=Path(settings.prompt_versions_path),
    )
    profile = registry.get_profile(model_profile_id)
    prompt = registry.active_prompt_for_task(task_name)  # type: ignore[arg-type]
    provider = provider_for_profile(
        profile,
        endpoint_url=settings.model_gateway_endpoint_url,
        api_key=settings.model_gateway_api_key,
        claude_command=_claude_command(settings.model_gateway_claude_command),
    )
    return (
        ModelGatewayClient(
            provider=provider,
            profile=profile,
            prompt=prompt,
            trace_repo=traces,
            artifact_store=artifact_store,
        ),
        profile.model_profile_id,
        prompt.prompt_version_id,
    )


def _claude_command(command_text: str) -> Sequence[str] | None:
    if not command_text.strip():
        return None
    return tuple(shlex.split(command_text))
