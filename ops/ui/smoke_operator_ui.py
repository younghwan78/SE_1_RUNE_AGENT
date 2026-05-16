"""Smoke-test the operator UI and scalable graph projection path."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def run_operator_ui_smoke() -> dict[str, Any]:
    """Exercise static UI assets and the 150-node graph projection contract."""
    with TemporaryDirectory() as tmp_dir:
        app = create_app(
            Settings(
                artifact_root=Path(tmp_dir) / "artifacts",
                auth_mode="local",
            )
        )
        with TestClient(app) as client:
            index = client.get("/")
            script = client.get("/ui/app.js")
            module_responses = {
                path: client.get(path)
                for path in [
                    "/ui/core.js",
                    "/ui/dashboard.js",
                    "/ui/work_queue.js",
                    "/ui/graph_workbench.js",
                    "/ui/debug_workbench.js",
                    "/ui/source_health.js",
                ]
            }
            run = client.post(
                "/api/v1/runs/analyze",
                json={
                    "project_key": "RUNE_CAM_ALPHA",
                    "scenario": "RUNE_SCALE_150",
                    "run_id": "run_operator_ui_smoke_scale",
                },
            )
            overview = client.get(
                "/api/v1/graph/projection?mode=overview&limit_nodes=120"
            )
            dashboard = client.get("/api/v1/dashboard/summary")
            work_queue = client.get("/api/v1/dashboard/work-queue?limit=200")
            work_queue_preferences = client.get("/api/v1/dashboard/work-queue/preferences")
            work_queue_assignment = client.post(
                "/api/v1/dashboard/work-queue/assignments/q_operator_smoke",
                json={"project_key": "RUNE_CAM_ALPHA", "action": "assign"},
            )
            work_queue_assignments = client.get("/api/v1/dashboard/work-queue/assignments")
            source_health = client.get("/api/v1/dashboard/source-health")
            pending = client.get(
                "/api/v1/graph/projection?mode=pending&edge_filter=pending&limit_nodes=200"
            )
            orphans = client.get("/api/v1/graph/projection?mode=orphans&limit_nodes=200")
    index_text = index.text
    script_text = script.text
    graph_module_text = module_responses["/ui/graph_workbench.js"].text
    overview_payload = overview.json() if overview.status_code == 200 else {}
    dashboard_payload = dashboard.json() if dashboard.status_code == 200 else {}
    work_queue_payload = work_queue.json() if work_queue.status_code == 200 else {}
    work_queue_preferences_payload = (
        work_queue_preferences.json() if work_queue_preferences.status_code == 200 else {}
    )
    work_queue_assignment_payload = (
        work_queue_assignment.json() if work_queue_assignment.status_code == 200 else {}
    )
    work_queue_assignments_payload = (
        work_queue_assignments.json() if work_queue_assignments.status_code == 200 else {}
    )
    source_health_payload = source_health.json() if source_health.status_code == 200 else {}
    pending_payload = pending.json() if pending.status_code == 200 else {}
    orphans_payload = orphans.json() if orphans.status_code == 200 else {}
    checks = {
        "index_served": index.status_code == 200,
        "static_script_served": script.status_code == 200,
        "dashboard_first_controls_present": all(
            snippet in index_text
            for snippet in [
                "Project Command Center",
                "Work Queue",
                "Risk Snapshot",
                "Source Health",
                "Compact Graph Preview",
                "data-dashboard-view",
                'type="module"',
            ]
        ),
        "workspace_view_split_present": all(
            snippet in index_text
            for snippet in [
                "Workspace Views",
                'data-app-view="dashboard"',
                'data-app-view="work-queue"',
                'data-app-view="traceability"',
                'data-app-view="debug"',
                'data-app-view="source-health"',
                'data-app-view="eval"',
                'data-app-view="admin"',
            ]
        ),
        "work_queue_detail_present": all(
            snippet in index_text
            for snippet in [
                'id="work-queue-full"',
                'id="work-queue-detail"',
                'id="queue-filter-type"',
                'id="queue-filter-priority"',
                'id="queue-filter-saved"',
                "Queue Detail",
            ]
        ),
        "health_detail_views_present": all(
            snippet in index_text
            for snippet in [
                'id="source-health-full"',
                'id="run-health-full"',
                "Run Health Detail",
                "Source Health Detail",
            ]
        ),
        "graph_controls_present": all(
            snippet in index_text
            for snippet in [
                "Overview",
                "Orphans",
                "Pending",
                "Relationship Graph",
                "Zoom In",
                "Reset View",
            ]
        ),
        "svg_renderer_present": all(
            module_responses["/ui/graph_workbench.js"].status_code == 200
            and snippet in graph_module_text
            for snippet in [
                "renderOntologyGraph",
                "renderRelationshipGraph",
                "relationshipLayoutPositions",
                "relationshipPinnedPositions",
                "startRelationshipNodeDrag",
                "updateRelationshipNodeDrag",
                "zoomOntology",
                "pointermove",
            ]
        ),
        "dashboard_renderer_present": all(
            snippet in script_text
            for snippet in [
                'from "./core.js"',
                'from "./dashboard.js"',
                'from "./work_queue.js"',
                'from "./graph_workbench.js"',
                'from "./debug_workbench.js"',
                'from "./source_health.js"',
            ]
        ),
        "ui_modules_served": all(
            response.status_code == 200
            for response in module_responses.values()
        ),
        "hash_routing_present": all(
            snippet in script_text
            for snippet in ["applyHashRoute", "navigateTo", "hashchange"]
        ),
        "saved_filter_assignment_present": all(
            snippet in module_responses["/ui/work_queue.js"].text
            for snippet in [
                "/dashboard/work-queue/preferences",
                "/dashboard/work-queue/assignments",
                "localStorage",
                "applyWorkQueueFilters",
                "saveCurrentFilter",
                "assignSelectedWorkItem",
                "rune.workQueue.filters.v1",
                "rune.workQueue.assignments.v1",
            ]
        ),
        "scale_run_succeeded": run.status_code == 200,
        "dashboard_summary_contract": (
            dashboard.status_code == 200
            and dashboard_payload.get("counts", {}).get("total_nodes") == 150
            and dashboard_payload.get("counts", {}).get("pending_approvals") == 103
        ),
        "dashboard_work_queue_contract": (
            work_queue.status_code == 200
            and work_queue_payload.get("counts", {}).get("approval") == 103
            and work_queue_payload.get("counts", {}).get("finding") == 48
        ),
        "dashboard_work_queue_preference_contract": (
            work_queue_preferences.status_code == 200
            and work_queue_preferences_payload.get("project_key") == "RUNE_CAM_ALPHA"
            and isinstance(work_queue_preferences_payload.get("saved_filters"), dict)
        ),
        "dashboard_work_queue_assignment_contract": (
            work_queue_assignment.status_code == 200
            and work_queue_assignment_payload.get("queue_id") == "q_operator_smoke"
            and work_queue_assignment_payload.get("assigned_to") == "local"
            and work_queue_assignments.status_code == 200
            and len(work_queue_assignments_payload.get("assignments", [])) == 1
        ),
        "dashboard_source_health_contract": (
            source_health.status_code == 200
            and any(
                item.get("source_type") == "dummy" and item.get("status") == "fresh"
                for item in source_health_payload.get("sources", [])
            )
        ),
        "overview_scale_contract": (
            overview.status_code == 200
            and overview_payload.get("counts", {}).get("total_nodes", 0) >= 150
            and overview_payload.get("counts", {}).get("visible_nodes", 0) <= 120
        ),
        "pending_mode_contract": (
            pending.status_code == 200
            and pending_payload.get("counts", {}).get("visible_pending_edges", 0) > 0
        ),
        "orphan_mode_contract": (
            orphans.status_code == 200
            and orphans_payload.get("counts", {}).get("orphan_nodes", 0) > 0
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "dashboard_counts": dashboard_payload.get("counts", {}),
        "work_queue_counts": work_queue_payload.get("counts", {}),
        "graph_counts": overview_payload.get("counts", {}),
        "schema_version": "v1",
    }


def main() -> int:
    """CLI entrypoint."""
    result = run_operator_ui_smoke()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
