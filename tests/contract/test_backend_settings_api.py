"""Backend setting contract tests."""

import pytest

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def test_create_app_rejects_unsupported_graph_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported GRAPH_BACKEND"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", graph_backend="other"))


def test_create_app_requires_neo4j_connection_settings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="NEO4J_URI and NEO4J_PASSWORD"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", graph_backend="neo4j"))


def test_create_app_rejects_unsupported_vector_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported VECTOR_BACKEND"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", vector_backend="other"))


def test_create_app_requires_qdrant_url(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="QDRANT_URL"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", vector_backend="qdrant"))
