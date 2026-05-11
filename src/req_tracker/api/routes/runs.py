"""Run APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from req_tracker.api.security import require_project, require_role
from req_tracker.api.state import RuntimeState
from req_tracker.config.settings import Settings
from req_tracker.debug.replay import ReplayService
from req_tracker.scheduler.models import ScheduleConfig

router = APIRouter(tags=["runs"])


class AnalyzeRunRequest(BaseModel):
    """Start a local analysis run."""

    project_key: str = "RUNE_CAM_ALPHA"
    scenario: str = "RUNE_CAM_ALPHA"
    run_id: str | None = Field(default=None)


class ReplayRunRequest(BaseModel):
    """Replay a previous analysis run."""

    replay_run_id: str | None = None
    replay_mode: str = "same_model_same_prompt"
    scenario: str = "RUNE_CAM_ALPHA"


@router.post("/runs/analyze")
def analyze(request: Request, payload: AnalyzeRunRequest) -> dict[str, Any]:
    """Run dummy/local analysis."""
    require_project(request, payload.project_key)
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    run_id = payload.run_id or settings.new_id("run")
    result = runtime.run_analysis(
        run_id=run_id,
        project_key=payload.project_key,
        scenario=payload.scenario,
    )
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
    require_project(request, run.project_key)
    result: dict[str, Any] = run.model_dump(mode="json")
    return result


@router.get("/runs/{run_id}/steps")
def get_steps(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return run step traces."""
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    require_project(request, run.project_key)
    return [step.model_dump(mode="json") for step in runtime.traces.list_steps(run_id)]


@router.get("/runs/{run_id}/llm-calls")
def get_llm_calls(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return model gateway call traces for a run."""
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    require_project(request, run.project_key, "developer")
    return [
        call.model_dump(mode="json")
        for call in runtime.traces.llm_calls.values()
        if call.run_id == run_id
    ]


@router.get("/runs/{run_id}/artifacts")
def get_run_artifacts(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return stage artifact references produced by a run."""
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    require_project(request, run.project_key, "developer")
    return [
        {
            "run_id": step.run_id,
            "step_id": step.step_id,
            "stage_name": step.stage_name,
            "artifact_ref": step.output_ref,
            "output_hash": step.output_hash,
            "schema_version": step.schema_version,
        }
        for step in runtime.traces.list_steps(run_id)
        if step.output_ref is not None
    ]


@router.get("/runs/{run_id}/graph-delta")
def get_graph_delta(request: Request, run_id: str) -> list[dict[str, Any]]:
    """Return approval graph deltas created by a run."""
    runtime = request.app.state.runtime
    run = runtime.traces.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    require_project(request, run.project_key)
    return [
        delta.model_dump(mode="json")
        for delta in runtime.approvals.deltas.values()
        if delta.created_from_run_id == run_id
    ]


@router.post("/runs/{run_id}/replay")
def replay_run(request: Request, run_id: str, payload: ReplayRunRequest) -> dict[str, Any]:
    """Replay a run and return object-level diff."""
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    if run_id not in runtime.analyses:
        raise HTTPException(status_code=404, detail="run not found")
    source = runtime.analyses[run_id]
    require_project(request, source.run.project_key)
    replay_run_id = payload.replay_run_id or settings.new_id("replay")
    result = ReplayService(runtime.workflow(), runtime.analyses).replay(
        source_run_id=run_id,
        replay_run_id=replay_run_id,
        project_key=source.run.project_key,
        scenario=payload.scenario,
        replay_mode=payload.replay_mode,
    )
    runtime.replays[replay_run_id] = result
    return result.model_dump(mode="json")


@router.get("/replays/{replay_id}/diff")
def get_replay_diff(request: Request, replay_id: str) -> dict[str, Any]:
    """Return a previously generated replay diff."""
    runtime = request.app.state.runtime
    replay = runtime.replays.get(replay_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="replay not found")
    source_run = runtime.traces.runs.get(replay.source_run_id)
    if source_run is None:
        raise HTTPException(status_code=404, detail="source run not found")
    require_project(request, source_run.project_key, "developer")
    return {
        "source_run_id": replay.source_run_id,
        "replay_run_id": replay.replay_run_id,
        "replay_mode": replay.replay_mode,
        "diff": replay.diff.model_dump(mode="json"),
    }


@router.get("/findings")
def list_findings(request: Request) -> list[dict[str, Any]]:
    """Return findings from all local analysis runs."""
    user = require_role(request, "developer")
    runtime = request.app.state.runtime
    findings: list[dict[str, Any]] = []
    for result in runtime.analyses.values():
        if "*" not in user.project_keys and result.run.project_key not in user.project_keys:
            continue
        findings.extend(finding.model_dump(mode="json") for finding in result.findings)
    return findings


@router.get("/schedule")
def get_schedule(request: Request) -> dict[str, Any]:
    """Return periodic run schedule status."""
    runtime: RuntimeState = request.app.state.runtime
    require_project(request, runtime.scheduler.config.project_key)
    result: dict[str, Any] = runtime.scheduler.status().model_dump(mode="json")
    return result


@router.put("/schedule")
async def configure_schedule(request: Request, payload: ScheduleConfig) -> dict[str, Any]:
    """Configure periodic analysis runs."""
    user = require_project(request, payload.project_key, "operator")
    runtime: RuntimeState = request.app.state.runtime
    settings: Settings = request.app.state.settings
    status = await runtime.scheduler.configure(
        payload,
        runner=lambda run_id, project_key, scenario: runtime.run_analysis(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
        ),
        new_id=settings.new_id,
    )
    runtime.audit.record(
        action="schedule_configured",
        actor_id=user.user_id,
        actor_role=user.role,
        project_key=payload.project_key,
        target_type="schedule",
        target_id="default",
        metadata=payload.model_dump(mode="json"),
    )
    runtime.persist_approval_state()
    result: dict[str, Any] = status.model_dump(mode="json")
    return result


@router.post("/schedule/run-now")
async def run_schedule_now(request: Request) -> dict[str, Any]:
    """Run one scheduled analysis immediately."""
    runtime: RuntimeState = request.app.state.runtime
    user = require_project(request, runtime.scheduler.config.project_key, "operator")
    settings: Settings = request.app.state.settings
    result = await runtime.scheduler.run_now(
        runner=lambda run_id, project_key, scenario: runtime.run_analysis(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
        ),
        new_id=settings.new_id,
    )
    runtime.audit.record(
        action="schedule_run_now",
        actor_id=user.user_id,
        actor_role=user.role,
        project_key=runtime.scheduler.config.project_key,
        target_type="run",
        target_id=result.run_id,
        metadata=result.model_dump(mode="json"),
    )
    runtime.persist_approval_state()
    response: dict[str, Any] = result.model_dump(mode="json")
    return response
