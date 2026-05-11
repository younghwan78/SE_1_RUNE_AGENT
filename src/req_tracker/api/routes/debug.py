"""Debug workbench APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from req_tracker.api.security import require_role
from req_tracker.debug.artifacts import ArtifactAccessError

router = APIRouter(tags=["debug"])


@router.get("/debug/runs")
def list_debug_runs(request: Request) -> list[dict[str, Any]]:
    """List runs for debug navigation."""
    runtime = request.app.state.runtime
    runs = sorted(runtime.traces.runs.values(), key=lambda run: run.started_at, reverse=True)
    return [run.model_dump(mode="json") for run in runs]


@router.get("/debug/runs/{run_id}/summary")
def debug_run_summary(request: Request, run_id: str) -> dict[str, Any]:
    """Return run, step, LLM call, artifact, and graph delta debug summary."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    steps = runtime.traces.list_steps(run_id)
    llm_calls = [
        call for call in runtime.traces.llm_calls.values() if call.run_id == run_id
    ]
    graph_deltas = [
        delta for delta in runtime.approvals.deltas.values() if delta.created_from_run_id == run_id
    ]
    return {
        "run": run.model_dump(mode="json"),
        "steps": [step.model_dump(mode="json") for step in steps],
        "llm_calls": [call.model_dump(mode="json") for call in llm_calls],
        "graph_deltas": [delta.model_dump(mode="json") for delta in graph_deltas],
        "artifact_refs": [
            step.output_ref for step in steps if step.output_ref is not None
        ],
        "counts": {
            "steps": len(steps),
            "llm_calls": len(llm_calls),
            "graph_deltas": len(graph_deltas),
            "artifact_refs": sum(1 for step in steps if step.output_ref is not None),
        },
    }


@router.get("/debug/runs/{run_id}/diff-view")
def debug_run_diff_view(request: Request, run_id: str) -> dict[str, Any]:
    """Return side-by-side debug data for LLM calls and graph deltas."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    llm_calls = [
        call for call in runtime.traces.llm_calls.values() if call.run_id == run_id
    ]
    graph_deltas = [
        delta for delta in runtime.approvals.deltas.values() if delta.created_from_run_id == run_id
    ]
    approved_edges = [
        edge.model_dump(mode="json")
        for edge in runtime.graph.edges.values()
        if edge.source_node_id in runtime.graph.nodes
        and runtime.graph.nodes[edge.source_node_id].project_key == run.project_key
    ]
    return {
        "run_id": run_id,
        "llm_payload_pairs": [
            {
                "llm_call_id": call.llm_call_id,
                "model_profile_id": call.model_profile_id,
                "prompt_version_id": call.prompt_version_id,
                "validation_status": call.validation_status,
                "left": {
                    "label": "masked_payload",
                    "artifact_ref": call.masked_payload_ref,
                    "payload": _read_optional_artifact(runtime, call.masked_payload_ref),
                },
                "right": {
                    "label": "raw_response",
                    "artifact_ref": call.raw_response_ref,
                    "payload": _read_optional_artifact(runtime, call.raw_response_ref),
                },
                "parsed": {
                    "label": "parsed_output",
                    "artifact_ref": call.parsed_output_ref,
                    "payload": _read_optional_artifact(runtime, call.parsed_output_ref),
                },
            }
            for call in llm_calls
        ],
        "graph_delta_previews": [
            {
                "delta_id": delta.delta_id,
                "left": {
                    "label": "approved_graph_edges",
                    "count": len(approved_edges),
                    "edges": approved_edges,
                },
                "right": {
                    "label": "proposed_delta_operations",
                    "count": len(delta.operations),
                    "operations": [
                        operation.model_dump(mode="json") for operation in delta.operations
                    ],
                },
            }
            for delta in graph_deltas
        ],
        "counts": {
            "llm_payload_pairs": len(llm_calls),
            "graph_delta_previews": len(graph_deltas),
        },
    }


@router.get("/debug/approvals/{approval_id}/lineage")
def debug_approval_lineage(request: Request, approval_id: str) -> dict[str, Any]:
    """Return approval creation, graph delta, step, feedback, and audit lineage."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    approval = runtime.approvals.items.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    run = runtime.traces.runs.get(approval.created_from_run_id)
    step = runtime.traces.steps.get(approval.created_from_step_id)
    delta = (
        runtime.approvals.deltas.get(approval.graph_delta_ref)
        if approval.graph_delta_ref is not None
        else None
    )
    feedback = [
        event
        for event in runtime.approvals.feedback
        if event.target_id == approval.proposal_ref
    ]
    audit_events = [
        event
        for event in runtime.audit.events.values()
        if event.target_type == "approval" and event.target_id == approval_id
    ]
    return {
        "approval": approval.model_dump(mode="json"),
        "run": run.model_dump(mode="json") if run is not None else None,
        "step": step.model_dump(mode="json") if step is not None else None,
        "graph_delta": delta.model_dump(mode="json") if delta is not None else None,
        "feedback": [event.model_dump(mode="json") for event in feedback],
        "audit_events": [event.model_dump(mode="json") for event in audit_events],
        "counts": {
            "feedback": len(feedback),
            "audit_events": len(audit_events),
            "graph_delta_operations": len(delta.operations) if delta is not None else 0,
        },
    }


@router.get("/debug/artifact")
def read_debug_artifact(
    request: Request,
    artifact_ref: str = Query(min_length=1),
) -> Any:
    """Read a local JSON debug artifact by artifact ref."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    try:
        artifact = runtime.artifact_store.read_json(artifact_ref)
    except ArtifactAccessError as exc:
        runtime.audit.record(
            action="debug_artifact_read",
            actor_id="local_debugger",
            actor_role="developer",
            project_key=None,
            target_type="debug_artifact",
            target_id=artifact_ref,
            outcome="blocked",
            reason_code="artifact_ref_outside_store",
            metadata={"artifact_ref": artifact_ref},
        )
        runtime.persist_approval_state()
        raise HTTPException(status_code=403, detail="artifact ref outside store") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact not found") from exc
    runtime.audit.record(
        action="debug_artifact_read",
        actor_id="local_debugger",
        actor_role="developer",
        project_key=_project_key_from_ref(runtime, artifact_ref),
        target_type="debug_artifact",
        target_id=artifact_ref,
        metadata={"artifact_ref": artifact_ref},
    )
    runtime.persist_approval_state()
    return artifact


def _read_optional_artifact(runtime: Any, artifact_ref: str | None) -> Any:
    if artifact_ref is None:
        return None
    try:
        return runtime.artifact_store.read_json(artifact_ref)
    except (ArtifactAccessError, FileNotFoundError):
        return None


def _project_key_from_ref(runtime: Any, artifact_ref: str) -> str | None:
    for step in runtime.traces.steps.values():
        if step.output_ref != artifact_ref:
            continue
        run = runtime.traces.runs.get(step.run_id)
        if run is not None:
            project_key: str = run.project_key
            return project_key
    return None
