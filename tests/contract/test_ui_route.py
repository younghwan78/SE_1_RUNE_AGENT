"""UI route contract tests."""

from fastapi.testclient import TestClient


def test_index_serves_operator_ui(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "SE 1 RUNE Agent" in response.text
    assert "Project Command Center" in response.text
    assert "Work Queue" in response.text
    assert "Risk Snapshot" in response.text
    assert "Workspace Views" in response.text
    assert 'data-app-view="dashboard"' in response.text
    assert 'data-app-view="work-queue"' in response.text
    assert 'data-app-view="traceability"' in response.text
    assert 'data-app-view="debug"' in response.text
    assert 'data-app-view="source-health"' in response.text
    assert 'data-app-view="eval"' in response.text
    assert 'data-app-view="admin"' in response.text
    assert 'id="work-queue-full"' in response.text
    assert 'id="work-queue-detail"' in response.text
    assert 'id="queue-filter-type"' in response.text
    assert 'id="queue-filter-priority"' in response.text
    assert 'id="queue-filter-owner"' in response.text
    assert 'id="queue-filter-search"' in response.text
    assert 'id="queue-filter-save-name"' in response.text
    assert 'id="queue-filter-saved"' in response.text
    assert 'id="source-health-full"' in response.text
    assert 'id="run-health-full"' in response.text
    assert "Traceability Workbench" in response.text
    assert "Compact Graph Preview" in response.text
    assert "Zoom In" in response.text
    assert "Zoom Out" in response.text
    assert "Reset View" in response.text
    assert "Orphans" in response.text
    assert "Neighborhood" in response.text
    assert "Scheduler" in response.text
    assert "LLM Payload Diff" in response.text
    assert "Graph Delta Preview" in response.text
    assert '<script type="module" src="/ui/app.js"' in response.text


def test_static_assets_served(client: TestClient) -> None:
    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "runAnalysis" in response.text
    assert 'from "./core.js"' in response.text
    assert 'from "./dashboard.js"' in response.text
    assert 'from "./work_queue.js"' in response.text
    assert 'from "./graph_workbench.js"' in response.text
    assert 'from "./debug_workbench.js"' in response.text
    assert 'from "./source_health.js"' in response.text
    assert "applyHashRoute" in response.text
    assert "navigateTo" in response.text


def test_static_ui_modules_served(client: TestClient) -> None:
    expected_snippets = {
        "/ui/core.js": ["state", "navigateTo", "applyHashRoute", "showView"],
        "/ui/dashboard.js": ["renderDashboard", "renderRiskSnapshot", "renderGraphPreview"],
        "/ui/work_queue.js": ["renderWorkQueue", "renderWorkQueueDetail", "selectWorkItem"],
        "/ui/graph_workbench.js": ["renderOntologyGraph", "zoomOntology", "renderOntologyDetail"],
        "/ui/debug_workbench.js": ["renderDebugSummary", "renderDebugDiffView", "/diff-view"],
        "/ui/source_health.js": ["renderSourceHealthFull", "renderRunHealthFull"],
    }

    for path, snippets in expected_snippets.items():
        response = client.get(path)

        assert response.status_code == 200
        for snippet in snippets:
            assert snippet in response.text


def test_work_queue_module_supports_saved_filters_and_local_assignment(
    client: TestClient,
) -> None:
    response = client.get("/ui/work_queue.js")

    assert response.status_code == 200
    assert "localStorage" in response.text
    assert "applyWorkQueueFilters" in response.text
    assert "saveCurrentFilter" in response.text
    assert "assignSelectedWorkItem" in response.text
    assert "rune.workQueue.filters.v1" in response.text
    assert "rune.workQueue.assignments.v1" in response.text
