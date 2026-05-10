"""UI route contract tests."""

from fastapi.testclient import TestClient


def test_index_serves_operator_ui(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "SE 1 RUNE Agent" in response.text
    assert "Ontology View" in response.text
    assert "Scheduler" in response.text
    assert "/ui/app.js" in response.text


def test_static_assets_served(client: TestClient) -> None:
    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "runAnalysis" in response.text
