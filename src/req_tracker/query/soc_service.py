"""Deterministic fixture-backed SoC query service.

This is the Stage D baseline: it routes natural language to a typed slice,
retrieves from seed fixture classifications, and returns structured answers with
source links. Claude Code planning/reranking can be layered behind this contract.
"""

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.hash import stable_hash
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.fixtures.soc_knowledge import load_soc_seed_artifacts
from req_tracker.ingestion.soc_classification import classify_soc_axes
from req_tracker.ontology.soc_models import (
    SocAnswer,
    SocAnswerItem,
    SocAnswerSource,
    SocLifecycleEvent,
    SocQueryPlan,
    SocSlice,
)
from req_tracker.query.reranking import SocReranker
from req_tracker.query.retrieval import SocRetrievalBackend
from req_tracker.query.soc_orchestration import (
    SocAnswerAssembler,
    SocQueryToolPlanner,
    build_deterministic_query_plan,
)
from req_tracker.query.soc_planner import SocSlicePlanner


def classify_soc_slice(user_query: str) -> SocSlice:
    """Classify a natural-language query into the initial SoC slice patterns."""
    text = user_query.lower()
    artifact_id = _artifact_id_from_text(user_query)
    if artifact_id is not None and _contains_any(text, ("lifecycle", "생명", "이력")):
        return SocSlice(pattern="lifecycle_trace", artifact_id=artifact_id)
    concerns = _concerns_from_text(text)
    components = _components_from_text(text)
    projects = _projects_from_text(user_query)
    keywords = _keywords_from_text(text)
    if "bluetooth" in text or not (concerns or components or artifact_id):
        return SocSlice(pattern="unknown", keywords=keywords or [user_query])
    if _contains_any(text, ("지난", "timeline", "처리", "history", "흐름")):
        return SocSlice(
            pattern="timeline_slice",
            project_keys=projects or ["SOC-N-1", "SOC-N-2"],
            concerns=concerns,
            components=components,
            keywords=keywords,
        )
    if concerns and components:
        return SocSlice(
            pattern="topic_intersection",
            project_keys=projects,
            concerns=concerns,
            components=components,
            keywords=keywords,
        )
    return SocSlice(
        pattern="concern_slice",
        project_keys=projects or (["SOC-N-1"] if "이전" in text else []),
        concerns=concerns,
        components=components,
        keywords=keywords,
    )


def answer_soc_query(
    *,
    user_query: str,
    user_id: str,
    session_id: str,
    query_id: str | None = None,
    query_slice: SocSlice | None = None,
    current_project: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    slice_planner: SocSlicePlanner | None = None,
    tool_planner: SocQueryToolPlanner | None = None,
    reranker: SocReranker | None = None,
    retrieval_backend: SocRetrievalBackend | None = None,
    answer_assembler: SocAnswerAssembler | None = None,
    artifacts: list[RawSourceArtifact] | None = None,
    artifact_store: LocalArtifactStore | None = None,
    trace_repo: InMemoryTraceRepository | None = None,
) -> SocAnswer:
    """Answer one SoC knowledge query using the packaged seed fixture index."""
    resolved_query_id = query_id or (
        f"soc_query_{stable_hash([user_query, user_id, session_id])[:12]}"
    )
    _start_query_trace(
        trace_repo=trace_repo,
        run_id=resolved_query_id,
        project_key=current_project or "soc_knowledge",
        user_id=user_id,
        input_payload={
            "user_query": user_query,
            "session_id": session_id,
            "current_project": current_project,
        },
    )
    slice_step_id = f"{resolved_query_id}_soc_slice_planning"
    _start_query_step(
        trace_repo=trace_repo,
        run_id=resolved_query_id,
        step_id=slice_step_id,
        stage_name="soc_slice_planning",
        input_payload={
            "user_query": user_query,
            "explicit_slice": query_slice.model_dump(mode="json") if query_slice else None,
        },
    )
    resolved_slice, slice_source = _resolve_slice(
        user_query=user_query,
        user_id=user_id,
        session_id=session_id,
        query_slice=query_slice,
        current_project=current_project,
        conversation_history=conversation_history or [],
        slice_planner=slice_planner,
        trace_run_id=resolved_query_id,
        trace_step_id=slice_step_id,
    )
    _finish_query_step(
        trace_repo=trace_repo,
        step_id=slice_step_id,
        output_payload={
            "slice_source": slice_source,
            "query_slice": resolved_slice.model_dump(mode="json"),
        },
        validation_status="passed",
    )
    plan_step_id = f"{resolved_query_id}_soc_query_tool_planning"
    _start_query_step(
        trace_repo=trace_repo,
        run_id=resolved_query_id,
        step_id=plan_step_id,
        stage_name="soc_query_tool_planning",
        input_payload=resolved_slice,
    )
    query_plan, plan_source = _resolve_query_plan(
        query_id=resolved_query_id,
        user_query=user_query,
        query_slice=resolved_slice,
        current_project=current_project,
        tool_planner=tool_planner,
        trace_run_id=resolved_query_id,
        trace_step_id=plan_step_id,
    )
    _finish_query_step(
        trace_repo=trace_repo,
        step_id=plan_step_id,
        output_payload={
            "plan_source": plan_source,
            "query_plan": query_plan.model_dump(mode="json"),
        },
        validation_status="passed",
    )
    query_artifacts = artifacts if artifacts is not None else load_soc_seed_artifacts()
    retrieval_backend_name = (
        retrieval_backend.backend_name if retrieval_backend is not None else "fixture_seed"
    )
    retrieval_step_id = f"{resolved_query_id}_soc_seed_retrieval"
    _start_query_step(
        trace_repo=trace_repo,
        run_id=resolved_query_id,
        step_id=retrieval_step_id,
        stage_name="soc_seed_retrieval",
        input_payload=resolved_slice,
    )
    candidates = (
        retrieval_backend.retrieve(
            query_id=resolved_query_id,
            user_query=user_query,
            query_slice=resolved_slice,
        )
        if retrieval_backend is not None
        else _retrieve(query_artifacts, resolved_slice)
    )
    _finish_query_step(
        trace_repo=trace_repo,
        step_id=retrieval_step_id,
        output_payload={
            "candidate_count": len(candidates),
            "candidate_artifact_ids": [artifact.external_id for artifact in candidates],
        },
    )
    rerank_step_id = f"{resolved_query_id}_soc_rerank"
    if candidates:
        _start_query_step(
            trace_repo=trace_repo,
            run_id=resolved_query_id,
            step_id=rerank_step_id,
            stage_name="soc_rerank",
            input_payload={
                "candidate_artifact_ids": [artifact.external_id for artifact in candidates],
            },
        )
        candidates, rerank_source = _rerank_candidates(
            reranker=reranker,
            query_id=resolved_query_id,
            user_query=user_query,
            query_slice=resolved_slice,
            candidates=candidates,
            run_id=resolved_query_id,
            step_id=rerank_step_id,
        )
        _finish_query_step(
            trace_repo=trace_repo,
            step_id=rerank_step_id,
            output_payload={
                "rerank_source": rerank_source,
                "candidate_artifact_ids": [artifact.external_id for artifact in candidates],
            },
            validation_status="passed",
        )
    else:
        rerank_source = "skipped"
    answer_step_id = f"{resolved_query_id}_soc_answer_projection"
    _start_query_step(
        trace_repo=trace_repo,
        run_id=resolved_query_id,
        step_id=answer_step_id,
        stage_name="soc_answer_projection",
        input_payload={
            "candidate_artifact_ids": [artifact.external_id for artifact in candidates],
        },
    )
    if not candidates:
        answer = SocAnswer(
            query_id=resolved_query_id,
            summary="해당 자료를 찾지 못함.",
            items=[],
            timeline=[],
            confidence="low",
            reasoning_log_ref=f"memory://soc-query/{resolved_query_id}/reasoning",
            quality_signals=["no_candidates"],
        )
        final_answer = _with_reasoning_log(
            answer=answer,
            artifact_store=artifact_store,
            user_query=user_query,
            user_id=user_id,
            session_id=session_id,
            query_slice=resolved_slice,
            query_plan=query_plan,
            plan_source=plan_source,
            rerank_source=rerank_source,
            retrieval_backend_name=retrieval_backend_name,
            candidates=candidates,
            slice_source=slice_source,
        )
        final_answer = _assemble_answer(
            answer_assembler=answer_assembler,
            user_query=user_query,
            query_slice=resolved_slice,
            query_plan=query_plan,
            base_answer=final_answer,
            candidates=candidates,
            run_id=resolved_query_id,
        )
        _finish_query_step(
            trace_repo=trace_repo,
            step_id=answer_step_id,
            output_payload=final_answer,
            output_ref=final_answer.reasoning_log_ref,
            validation_status="passed",
        )
        _complete_query_trace(trace_repo=trace_repo, run_id=resolved_query_id)
        return final_answer

    items = [_answer_item(artifact) for artifact in candidates]
    timeline = (
        _timeline_for_artifact(candidates[0])
        if resolved_slice.pattern == "lifecycle_trace"
        else _timeline_for_artifacts(candidates)
    )
    answer = SocAnswer(
        query_id=resolved_query_id,
        summary=f"{len(items)}개 SoC knowledge artifact를 찾았습니다.",
        items=items,
        timeline=timeline,
        confidence="high" if all(item.sources for item in items) else "medium",
        reasoning_log_ref=f"memory://soc-query/{resolved_query_id}/reasoning",
        quality_signals=_quality_signals(candidates),
    )
    final_answer = _with_reasoning_log(
        answer=answer,
        artifact_store=artifact_store,
        user_query=user_query,
        user_id=user_id,
        session_id=session_id,
            query_slice=resolved_slice,
        query_plan=query_plan,
        plan_source=plan_source,
        rerank_source=rerank_source,
        retrieval_backend_name=retrieval_backend_name,
        candidates=candidates,
        slice_source=slice_source,
        )
    final_answer = _assemble_answer(
        answer_assembler=answer_assembler,
        user_query=user_query,
        query_slice=resolved_slice,
        query_plan=query_plan,
        base_answer=final_answer,
        candidates=candidates,
        run_id=resolved_query_id,
    )
    _finish_query_step(
        trace_repo=trace_repo,
        step_id=answer_step_id,
        output_payload=final_answer,
        output_ref=final_answer.reasoning_log_ref,
        validation_status="passed",
    )
    _complete_query_trace(trace_repo=trace_repo, run_id=resolved_query_id)
    return final_answer


def _resolve_slice(
    *,
    user_query: str,
    user_id: str,
    session_id: str,
    query_slice: SocSlice | None,
    current_project: str | None,
    conversation_history: list[dict[str, str]],
    slice_planner: SocSlicePlanner | None,
    trace_run_id: str,
    trace_step_id: str,
) -> tuple[SocSlice, str]:
    if query_slice is not None:
        return query_slice, "explicit"
    if slice_planner is not None:
        return (
            slice_planner.plan(
                user_query=user_query,
                user_id=user_id,
                session_id=session_id,
                current_project=current_project,
                conversation_history=conversation_history,
                run_id=trace_run_id,
                step_id=trace_step_id,
            ),
            "planner",
        )
    return classify_soc_slice(user_query), "deterministic"


def _rerank_candidates(
    *,
    reranker: SocReranker | None,
    query_id: str,
    user_query: str,
    query_slice: SocSlice,
    candidates: list[RawSourceArtifact],
    run_id: str,
    step_id: str,
) -> tuple[list[RawSourceArtifact], str]:
    if reranker is None:
        return candidates, "deterministic_order"
    return (
        reranker.rerank(
            query_id=query_id,
            user_query=user_query,
            query_slice=query_slice,
            candidates=candidates,
            run_id=run_id,
            step_id=step_id,
        ),
        "reranker",
    )


def _resolve_query_plan(
    *,
    query_id: str,
    user_query: str,
    query_slice: SocSlice,
    current_project: str | None,
    tool_planner: SocQueryToolPlanner | None,
    trace_run_id: str,
    trace_step_id: str,
) -> tuple[SocQueryPlan, str]:
    if tool_planner is None:
        return (
            build_deterministic_query_plan(query_id=query_id, query_slice=query_slice),
            "deterministic",
        )
    return (
        tool_planner.plan(
            query_id=query_id,
            user_query=user_query,
            query_slice=query_slice,
            current_project=current_project,
            run_id=trace_run_id,
            step_id=trace_step_id,
        ),
        "planner",
    )


def _assemble_answer(
    *,
    answer_assembler: SocAnswerAssembler | None,
    user_query: str,
    query_slice: SocSlice,
    query_plan: SocQueryPlan,
    base_answer: SocAnswer,
    candidates: list[RawSourceArtifact],
    run_id: str,
) -> SocAnswer:
    if answer_assembler is None:
        return base_answer
    return answer_assembler.assemble(
        user_query=user_query,
        query_slice=query_slice,
        query_plan=query_plan,
        base_answer=base_answer,
        candidate_context=[_candidate_context(artifact) for artifact in candidates],
        run_id=run_id,
    )


def _start_query_trace(
    *,
    trace_repo: InMemoryTraceRepository | None,
    run_id: str,
    project_key: str,
    user_id: str,
    input_payload: dict[str, object | None],
) -> None:
    if trace_repo is None:
        return
    trace_repo.create_run(
        run_id=run_id,
        run_type="query",
        project_key=project_key,
        triggered_by=user_id,
        trigger_source="api",
    )
    trace_repo.mark_run_running(run_id)
    trace_repo.start_step(
        step_id=f"{run_id}_soc_query_received",
        run_id=run_id,
        stage_name="soc_query_received",
        input_payload=input_payload,
    )
    trace_repo.finish_step(
        step_id=f"{run_id}_soc_query_received",
        output_payload={"accepted": True},
    )


def _start_query_step(
    *,
    trace_repo: InMemoryTraceRepository | None,
    run_id: str,
    step_id: str,
    stage_name: str,
    input_payload: object,
) -> None:
    if trace_repo is None:
        return
    trace_repo.start_step(
        step_id=step_id,
        run_id=run_id,
        stage_name=stage_name,
        input_payload=input_payload,
    )


def _finish_query_step(
    *,
    trace_repo: InMemoryTraceRepository | None,
    step_id: str,
    output_payload: object,
    output_ref: str | None = None,
    validation_status: str = "not_applicable",
) -> None:
    if trace_repo is None:
        return
    trace_repo.finish_step(
        step_id=step_id,
        output_payload=output_payload,
        output_ref=output_ref,
        validation_status=validation_status,  # type: ignore[arg-type]
    )


def _complete_query_trace(
    *,
    trace_repo: InMemoryTraceRepository | None,
    run_id: str,
) -> None:
    if trace_repo is None:
        return
    trace_repo.complete_run(run_id)


def _retrieve(artifacts: list[RawSourceArtifact], query_slice: SocSlice) -> list[RawSourceArtifact]:
    if query_slice.pattern == "unknown":
        return []
    if query_slice.pattern == "lifecycle_trace":
        return [
            artifact for artifact in artifacts if artifact.external_id == query_slice.artifact_id
        ]
    matched = [artifact for artifact in artifacts if _artifact_matches_slice(artifact, query_slice)]
    matched.sort(key=lambda artifact: (artifact.created_at, artifact.external_id))
    return matched


def _artifact_matches_slice(artifact: RawSourceArtifact, query_slice: SocSlice) -> bool:
    classifications = classify_soc_axes(
        artifact,
        run_id="soc_query",
        step_id="deterministic_retrieval",
    )
    values_by_axis: dict[str, set[str]] = {}
    for classification in classifications:
        values_by_axis.setdefault(classification.axis, set()).add(classification.value)
    if query_slice.project_keys and artifact.project_key not in query_slice.project_keys:
        return False
    if query_slice.v_levels and not (
        set(query_slice.v_levels) & values_by_axis.get("v_level", set())
    ):
        return False
    if query_slice.concerns and not (
        set(query_slice.concerns) & values_by_axis.get("concern", set())
    ):
        return False
    if query_slice.components and not (
        set(query_slice.components) & values_by_axis.get("component", set())
    ):
        return False
    if query_slice.keywords and not _keywords_match(artifact, query_slice.keywords):
        return False
    return True


def _answer_item(artifact: RawSourceArtifact) -> SocAnswerItem:
    classifications = classify_soc_axes(
        artifact,
        run_id="soc_query",
        step_id="answer_projection",
    )
    level = next(
        (
            classification.value
            for classification in classifications
            if classification.axis == "v_level"
        ),
        None,
    )
    concerns = [
        classification.value
        for classification in classifications
        if classification.axis == "concern"
    ]
    components = [
        classification.value
        for classification in classifications
        if classification.axis == "component"
    ]
    return SocAnswerItem(
        title=artifact.title,
        summary=artifact.body_text,
        sources=[
            SocAnswerSource(
                type=artifact.source_type,
                key=artifact.external_id,
                url=artifact.source_url,
            )
        ],
        level=level,  # type: ignore[arg-type]
        concern=concerns,
        component=components,
    )


def _timeline_for_artifacts(artifacts: list[RawSourceArtifact]) -> list[SocLifecycleEvent]:
    return [
        SocLifecycleEvent(
            event_id=f"soc_evt_{stable_hash([artifact.external_id, 'created'])[:16]}",
            entity_id=artifact.external_id,
            timestamp=datetime.fromisoformat(artifact.created_at),
            change_type="created",
            before=None,
            after={"source_type": artifact.source_type, "project_key": artifact.project_key},
            source=artifact.source_type,
            source_url=artifact.source_url,
            run_id="soc_query",
            step_id="timeline_projection",
        )
        for artifact in artifacts
    ]


def _timeline_for_artifact(artifact: RawSourceArtifact) -> list[SocLifecycleEvent]:
    return [
        SocLifecycleEvent(
            event_id=f"soc_evt_{stable_hash([artifact.external_id, 'created'])[:16]}",
            entity_id=artifact.external_id,
            timestamp=datetime.fromisoformat(artifact.created_at),
            change_type="created",
            before=None,
            after={"source_type": artifact.source_type, "project_key": artifact.project_key},
            source=artifact.source_type,
            source_url=artifact.source_url,
            run_id="soc_query",
            step_id="timeline_projection",
        ),
        SocLifecycleEvent(
            event_id=f"soc_evt_{stable_hash([artifact.external_id, 'updated'])[:16]}",
            entity_id=artifact.external_id,
            timestamp=datetime.fromisoformat(artifact.updated_at),
            change_type="updated",
            before={"content_hash": "unknown"},
            after={"content_hash": stable_hash(artifact.body_text)},
            source=artifact.source_type,
            source_url=artifact.source_url,
            run_id="soc_query",
            step_id="timeline_projection",
        ),
    ]


def _quality_signals(candidates: list[RawSourceArtifact]) -> list[str]:
    signals: list[str] = []
    if len(candidates) <= 2:
        signals.append("limited_evidence")
    if len({artifact.project_key for artifact in candidates}) > 1:
        signals.append("cross_project_data")
    return signals


def _with_reasoning_log(
    *,
    answer: SocAnswer,
    artifact_store: LocalArtifactStore | None,
    user_query: str,
    user_id: str,
    session_id: str,
    query_slice: SocSlice,
    query_plan: SocQueryPlan,
    plan_source: str,
    rerank_source: str,
    retrieval_backend_name: str,
    candidates: list[RawSourceArtifact],
    slice_source: str,
) -> SocAnswer:
    if artifact_store is None:
        return answer
    ref = artifact_store.write_json(
        answer.query_id,
        "soc_query_reasoning",
        _reasoning_log_payload(
            answer=answer,
            user_query=user_query,
            user_id=user_id,
            session_id=session_id,
            query_slice=query_slice,
            query_plan=query_plan,
            plan_source=plan_source,
            rerank_source=rerank_source,
            retrieval_backend_name=retrieval_backend_name,
            candidates=candidates,
            slice_source=slice_source,
        ),
    )
    return answer.model_copy(update={"reasoning_log_ref": ref.artifact_ref})


def _reasoning_log_payload(
    *,
    answer: SocAnswer,
    user_query: str,
    user_id: str,
    session_id: str,
    query_slice: SocSlice,
    query_plan: SocQueryPlan,
    plan_source: str,
    rerank_source: str,
    retrieval_backend_name: str,
    candidates: list[RawSourceArtifact],
    slice_source: str,
) -> dict[str, Any]:
    return {
        "query": {
            "query_id": answer.query_id,
            "user_query": user_query,
            "user_id": user_id,
            "session_id": session_id,
        },
        "slice": query_slice.model_dump(mode="json"),
        "query_plan": {
            "source": plan_source,
            **query_plan.model_dump(mode="json"),
        },
        "retrieval": {
            "backend": retrieval_backend_name,
            "rerank_source": rerank_source,
            "candidate_count": len(candidates),
            "candidate_artifact_ids": [artifact.external_id for artifact in candidates],
        },
        "answer": {
            "confidence": answer.confidence,
            "item_count": len(answer.items),
            "timeline_count": len(answer.timeline),
            "quality_signals": answer.quality_signals,
        },
        "tool_trace": [
            {
                "tool": _slice_tool_name(slice_source),
                "status": "provided" if slice_source == "explicit" else "executed",
                "output_pattern": query_slice.pattern,
            },
            {
                "tool": "fixture_axis_filter",
                "status": "executed",
                "candidate_count": len(candidates),
            },
            {
                "tool": "rerank",
                "status": "skipped" if rerank_source == "skipped" else "executed",
                "source": rerank_source,
                "candidate_count": len(candidates),
            },
            {
                "tool": "answer_projection",
                "status": "executed",
                "item_count": len(answer.items),
            },
        ],
    }


def _candidate_context(artifact: RawSourceArtifact) -> dict[str, object]:
    return {
        "artifact_id": artifact.external_id,
        "title": artifact.title,
        "body_text": artifact.body_text,
        "source_type": artifact.source_type,
        "source_url": artifact.source_url,
        "project_key": artifact.project_key,
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at,
    }


def _slice_tool_name(slice_source: str) -> str:
    if slice_source == "explicit":
        return "provided_soc_slice"
    if slice_source == "planner":
        return "soc_slice_planner"
    return "classify_soc_slice"


def _concerns_from_text(text: str) -> list[str]:
    mapping = {
        "Power": ("power", "전력", "파워"),
        "Performance": ("performance", "성능", "perf"),
        "Memory": ("memory", "메모리"),
        "Area": ("area", "면적"),
        "Thermal": ("thermal", "발열", "온도"),
        "Latency": ("latency", "지연"),
        "Bandwidth": ("bandwidth", "대역폭", "bw"),
        "Reliability": ("reliability", "신뢰성"),
    }
    return _matches(text, mapping)


def _components_from_text(text: str) -> list[str]:
    mapping = {
        "Camera": ("camera", "카메라"),
        "Display": ("display", "디스플레이"),
        "NPU": ("npu",),
        "GPU": ("gpu",),
        "MemorySubsystem": ("memory subsystem", "memory_subsystem", "메모리"),
        "NoC": ("noc",),
        "PMU": ("pmu",),
        "SensorHub": ("sensor hub", "sensor_hub"),
    }
    return _matches(text, mapping)


def _matches(text: str, mapping: Mapping[str, Iterable[str]]) -> list[str]:
    return [
        name
        for name, aliases in mapping.items()
        if any(alias.lower() in text for alias in aliases)
    ]


def _projects_from_text(user_query: str) -> list[str]:
    projects = [project for project in ("SOC-N-1", "SOC-N-2") if project in user_query]
    return projects


def _artifact_id_from_text(user_query: str) -> str | None:
    for artifact in load_soc_seed_artifacts():
        if artifact.external_id in user_query:
            return artifact.external_id
    return None


def _keywords_from_text(text: str) -> list[str]:
    keywords: list[str] = []
    for keyword in ("shot", "launch", "regression", "bluetooth"):
        if keyword in text:
            keywords.append(keyword)
    return keywords


def _keywords_match(artifact: RawSourceArtifact, keywords: list[str]) -> bool:
    text = f"{artifact.title} {artifact.body_text}".lower()
    return all(keyword.lower() in text for keyword in keywords)


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)
