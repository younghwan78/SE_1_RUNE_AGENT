"""In-memory approved graph backend."""

from req_tracker.approvals.models import GraphDelta
from req_tracker.ontology.models import OntologyNode, TraceabilityEdge


class MemoryGraphBackend:
    """Simple approved graph backend for local validation."""

    def __init__(self) -> None:
        self.nodes: dict[str, OntologyNode] = {}
        self.edges: dict[str, TraceabilityEdge] = {}
        self._idempotency_keys: set[str] = set()

    def stage_baseline_nodes(self, nodes: list[OntologyNode]) -> None:
        """Load source-derived nodes into the local graph projection."""
        for node in nodes:
            self.nodes[node.node_id] = node

    def apply_delta(self, delta: GraphDelta, idempotency_key: str) -> None:
        """Apply an approved graph delta idempotently."""
        if idempotency_key in self._idempotency_keys:
            return
        for operation in delta.operations:
            if operation.operation == "create_node":
                node = OntologyNode.model_validate(operation.payload)
                self.nodes[node.node_id] = node
            elif operation.operation == "create_edge":
                edge = TraceabilityEdge.model_validate(operation.payload)
                self.edges[edge.edge_id] = edge
        self._idempotency_keys.add(idempotency_key)

    def approved_edges(self) -> list[TraceabilityEdge]:
        """Return approved edges only."""
        return list(self.edges.values())

    def subgraph(self, project_key: str) -> dict[str, list[dict[str, object]]]:
        """Return a serializable project-scoped graph."""
        return {
            "nodes": [
                node.model_dump(mode="json")
                for node in self.nodes.values()
                if node.project_key == project_key
            ],
            "edges": [edge.model_dump(mode="json") for edge in self.edges.values()],
        }

