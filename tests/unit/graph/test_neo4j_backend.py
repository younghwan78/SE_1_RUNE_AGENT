"""Neo4j graph backend tests."""

from typing import Any, Literal

from req_tracker.approvals.models import GraphDelta, GraphDeltaOperation
from req_tracker.graph.neo4j_backend import Neo4jGraphBackend
from req_tracker.ontology.models import EvidenceSpan, OntologyNode, TraceabilityEdge


class FakeRecord:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def __getitem__(self, key: str) -> Any:
        return self.values[key]


class FakeResult:
    def __init__(self, record: FakeRecord | None = None) -> None:
        self.record = record

    def single(self) -> FakeRecord | None:
        return self.record


class FakeTransaction:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.params: list[dict[str, Any]] = []
        self.seen_keys: set[str] = set()

    def run(self, query: str, **params: Any) -> FakeResult:
        self.queries.append(" ".join(query.split()))
        self.params.append(params)
        if "GraphIdempotencyKey" not in query:
            return FakeResult()
        key = str(params["idempotency_key"])
        created = key not in self.seen_keys
        self.seen_keys.add(key)
        return FakeResult(FakeRecord({"created": created}))


class FakeSession:
    def __init__(self, tx: FakeTransaction) -> None:
        self.tx = tx

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *_exc: object) -> Literal[False]:
        return False

    def execute_write(self, fn: Any, *args: Any) -> Any:
        return fn(self.tx, *args)


class FakeDriver:
    def __init__(self) -> None:
        self.tx = FakeTransaction()
        self.closed = False

    def session(self, *, database: str) -> FakeSession:
        assert database == "neo4j"
        return FakeSession(self.tx)

    def close(self) -> None:
        self.closed = True


def test_neo4j_backend_stages_nodes_and_applies_delta_idempotently() -> None:
    driver = FakeDriver()
    backend = Neo4jGraphBackend(
        uri="",
        username="neo4j",
        password="pw",
        driver=driver,
    )
    source = _node("node_req", "Requirement")
    target = _node("node_ver", "Verification")
    edge = _edge(source.node_id, target.node_id)
    delta = GraphDelta(
        delta_id="delta_edge_1",
        project_key="RUNE_CAM_ALPHA",
        operations=[
            GraphDeltaOperation(
                operation="create_edge",
                target_id=edge.edge_id,
                payload=edge.model_dump(mode="json"),
            )
        ],
        created_from_run_id="run_1",
        created_from_step_id="step_1",
    )

    backend.stage_baseline_nodes([source, target])
    backend.apply_delta(delta, "apv_1:1")
    backend.apply_delta(delta, "apv_1:1")

    assert set(backend.nodes) == {"node_req", "node_ver"}
    assert list(backend.edges) == ["edge_1"]
    assert len(backend.approved_edges()) == 1
    assert any("MERGE (k:GraphIdempotencyKey" in query for query in driver.tx.queries)
    assert driver.tx.queries.count(
        "MATCH (source:OntologyNode {node_id: $source_node_id}) "
        "MATCH (target:OntologyNode {node_id: $target_node_id}) "
        "MERGE (source)-[r:TRACEABILITY {edge_id: $edge_id}]->(target) "
        "SET r.relation = $relation, r.approval_status = $approval_status, "
        "r.schema_version = $schema_version, r.payload_json = $payload_json"
    ) == 1
    assert any(
        "payload_json" in node
        for params in driver.tx.params
        for node in params.get("nodes", [])
    )
    assert any("payload_json" in params for params in driver.tx.params if "edge_id" in params)

    backend.close()
    assert driver.closed is True


def _evidence() -> EvidenceSpan:
    return EvidenceSpan(
        artifact_id="artifact_1",
        source_url="dummy://artifact/1",
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
        edge_id="edge_1",
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
