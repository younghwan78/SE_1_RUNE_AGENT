"""Run APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["runs"])


class AnalyzeRunRequest(BaseModel):
    """Start a local analysis run."""

    project_key: str = "RUNE_CAM_ALPHA"
    scenario: str = "RUNE_CAM_ALPHA"
    run_id: str | None = Field(default=None)


@router.post("/runs/analyze")
def analyze(request: Request, payload: AnalyzeRunRequest) -> dict[str, Any]:
    """Run dummy/local analysis."""
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    run_id = payload.run_id or settings.new_id("run")
    result = runtime.workflow().run(
        run_id=run_id,
        project_key=payload.project_key,
        scenario=payload.scenario,
    )
    runtime.analyses[run_id] = result
    return {
        "run": result.run.model_dump(mode="json"),
        "counts": {
            "artifacts": len(result.artifacts),
            "chunks": len(result.chunks),
            "nodes": len(result.nodes),
            "candidate_edges": len(result.candidate_edges),
            "findings": len(result.findings),
            "approvals": len(result.approvals),
        },
    }


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str) -> dict[str, Any]:
    """Return run detail."""
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    result: dict[str, Any] = run.model_dump(mode="json")
    return result


@router.get("/runs/{run_id}/steps")
def get_steps(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return run step traces."""
    runtime = request.app.state.runtime
    if run_id not in runtime.traces.runs:
        raise HTTPException(status_code=404, detail="run not found")
    return [step.model_dump(mode="json") for step in runtime.traces.list_steps(run_id)]


@router.get("/runs/{run_id}/graph-delta")
def get_graph_delta(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return approval graph deltas created by a run."""
    runtime = request.app.state.runtime
    if run_id not in runtime.traces.runs:
        raise HTTPException(status_code=404, detail="run not found")
    return [
        delta.model_dump(mode="json")
        for delta in runtime.approvals.deltas.values()
        if delta.created_from_run_id == run_id
    ]


@router.get("/findings")
def list_findings(request: Request) -> list[dict[str, Any]]:
    """Return findings from all local analysis runs."""
    runtime = request.app.state.runtime
    findings: list[dict[str, Any]] = []
    for result in runtime.analyses.values():
        findings.extend(finding.model_dump(mode="json") for finding in result.findings)
    return findings
