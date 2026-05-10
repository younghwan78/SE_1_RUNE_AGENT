"""Approval service."""

from req_tracker.approvals.models import (
    ApprovalDecision,
    ApprovalItem,
    GraphDelta,
    GraphDeltaOperation,
)
from req_tracker.debug.hash import stable_hash
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.ontology.models import TraceabilityEdge


class ApprovalService:
    """Create and decide approval items."""

    def __init__(self) -> None:
        self.items: dict[str, ApprovalItem] = {}
        self.deltas: dict[str, GraphDelta] = {}
        self.feedback: list[FeedbackEvent] = []

    def stage_edges(
        self,
        *,
        project_key: str,
        run_id: str,
        step_id: str,
        edges: list[TraceabilityEdge],
    ) -> list[ApprovalItem]:
        """Create approval items for candidate edges."""
        approvals: list[ApprovalItem] = []
        for edge in edges:
            approved_edge = edge.model_copy(
                update={"approval_status": "approved", "approved_by": "system"}
            )
            delta = GraphDelta(
                delta_id=f"delta_{edge.edge_id}",
                project_key=project_key,
                operations=[
                    GraphDeltaOperation(
                        operation="create_edge",
                        target_id=edge.edge_id,
                        payload=approved_edge.model_dump(mode="json"),
                    )
                ],
                created_from_run_id=run_id,
                created_from_step_id=step_id,
            )
            proposal_hash = stable_hash(edge)
            approval = ApprovalItem(
                approval_id=f"apv_{proposal_hash[:16]}",
                project_key=project_key,
                proposal_type="edge",
                proposal_ref=edge.edge_id,
                graph_delta_ref=delta.delta_id,
                risk_level="medium",
                owner_role="System Architect",
                created_from_run_id=run_id,
                created_from_step_id=step_id,
                proposal_hash=proposal_hash,
            )
            self.items[approval.approval_id] = approval
            self.deltas[delta.delta_id] = delta
            approvals.append(approval)
        return approvals

    def decide(
        self,
        decision: ApprovalDecision,
        graph: MemoryGraphBackend,
    ) -> ApprovalItem:
        """Apply an approval decision."""
        item = self.items[decision.approval_id]
        if item.status != "pending":
            return item
        if decision.action == "approve" and item.graph_delta_ref:
            graph.apply_delta(
                self.deltas[item.graph_delta_ref],
                idempotency_key=f"{decision.approval_id}:{item.version}",
            )
            status = "approved"
        elif decision.action == "reject":
            status = "rejected"
        elif decision.action == "hold":
            status = "held"
        else:
            status = "modified_approved"
        updated = item.model_copy(update={"status": status, "version": item.version + 1})
        self.items[item.approval_id] = updated
        self.feedback.append(
            FeedbackEvent(
                feedback_id=f"fb_{stable_hash(decision)[:16]}",
                target_type="edge",
                target_id=item.proposal_ref,
                action="approved" if status == "approved" else "rejected",
                user_id=decision.decided_by,
                user_role=item.owner_role,
                reason_code=decision.reason_code,  # type: ignore[arg-type]
                correction_text=None,
            )
        )
        return updated
