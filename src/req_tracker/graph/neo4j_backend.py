"""Neo4j approved graph backend."""

import json
from typing import Any

from neo4j import GraphDatabase

from req_tracker.approvals.models import GraphDelta
from req_tracker.ontology.models import OntologyNode, TraceabilityEdge


class Neo4jGraphBackend:
    """Neo4j graph backend with local projection cache for API compatibility."""

    def __init__(
        self,
        *,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
        driver: Any | None = None,
    ) -> None:
        if not uri and driver is None:
            raise ValueError("neo4j uri is required when driver is not provided")
        self.database = database
        self._driver = driver or GraphDatabase.driver(uri, auth=(username, password))
        self.nodes: dict[str, OntologyNode] = {}
        self.edges: dict[str, TraceabilityEdge] = {}

    def close(self) -> None:
        """Close the underlying Neo4j driver."""
        self._driver.close()

    def stage_baseline_nodes(self, nodes: list[OntologyNode]) -> None:
        """Load source-derived nodes into Neo4j and the local projection cache."""
        if not nodes:
            return
        payloads = [_node_record(node.model_dump(mode="json")) for node in nodes]
        with self._driver.session(database=self.database) as session:
            session.execute_write(_merge_nodes, payloads)
        for node in nodes:
            self.nodes[node.node_id] = node

    def apply_delta(self, delta: GraphDelta, idempotency_key: str) -> None:
        """Apply an approved graph delta idempotently."""
        with self._driver.session(database=self.database) as session:
            applied = session.execute_write(
                _apply_delta,
                delta.model_dump(mode="json"),
                idempotency_key,
            )
        if not applied:
            return
        for operation in delta.operations:
            if operation.operation == "create_node":
                node = OntologyNode.model_validate(operation.payload)
                self.nodes[node.node_id] = node
            elif operation.operation == "create_edge":
                edge = TraceabilityEdge.model_validate(operation.payload)
                self.edges[edge.edge_id] = edge

    def approved_edges(self) -> list[TraceabilityEdge]:
        """Return approved edges from the local projection cache."""
        return list(self.edges.values())

    def subgraph(self, project_key: str) -> dict[str, list[dict[str, object]]]:
        """Return a serializable project-scoped graph from the local cache."""
        return {
            "nodes": [
                node.model_dump(mode="json")
                for node in self.nodes.values()
                if node.project_key == project_key
            ],
            "edges": [edge.model_dump(mode="json") for edge in self.edges.values()],
        }


def _merge_nodes(tx: Any, nodes: list[dict[str, Any]]) -> None:
    tx.run(
        """
        UNWIND $nodes AS node
        MERGE (n:OntologyNode {node_id: node.node_id})
        SET n.project_key = node.project_key,
            n.node_type = node.node_type,
            n.name = node.name,
            n.schema_version = node.schema_version,
            n.payload_json = node.payload_json
        """,
        nodes=nodes,
    )


def _apply_delta(tx: Any, delta: dict[str, Any], idempotency_key: str) -> bool:
    existing = tx.run(
        """
        MERGE (k:GraphIdempotencyKey {key: $idempotency_key})
        ON CREATE SET k.created = true, k.delta_id = $delta_id
        RETURN k.created AS created
        """,
        idempotency_key=idempotency_key,
        delta_id=delta["delta_id"],
    ).single()
    if existing is None or existing["created"] is not True:
        return False
    for operation in delta["operations"]:
        if operation["operation"] == "create_node":
            _merge_nodes(tx, [_node_record(operation["payload"])])
        elif operation["operation"] == "create_edge":
            _merge_edge(tx, operation["payload"])
    return True


def _merge_edge(tx: Any, edge: dict[str, Any]) -> None:
    record = _edge_record(edge)
    tx.run(
        """
        MATCH (source:OntologyNode {node_id: $source_node_id})
        MATCH (target:OntologyNode {node_id: $target_node_id})
        MERGE (source)-[r:TRACEABILITY {edge_id: $edge_id}]->(target)
        SET r.relation = $relation,
            r.approval_status = $approval_status,
            r.schema_version = $schema_version,
            r.payload_json = $payload_json
        """,
        **record,
    )


def _node_record(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node["node_id"],
        "project_key": node["project_key"],
        "node_type": node["node_type"],
        "name": node["name"],
        "schema_version": node["schema_version"],
        "payload_json": json.dumps(node, ensure_ascii=False, sort_keys=True),
    }


def _edge_record(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": edge["edge_id"],
        "source_node_id": edge["source_node_id"],
        "target_node_id": edge["target_node_id"],
        "relation": edge["relation"],
        "approval_status": edge["approval_status"],
        "schema_version": edge["schema_version"],
        "payload_json": json.dumps(edge, ensure_ascii=False, sort_keys=True),
    }
