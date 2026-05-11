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
            pending = client.get(
                "/api/v1/graph/projection?mode=pending&edge_filter=pending&limit_nodes=200"
            )
            orphans = client.get("/api/v1/graph/projection?mode=orphans&limit_nodes=200")
    index_text = index.text
    script_text = script.text
    overview_payload = overview.json() if overview.status_code == 200 else {}
    pending_payload = pending.json() if pending.status_code == 200 else {}
    orphans_payload = orphans.json() if orphans.status_code == 200 else {}
    checks = {
        "index_served": index.status_code == 200,
        "static_script_served": script.status_code == 200,
        "graph_controls_present": all(
            snippet in index_text
            for snippet in ["Overview", "Orphans", "Pending", "Zoom In", "Reset View"]
        ),
        "svg_renderer_present": all(
            snippet in script_text
            for snippet in ["renderOntologyGraph", "zoomOntology", "pointermove"]
        ),
        "scale_run_succeeded": run.status_code == 200,
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
