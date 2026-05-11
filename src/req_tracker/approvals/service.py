"""Approval service."""

import json
from datetime import UTC, datetime

from req_tracker.approvals.models import (
    ApprovalDecision,
    ApprovalItem,
    GraphDelta,
    GraphDeltaOperation,
)
from req_tracker.debug.hash import stable_hash
from req_tracker.feedback.models import FeedbackAction, FeedbackEvent
from req_tracker.graph.base import GraphBackend
from req_tracker.ontology.models import TraceabilityEdge
from req_tracker.reasoning.scoring import approval_risk_for_edge


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
                risk_level=approval_risk_for_edge(edge),
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
        graph: GraphBackend,
    ) -> ApprovalItem:
        """Apply an approval decision."""
        item = self.items[decision.approval_id]
        if item.status != "pending":
            return item
        if _is_stale_decision(item, decision):
            updated = item.model_copy(
                update={
                    "status": "stale",
                    "version": item.version + 1,
                    "updated_at": datetime.now(UTC),
                }
            )
            self.items[item.approval_id] = updated
            return updated
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
            if item.graph_delta_ref and decision.correction_payload:
                delta = self._modified_delta(item, decision)
                self.deltas[delta.delta_id] = delta
                graph.apply_delta(
                    delta,
                    idempotency_key=f"{decision.approval_id}:{item.version}:modify",
                )
            status = "modified_approved"
        updated = item.model_copy(
            update={
                "status": status,
                "version": item.version + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        self.items[item.approval_id] = updated
        self.feedback.append(
            FeedbackEvent(
                feedback_id=f"fb_{stable_hash(decision)[:16]}",
                target_type="edge",
                target_id=item.proposal_ref,
                action=_feedback_action(status),
                user_id=decision.decided_by,
                user_role=item.owner_role,
                reason_code=decision.reason_code,  # type: ignore[arg-type]
                correction_text=_correction_text(decision),
            )
        )
        return updated

    def _modified_delta(
        self,
        item: ApprovalItem,
        decision: ApprovalDecision,
    ) -> GraphDelta:
        original = self.deltas[item.graph_delta_ref or ""]
        operations: list[GraphDeltaOperation] = []
        for operation in original.operations:
            payload = dict(operation.payload)
            payload.update(decision.correction_payload or {})
            if operation.operation == "create_edge":
                payload["approval_status"] = "approved"
                payload["approved_by"] = decision.decided_by
                payload["approved_at"] = decision.decided_at
                edge = TraceabilityEdge.model_validate(payload)
                payload = edge.model_dump(mode="json")
            operations.append(
                GraphDeltaOperation(
                    operation=operation.operation,
                    target_id=operation.target_id,
                    payload=payload,
                )
            )
        return GraphDelta(
            delta_id=f"{original.delta_id}_modified_v{item.version}",
            project_key=original.project_key,
            operations=operations,
            created_from_run_id=original.created_from_run_id,
            created_from_step_id=original.created_from_step_id,
        )


def _feedback_action(status: str) -> FeedbackAction:
    if status == "approved":
        return "approved"
    if status == "modified_approved":
        return "modified"
    if status == "held":
        return "commented"
    return "rejected"


def _is_stale_decision(item: ApprovalItem, decision: ApprovalDecision) -> bool:
    if decision.expected_version is not None and decision.expected_version != item.version:
        return True
    return (
        decision.expected_proposal_hash is not None
        and decision.expected_proposal_hash != item.proposal_hash
    )


def _correction_text(decision: ApprovalDecision) -> str | None:
    if not decision.correction_payload:
        return None
    return json.dumps(decision.correction_payload, sort_keys=True)
