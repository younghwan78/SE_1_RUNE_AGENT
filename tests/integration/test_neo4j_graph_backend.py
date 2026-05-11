"""Optional real Neo4j graph backend integration tests."""

import os

import pytest
from neo4j import GraphDatabase

from req_tracker.approvals.models import GraphDelta, GraphDeltaOperation
from req_tracker.graph.neo4j_backend import Neo4jGraphBackend
from req_tracker.ontology.models import EvidenceSpan, OntologyNode, TraceabilityEdge

NEO4J_TEST_URI = os.getenv("NEO4J_TEST_URI")
NEO4J_TEST_USERNAME = os.getenv("NEO4J_TEST_USERNAME", "neo4j")
NEO4J_TEST_PASSWORD = os.getenv("NEO4J_TEST_PASSWORD", "")
NEO4J_TEST_DATABASE = os.getenv("NEO4J_TEST_DATABASE", "neo4j")

pytestmark = pytest.mark.skipif(
    not NEO4J_TEST_URI or not NEO4J_TEST_PASSWORD,
    reason="NEO4J_TEST_URI and NEO4J_TEST_PASSWORD are not set",
)


def test_neo4j_graph_backend_applies_delta_against_real_db() -> None:
    assert NEO4J_TEST_URI is not None
    assert NEO4J_TEST_PASSWORD
    backend = Neo4jGraphBackend(
        uri=NEO4J_TEST_URI,
        username=NEO4J_TEST_USERNAME,
        password=NEO4J_TEST_PASSWORD,
        database=NEO4J_TEST_DATABASE,
    )
    source = _node("rune_it_node_req", "Requirement")
    target = _node("rune_it_node_ver", "Verification")
    edge = _edge(source.node_id, target.node_id)
    delta = GraphDelta(
        delta_id="rune_it_delta_edge",
        project_key="RUNE_CAM_ALPHA",
        operations=[
            GraphDeltaOperation(
                operation="create_edge",
                target_id=edge.edge_id,
                payload=edge.model_dump(mode="json"),
            )
        ],
        created_from_run_id="run_neo4j_it",
        created_from_step_id="step_neo4j_it",
    )

    _cleanup()
    try:
        backend.stage_baseline_nodes([source, target])
        backend.apply_delta(delta, "rune_it_apv:1")
        backend.apply_delta(delta, "rune_it_apv:1")

        assert len(backend.approved_edges()) == 1
        assert _edge_count() == 1
    finally:
        backend.close()
        _cleanup()


def _cleanup() -> None:
    assert NEO4J_TEST_URI is not None
    assert NEO4J_TEST_PASSWORD
    driver = GraphDatabase.driver(
        NEO4J_TEST_URI,
        auth=(NEO4J_TEST_USERNAME, NEO4J_TEST_PASSWORD),
    )
    try:
        with driver.session(database=NEO4J_TEST_DATABASE) as session:
            session.run(
                """
                MATCH (n)
                WHERE n.node_id IN ['rune_it_node_req', 'rune_it_node_ver']
                   OR n.key = 'rune_it_apv:1'
                DETACH DELETE n
                """
            )
    finally:
        driver.close()


def _edge_count() -> int:
    assert NEO4J_TEST_URI is not None
    assert NEO4J_TEST_PASSWORD
    driver = GraphDatabase.driver(
        NEO4J_TEST_URI,
        auth=(NEO4J_TEST_USERNAME, NEO4J_TEST_PASSWORD),
    )
    try:
        with driver.session(database=NEO4J_TEST_DATABASE) as session:
            record = session.run(
                """
                MATCH (:OntologyNode {node_id: 'rune_it_node_req'})
                      -[r:TRACEABILITY {edge_id: 'rune_it_edge'}]->
                      (:OntologyNode {node_id: 'rune_it_node_ver'})
                RETURN count(r) AS count
                """
            ).single()
            assert record is not None
            return int(record["count"])
    finally:
        driver.close()


def _evidence() -> EvidenceSpan:
    return EvidenceSpan(
        artifact_id="artifact_neo4j_it",
        source_url="dummy://artifact/neo4j-it",
        quote_hash="hash",
        extracted_text_preview="evidence",
    )


def _node(node_id: str, node_type: str) -> OntologyNode:
    return OntologyNode(
        node_id=node_id,
        node_type=node_type,  # type: ignore[arg-type]
        name=node_id,
        description=node_id,
        project_key="RUNE_CAM_ALPHA",
        evidence=[_evidence()],
        created_by="source",
        confidence_score=1.0,
    )


def _edge(source_node_id: str, target_node_id: str) -> TraceabilityEdge:
    return TraceabilityEdge(
        edge_id="rune_it_edge",
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation="verifies",
        reasoning="test",
        evidence=[_evidence()],
        is_inferred=False,
        confidence_score=1.0,
        approval_status="approved",
        approved_by="reviewer",
    )
