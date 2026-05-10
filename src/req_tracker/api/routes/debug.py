"""Debug workbench APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

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


@router.get("/debug/artifact")
def read_debug_artifact(
    request: Request,
    artifact_ref: str = Query(min_length=1),
) -> Any:
    """Read a local JSON debug artifact by artifact ref."""
    runtime = request.app.state.runtime
    try:
        artifact = runtime.artifact_store.read_json(artifact_ref)
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


def _project_key_from_ref(runtime: Any, artifact_ref: str) -> str | None:
    for step in runtime.traces.steps.values():
        if step.output_ref != artifact_ref:
            continue
        run = runtime.traces.runs.get(step.run_id)
        if run is not None:
            project_key: str = run.project_key
            return project_key
    return None
