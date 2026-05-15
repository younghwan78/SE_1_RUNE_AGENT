"""Dashboard read-model aggregation service."""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from req_tracker.adapters.base import SourceSyncCursorState
from req_tracker.approvals.models import RiskLevel
from req_tracker.dashboard.models import (
    DashboardCounts,
    DashboardEvalGate,
    DashboardHealth,
    DashboardLastRun,
    DashboardSchedule,
    DashboardSummary,
    FreshnessStatus,
    QueuePriority,
    RecentActivityItem,
    RecentActivityResponse,
    RiskSummaryResponse,
    RunHealthResponse,
    SourceHealthItem,
    SourceHealthResponse,
    WorkQueueCounts,
    WorkQueueItem,
    WorkQueueResponse,
)
from req_tracker.evals.datasets import build_eval_candidates
from req_tracker.evals.runner import run_local_eval_gate
from req_tracker.graph.projection import build_graph_projection
from req_tracker.ontology.models import Finding, Severity, TraceabilityEdge

_SEVERITY_PRIORITY: dict[Severity, QueuePriority] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}
_RISK_PRIORITY: dict[RiskLevel, QueuePriority] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}
_PRIORITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}
_ITEM_TYPE_RANK = {
    "failed_run": 0,
    "finding": 1,
    "source_warning": 2,
    "approval": 3,
    "eval_gate": 4,
}
_SOURCE_TYPES = ("jira", "confluence", "decision_archive", "email", "dummy")


class DashboardService:
    """Build product dashboard read models from runtime state."""

    def __init__(self, runtime: Any, *, new_id: Any | None = None) -> None:
        self.runtime = runtime
        self.new_id = new_id or (lambda prefix: f"{prefix}_dashboard")

    def summary(self, project_key: str) -> DashboardSummary:
        """Build first-viewport dashboard summary."""
        counts = self._counts(project_key)
        eval_gate = self._eval_gate()
        source_health = self.source_health(project_key)
        source_freshness = {
            item.source_type: item.status
            for item in source_health.sources
        }
        schedule_status = self.runtime.scheduler.status()
        return DashboardSummary(
            project_key=project_key,
            generated_at=datetime.now(UTC),
            traceability_health=_derive_health(
                counts=counts,
                latest_run=self._latest_run(project_key),
                source_freshness=source_freshness,
                eval_gate=eval_gate,
            ),
            last_run=self._run_summary(self._latest_run(project_key)),
            counts=counts,
            source_freshness=source_freshness,
            eval_gate=eval_gate,
            schedule=DashboardSchedule(
                enabled=schedule_status.enabled,
                running=schedule_status.running,
                last_run_id=schedule_status.last_run_id,
                next_run_at=schedule_status.next_run_at,
                last_error=schedule_status.last_error,
            ),
        )

    def work_queue(
        self,
        project_key: str,
        *,
        status: str = "open",
        limit: int = 50,
    ) -> WorkQueueResponse:
        """Build a prioritized product work queue."""
        items = [
            *self._finding_items(project_key),
            *self._approval_items(project_key),
            *self._failed_run_items(project_key),
            *self._source_warning_items(project_key),
            *self._eval_gate_items(project_key),
        ]
        if status != "all":
            items = [item for item in items if item.status == status]
        sorted_items = sorted(
            items,
            key=lambda item: (
                _PRIORITY_RANK[item.priority],
                _ITEM_TYPE_RANK[item.item_type],
                item.created_at or datetime.min.replace(tzinfo=UTC),
                item.queue_id,
            ),
        )
        capped_items = sorted_items[: min(max(limit, 1), 200)]
        return WorkQueueResponse(
            project_key=project_key,
            items=capped_items,
            counts=_work_queue_counts(items),
        )

    def source_health(self, project_key: str) -> SourceHealthResponse:
        """Build source health from persisted source sync cursors."""
        cursors = [
            cursor
            for cursor in self.runtime.source_sync_cursors.values()
            if cursor.project_key == project_key
        ]
        by_source: dict[str, SourceSyncCursorState] = {}
        for cursor in sorted(cursors, key=lambda item: item.updated_at):
            by_source[cursor.source_type] = cursor
        known_sources = [
            _source_health_item(source_type, cursor)
            for source_type, cursor in sorted(by_source.items())
        ]
        missing_sources = [
            _source_health_item(source_type, None)
            for source_type in _SOURCE_TYPES
            if source_type not in by_source and source_type != "email"
        ]
        sources = [*known_sources, *missing_sources]
        if not sources:
            sources = [
                SourceHealthItem(source_type="dummy", status="unknown"),
            ]
        return SourceHealthResponse(project_key=project_key, sources=sources)

    def run_health(self, project_key: str, *, limit: int = 10) -> RunHealthResponse:
        """Build dashboard run-health state."""
        runs = self._project_runs(project_key)
        recent = sorted(runs, key=lambda run: run.started_at, reverse=True)[
            : min(max(limit, 1), 50)
        ]
        failed = [run for run in runs if run.status == "failed"]
        return RunHealthResponse(
            project_key=project_key,
            latest_run=self._run_summary(self._latest_run(project_key)),
            total_runs=len(runs),
            failed_runs=len(failed),
            recent_runs=[summary for run in recent if (summary := self._run_summary(run))],
        )

    def risk_summary(self, project_key: str, *, limit: int = 10) -> RiskSummaryResponse:
        """Build risk summary and top finding items."""
        findings = self._project_findings(project_key)
        severity_counts = Counter(finding.severity for finding in findings)
        top_findings = [
            item
            for item in self._finding_items(project_key)
            if item.status == "open"
        ][: min(max(limit, 1), 50)]
        return RiskSummaryResponse(
            project_key=project_key,
            counts=self._counts(project_key),
            risk_by_severity=_severity_count_payload(severity_counts),
            top_findings=top_findings,
        )

    def recent_activity(self, project_key: str, *, limit: int = 20) -> RecentActivityResponse:
        """Build sanitized recent activity from audit events."""
        events = [
            event
            for event in self.runtime.audit.events.values()
            if event.project_key in {project_key, None}
        ]
        recent = sorted(events, key=lambda event: event.created_at, reverse=True)[
            : min(max(limit, 1), 100)
        ]
        return RecentActivityResponse(
            project_key=project_key,
            items=[
                RecentActivityItem(
                    activity_id=event.audit_id,
                    action=event.action,
                    outcome=event.outcome,
                    actor_id=event.actor_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    created_at=event.created_at,
                    summary=(
                        f"{event.action} {event.outcome} for "
                        f"{event.target_type}:{event.target_id}"
                    ),
                )
                for event in recent
            ],
        )

    def _counts(self, project_key: str) -> DashboardCounts:
        nodes = [
            node
            for node in self.runtime.graph.nodes.values()
            if node.project_key == project_key
        ]
        approved_edges = [
            edge
            for edge in self.runtime.graph.edges.values()
            if _edge_project_key(self.runtime, edge) == project_key
        ]
        pending_edges = _pending_edges(self.runtime, project_key)
        findings = self._project_findings(project_key)
        open_findings = [
            finding for finding in findings if finding.approval_status == "open"
        ]
        pending_approvals = [
            item
            for item in self.runtime.approvals.items.values()
            if item.project_key == project_key and item.status == "pending"
        ]
        projection = build_graph_projection(
            nodes=nodes,
            approved_edges=approved_edges,
            pending_edges=pending_edges,
            findings=findings,
            mode="overview",
            limit_nodes=120,
        )
        failed_runs = [
            run for run in self._project_runs(project_key) if run.status == "failed"
        ]
        source_warning_count = sum(
            len(cursor.source_warnings) + int(cursor.partial_failure)
            for cursor in self.runtime.source_sync_cursors.values()
            if cursor.project_key == project_key
        )
        return DashboardCounts(
            total_nodes=projection.counts.total_nodes,
            approved_edges=projection.counts.approved_edges,
            pending_edges=projection.counts.pending_edges,
            orphan_nodes=projection.counts.orphan_nodes,
            open_findings=len(open_findings),
            critical_findings=sum(1 for item in open_findings if item.severity == "critical"),
            high_findings=sum(1 for item in open_findings if item.severity == "high"),
            pending_approvals=len(pending_approvals),
            feedback_events=len(self.runtime.approvals.feedback),
            failed_runs=len(failed_runs),
            source_warnings=source_warning_count,
        )

    def _project_runs(self, project_key: str) -> list[Any]:
        return [
            run for run in self.runtime.traces.runs.values() if run.project_key == project_key
        ]

    def _latest_run(self, project_key: str) -> Any | None:
        runs = self._project_runs(project_key)
        if not runs:
            return None
        return max(runs, key=lambda run: run.started_at)

    def _project_findings(self, project_key: str) -> list[Finding]:
        by_id: dict[str, Finding] = {}
        for analysis in self.runtime.analyses.values():
            if analysis.run.project_key != project_key:
                continue
            for finding in analysis.findings:
                by_id[finding.finding_id] = self.runtime.findings.get(
                    finding.finding_id,
                    finding,
                )
        for finding in self.runtime.findings.values():
            if _finding_project_key(self.runtime, finding) == project_key:
                by_id[finding.finding_id] = finding
        return list(by_id.values())

    def _run_summary(self, run: Any | None) -> DashboardLastRun | None:
        if run is None:
            return None
        return DashboardLastRun(
            run_id=run.run_id,
            run_type=run.run_type,
            status=run.status,
            completed_at=run.completed_at,
            failure_code=run.failure_code,
            failure_message=run.failure_message,
        )

    def _eval_gate(self) -> DashboardEvalGate:
        candidates = build_eval_candidates(self.runtime.approvals.feedback)
        gate = run_local_eval_gate(candidates, self.new_id("eval"))
        reason = ", ".join(gate.blockers[:2]) if gate.blockers else None
        return DashboardEvalGate(
            status=gate.status,
            reason=reason,
            eval_run_id=gate.eval_run_id,
        )

    def _finding_items(self, project_key: str) -> list[WorkQueueItem]:
        items: list[WorkQueueItem] = []
        for finding in self._project_findings(project_key):
            item_status = "open" if finding.approval_status == "open" else finding.approval_status
            items.append(
                WorkQueueItem(
                    queue_id=f"wq_finding_{finding.finding_id}",
                    item_type="finding",
                    priority=_SEVERITY_PRIORITY[finding.severity],
                    status=item_status,
                    title=finding.finding_type,
                    summary=finding.description,
                    project_key=project_key,
                    source_type=_source_type_for_finding(self.runtime, finding),
                    owner_role=_owner_for_finding(finding),
                    related_run_id=_run_id_for_finding(self.runtime, project_key, finding),
                    related_node_ids=finding.affected_node_ids,
                    related_edge_ids=finding.affected_edge_ids,
                    related_finding_id=finding.finding_id,
                    evidence_refs=_evidence_refs(finding.evidence),
                    actions=[
                        "inspect",
                        "acknowledge",
                        "resolve",
                        "dismiss",
                        "open_graph",
                        "open_debug",
                    ],
                )
            )
        return items

    def _approval_items(self, project_key: str) -> list[WorkQueueItem]:
        items: list[WorkQueueItem] = []
        for approval in self.runtime.approvals.items.values():
            if approval.project_key != project_key:
                continue
            item_status = "open" if approval.status == "pending" else approval.status
            title = f"{approval.proposal_type} proposal requires review"
            items.append(
                WorkQueueItem(
                    queue_id=f"wq_approval_{approval.approval_id}",
                    item_type="approval",
                    priority=_RISK_PRIORITY[approval.risk_level],
                    status=item_status,
                    title=title,
                    summary=(
                        f"{approval.proposal_type} {approval.proposal_ref} from "
                        f"{approval.created_from_run_id} is {approval.status}."
                    ),
                    project_key=project_key,
                    owner_role=approval.owner_role,
                    related_run_id=approval.created_from_run_id,
                    related_approval_id=approval.approval_id,
                    evidence_refs=[f"graph-delta:{approval.graph_delta_ref}"]
                    if approval.graph_delta_ref
                    else [],
                    actions=[
                        "inspect",
                        "approve",
                        "reject",
                        "modify",
                        "hold",
                        "open_graph",
                        "open_debug",
                    ],
                    created_at=approval.created_at,
                )
            )
        return items

    def _failed_run_items(self, project_key: str) -> list[WorkQueueItem]:
        items: list[WorkQueueItem] = []
        for run in self._project_runs(project_key):
            if run.status != "failed":
                continue
            items.append(
                WorkQueueItem(
                    queue_id=f"wq_failed_run_{run.run_id}",
                    item_type="failed_run",
                    priority="critical",
                    status="open",
                    title=f"{run.run_type} run failed",
                    summary=run.failure_message or run.failure_code or "Run failed.",
                    project_key=project_key,
                    related_run_id=run.run_id,
                    actions=["open_debug", "replay", "rerun"],
                    created_at=run.completed_at or run.started_at,
                )
            )
        return items

    def _source_warning_items(self, project_key: str) -> list[WorkQueueItem]:
        items: list[WorkQueueItem] = []
        for cursor in self.runtime.source_sync_cursors.values():
            if cursor.project_key != project_key:
                continue
            warnings = list(cursor.source_warnings)
            if cursor.partial_failure:
                warnings.append("partial source fetch failure")
            for index, warning in enumerate(warnings):
                items.append(
                    WorkQueueItem(
                        queue_id=f"wq_source_{cursor.cursor_id}_{index}",
                        item_type="source_warning",
                        priority="high" if cursor.partial_failure else "medium",
                        status="open",
                        title=f"{cursor.source_type} source warning",
                        summary=warning,
                        project_key=project_key,
                        source_type=cursor.source_type,
                        related_run_id=cursor.run_id,
                        evidence_refs=[f"source-cursor:{cursor.cursor_id}"],
                        actions=["inspect_source", "rerun_ingestion", "open_debug"],
                        created_at=cursor.updated_at,
                    )
                )
        return items

    def _eval_gate_items(self, project_key: str) -> list[WorkQueueItem]:
        gate = self._eval_gate()
        if gate.status == "passed":
            return []
        return [
            WorkQueueItem(
                queue_id=f"wq_eval_gate_{gate.eval_run_id or 'current'}",
                item_type="eval_gate",
                priority="medium" if gate.status == "warning" else "high",
                status="open",
                title=f"Eval gate {gate.status}",
                summary=gate.reason or "Eval gate is not passed.",
                project_key=project_key,
                actions=["open_eval", "inspect_feedback"],
            )
        ]


def _derive_health(
    *,
    counts: DashboardCounts,
    latest_run: Any | None,
    source_freshness: dict[str, FreshnessStatus],
    eval_gate: DashboardEvalGate,
) -> DashboardHealth:
    if latest_run is None:
        return "unknown"
    if latest_run.status == "failed" or counts.critical_findings > 0:
        return "blocked"
    if counts.high_findings > 0 or counts.pending_approvals > 0:
        return "attention_required"
    if any(status in {"failed", "stale", "warning"} for status in source_freshness.values()):
        return "attention_required"
    if eval_gate.status != "passed":
        return "attention_required"
    return "healthy"


def _work_queue_counts(items: list[WorkQueueItem]) -> WorkQueueCounts:
    return WorkQueueCounts(
        open=sum(1 for item in items if item.status == "open"),
        critical=sum(1 for item in items if item.priority == "critical"),
        high=sum(1 for item in items if item.priority == "high"),
        approval=sum(1 for item in items if item.item_type == "approval"),
        finding=sum(1 for item in items if item.item_type == "finding"),
        source_warning=sum(1 for item in items if item.item_type == "source_warning"),
        failed_run=sum(1 for item in items if item.item_type == "failed_run"),
        eval_gate=sum(1 for item in items if item.item_type == "eval_gate"),
    )


def _source_health_item(
    source_type: str,
    cursor: SourceSyncCursorState | None,
) -> SourceHealthItem:
    if cursor is None:
        status: FreshnessStatus = "disabled" if source_type == "email" else "unknown"
        return SourceHealthItem(source_type=source_type, status=status)
    if cursor.partial_failure:
        status = "failed"
    elif cursor.source_warnings:
        status = "warning"
    else:
        status = "fresh"
    return SourceHealthItem(
        source_type=cursor.source_type,
        status=status,
        mode=cursor.source_type,
        last_run_id=cursor.run_id,
        cursor_id=cursor.cursor_id,
        artifact_count=cursor.artifact_count,
        warning_count=len(cursor.source_warnings),
        last_success_at=cursor.updated_at if status == "fresh" else None,
        source_warnings=cursor.source_warnings,
    )


def _edge_project_key(runtime: Any, edge: TraceabilityEdge) -> str | None:
    source_node = runtime.graph.nodes.get(edge.source_node_id)
    if source_node is None:
        return None
    project_key = getattr(source_node, "project_key", None)
    return project_key if isinstance(project_key, str) else None


def _pending_edges(runtime: Any, project_key: str) -> list[TraceabilityEdge]:
    approval_by_delta = {
        item.graph_delta_ref
        for item in runtime.approvals.items.values()
        if item.project_key == project_key and item.status == "pending" and item.graph_delta_ref
    }
    pending_edges: list[TraceabilityEdge] = []
    for delta in runtime.approvals.deltas.values():
        if delta.project_key != project_key or delta.delta_id not in approval_by_delta:
            continue
        for operation in delta.operations:
            if operation.operation != "create_edge":
                continue
            payload = dict(operation.payload)
            payload["approval_status"] = "pending"
            payload["approved_by"] = None
            payload["approved_at"] = None
            pending_edges.append(TraceabilityEdge.model_validate(payload))
    return pending_edges


def _finding_project_key(runtime: Any, finding: Finding) -> str | None:
    for node_id in finding.affected_node_ids:
        node = runtime.graph.nodes.get(node_id)
        if node is not None:
            project_key = getattr(node, "project_key", None)
            return project_key if isinstance(project_key, str) else None
    for edge_id in finding.affected_edge_ids:
        edge = runtime.graph.edges.get(edge_id)
        if edge is not None:
            return _edge_project_key(runtime, edge)
    return None


def _source_type_for_finding(runtime: Any, finding: Finding) -> str | None:
    for evidence in finding.evidence:
        artifact_id = evidence.artifact_id
        for analysis in runtime.analyses.values():
            for artifact in analysis.artifacts:
                if artifact.artifact_id == artifact_id:
                    source_type = getattr(artifact, "source_type", None)
                    return source_type if isinstance(source_type, str) else None
    return None


def _owner_for_finding(finding: Finding) -> str:
    if finding.severity in {"critical", "high"}:
        return "System Architect"
    return "Reviewer"


def _run_id_for_finding(runtime: Any, project_key: str, finding: Finding) -> str | None:
    for run_id, analysis in runtime.analyses.items():
        if analysis.run.project_key != project_key:
            continue
        if any(item.finding_id == finding.finding_id for item in analysis.findings):
            return run_id if isinstance(run_id, str) else None
    return None


def _evidence_refs(evidence: list[Any]) -> list[str]:
    return [f"artifact:{item.artifact_id}" for item in evidence]


def _severity_count_payload(severity_counts: Counter[Severity]) -> dict[str, int]:
    return {
        "critical": severity_counts.get("critical", 0),
        "high": severity_counts.get("high", 0),
        "medium": severity_counts.get("medium", 0),
        "low": severity_counts.get("low", 0),
    }
