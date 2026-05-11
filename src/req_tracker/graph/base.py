"""Graph backend contract."""

from typing import Protocol, runtime_checkable

from req_tracker.approvals.models import GraphDelta
from req_tracker.ontology.models import OntologyNode, TraceabilityEdge


@runtime_checkable
class GraphBackend(Protocol):
    """Approved graph backend interface shared by memory and production stores."""

    nodes: dict[str, OntologyNode]
    edges: dict[str, TraceabilityEdge]

    def stage_baseline_nodes(self, nodes: list[OntologyNode]) -> None:
        """Load source-derived nodes into the graph projection."""

    def apply_delta(self, delta: GraphDelta, idempotency_key: str) -> None:
        """Apply an approved graph delta idempotently."""

    def approved_edges(self) -> list[TraceabilityEdge]:
        """Return approved edges only."""

    def subgraph(self, project_key: str) -> dict[str, list[dict[str, object]]]:
        """Return a serializable project-scoped graph."""
