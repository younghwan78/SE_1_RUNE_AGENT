"""Runtime state for local API execution."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from req_tracker.adapters.base import SourceSyncCursorState
from req_tracker.approvals.models import ApprovalItem, GraphDelta
from req_tracker.approvals.service import ApprovalService
from req_tracker.audit.archive import AuditArchiveWriter, LocalAuditArchiveStore
from req_tracker.audit.models import AuditEvent, AuditRetentionPolicy
from req_tracker.audit.service import AuditService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.models import AgentRun, AgentStepTrace, LLMCallTrace, TriggerSource
from req_tracker.debug.replay import ReplayResult
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.graph.base import GraphBackend
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.ontology.models import Finding, OntologyNode, TraceabilityEdge
from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.scheduler.service import RunScheduler, SchedulerLeaseManager
from req_tracker.storage.state_store import StateStore
from req_tracker.vector.base import VectorBackend
from req_tracker.vector.memory_backend import MemoryVectorBackend
from req_tracker.workflows.analysis_graph import (
    AnalysisResult,
    IngestionResult,
    LocalAnalysisWorkflow,
)


class RuntimeState(BaseModel):
    """In-memory runtime state for local/dummy mode."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    traces: InMemoryTraceRepository
    artifact_store: LocalArtifactStore
    graph: GraphBackend
    vector: VectorBackend
    approvals: ApprovalService
    audit: AuditService
    audit_archive_store: AuditArchiveWriter
    analyses: dict[str, AnalysisResult]
    ingestions: dict[str, IngestionResult]
    findings: dict[str, Finding]
    replays: dict[str, ReplayResult]
    source_sync_cursors: dict[str, SourceSyncCursorState]
    idempotency_results: dict[str, dict[str, Any]]
    registry_activations: dict[str, dict[str, Any]]
    improvement_decisions: dict[str, dict[str, Any]]
    scheduler: RunScheduler
    state_store: StateStore | None = None

    @classmethod
    def create(
        cls,
        artifact_root: Path,
        schedule_config: ScheduleConfig | None = None,
        state_store: StateStore | None = None,
        graph: GraphBackend | None = None,
        vector: VectorBackend | None = None,
        audit_policy: AuditRetentionPolicy | None = None,
        audit_archive_store: AuditArchiveWriter | None = None,
        scheduler_lease_manager: SchedulerLeaseManager | None = None,
    ) -> "RuntimeState":
        """Create a local runtime state."""
        runtime = cls(
            traces=InMemoryTraceRepository(),
            artifact_store=LocalArtifactStore(artifact_root),
            graph=graph or MemoryGraphBackend(),
            vector=vector or MemoryVectorBackend(),
            approvals=ApprovalService(),
            audit=AuditService(audit_policy),
            audit_archive_store=audit_archive_store
            or LocalAuditArchiveStore(artifact_root / "audit_archives"),
            analyses={},
            ingestions={},
            findings={},
            replays={},
            source_sync_cursors={},
            idempotency_results={},
            registry_activations={},
            improvement_decisions={},
            scheduler=RunScheduler(
                schedule_config,
                lease_manager=scheduler_lease_manager,
            ),
            state_store=state_store,
        )
        runtime.restore_from_state_store()
        return runtime

    def workflow(self) -> LocalAnalysisWorkflow:
        """Create a workflow bound to this runtime state."""
        return LocalAnalysisWorkflow(
            traces=self.traces,
            artifact_store=self.artifact_store,
            graph=self.graph,
            vector=self.vector,
            approvals=self.approvals,
        )

    def run_analysis(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        triggered_by: str = "local",
        trigger_source: TriggerSource = "manual",
    ) -> AnalysisResult:
        """Run analysis and store the result."""
        self._record_run_started(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
            run_type="analysis",
            triggered_by=triggered_by,
            trigger_source=trigger_source,
        )
        try:
            result = self.workflow().run(
                run_id=run_id,
                project_key=project_key,
                scenario=scenario,
                triggered_by=triggered_by,
                trigger_source=trigger_source,
            )
        except Exception as exc:
            self._record_run_failed(
                run_id=run_id,
                project_key=project_key,
                scenario=scenario,
                run_type="analysis",
                triggered_by=triggered_by,
                trigger_source=trigger_source,
                exc=exc,
            )
            raise
        self.analyses[run_id] = result
        self.source_sync_cursors[result.source_cursor.cursor_id] = result.source_cursor
        for finding in result.findings:
            self.findings[finding.finding_id] = finding
        self.audit.record(
            action="run_completed",
            actor_id="local",
            actor_role="system",
            project_key=project_key,
            target_type="run",
            target_id=run_id,
            metadata={
                "scenario": scenario,
                "nodes": len(result.nodes),
                "candidate_edges": len(result.candidate_edges),
                "findings": len(result.findings),
                "approvals": len(result.approvals),
            },
        )
        self.persist_analysis_result(result)
        return result

    def run_ingestion(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        triggered_by: str = "local",
        trigger_source: TriggerSource = "manual",
    ) -> IngestionResult:
        """Run deterministic ingestion and store the result."""
        self._record_run_started(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
            run_type="ingestion",
            triggered_by=triggered_by,
            trigger_source=trigger_source,
        )
        try:
            result = self.workflow().ingest(
                run_id=run_id,
                project_key=project_key,
                scenario=scenario,
                triggered_by=triggered_by,
                trigger_source=trigger_source,
            )
        except Exception as exc:
            self._record_run_failed(
                run_id=run_id,
                project_key=project_key,
                scenario=scenario,
                run_type="ingestion",
                triggered_by=triggered_by,
                trigger_source=trigger_source,
                exc=exc,
            )
            raise
        self.ingestions[run_id] = result
        self.source_sync_cursors[result.source_cursor.cursor_id] = result.source_cursor
        self.audit.record(
            action="run_completed",
            actor_id="local",
            actor_role="system",
            project_key=project_key,
            target_type="run",
            target_id=run_id,
            metadata={
                "scenario": scenario,
                "run_type": "ingestion",
                "artifacts": len(result.artifacts),
                "chunks": len(result.chunks),
            },
        )
        self.persist_ingestion_result(result)
        return result

    def _record_run_started(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        run_type: str,
        triggered_by: str,
        trigger_source: TriggerSource,
    ) -> None:
        """Record the start boundary for a runtime run."""
        event = self.audit.record(
            action="run_started",
            actor_id=triggered_by,
            actor_role=_run_actor_role(trigger_source),
            project_key=project_key,
            target_type="run",
            target_id=run_id,
            metadata={
                "scenario": scenario,
                "run_type": run_type,
                "trigger_source": trigger_source,
            },
        )
        self._persist_audit_event(event)

    def _record_run_failed(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        run_type: str,
        triggered_by: str,
        trigger_source: TriggerSource,
        exc: Exception,
    ) -> None:
        """Record failed run state and audit evidence before re-raising."""
        failure_code = type(exc).__name__
        failure_message = str(exc)
        if run_id in self.traces.runs:
            self.traces.complete_run(
                run_id,
                status="failed",
                failure_code=failure_code,
                failure_message=failure_message,
            )
        self.audit.record(
            action="run_completed",
            actor_id=triggered_by,
            actor_role=_run_actor_role(trigger_source),
            project_key=project_key,
            target_type="run",
            target_id=run_id,
            outcome="failed",
            reason_code=failure_code,
            metadata={
                "scenario": scenario,
                "run_type": run_type,
                "trigger_source": trigger_source,
                "failure_message": failure_message,
            },
        )
        self.persist_runtime_failure(run_id=run_id, project_key=project_key)

    def persist_ingestion_result(self, result: IngestionResult) -> None:
        """Persist completed ingestion outputs into the configured state store."""
        if self.state_store is None:
            return
        project_key = result.run.project_key
        self.state_store.upsert(
            collection="agent_runs",
            entity_id=result.run.run_id,
            project_key=project_key,
            payload=result.run,
        )
        for step in result.steps:
            self.state_store.upsert(
                collection="agent_step_traces",
                entity_id=step.step_id,
                project_key=project_key,
                payload=step,
            )
        for artifact in result.artifacts:
            self.state_store.upsert(
                collection="source_artifacts",
                entity_id=artifact.artifact_id,
                project_key=project_key,
                payload=artifact,
            )
        for chunk in result.chunks:
            self.state_store.upsert(
                collection="artifact_chunks",
                entity_id=chunk.chunk_id,
                project_key=project_key,
                payload=chunk,
            )
        self.state_store.upsert(
            collection="source_sync_cursors",
            entity_id=result.source_cursor.cursor_id,
            project_key=project_key,
            payload=result.source_cursor,
        )
        self.persist_approval_state()

    def persist_analysis_result(self, result: AnalysisResult) -> None:
        """Persist a completed local analysis into the configured state store."""
        if self.state_store is None:
            return
        project_key = result.run.project_key
        self.state_store.upsert(
            collection="agent_runs",
            entity_id=result.run.run_id,
            project_key=project_key,
            payload=result.run,
        )
        for step in result.steps:
            self.state_store.upsert(
                collection="agent_step_traces",
                entity_id=step.step_id,
                project_key=project_key,
                payload=step,
            )
        for llm_call in self.traces.llm_calls.values():
            if llm_call.run_id != result.run.run_id:
                continue
            self.state_store.upsert(
                collection="llm_call_traces",
                entity_id=llm_call.llm_call_id,
                project_key=project_key,
                payload=llm_call,
            )
        for artifact in result.artifacts:
            self.state_store.upsert(
                collection="source_artifacts",
                entity_id=artifact.artifact_id,
                project_key=project_key,
                payload=artifact,
            )
        for chunk in result.chunks:
            self.state_store.upsert(
                collection="artifact_chunks",
                entity_id=chunk.chunk_id,
                project_key=project_key,
                payload=chunk,
            )
        self.state_store.upsert(
            collection="source_sync_cursors",
            entity_id=result.source_cursor.cursor_id,
            project_key=project_key,
            payload=result.source_cursor,
        )
        for node in result.nodes:
            self.state_store.upsert(
                collection="graph_nodes",
                entity_id=node.node_id,
                project_key=project_key,
                payload=node,
            )
        for edge in result.candidate_edges:
            self.state_store.upsert(
                collection="candidate_edges",
                entity_id=edge.edge_id,
                project_key=project_key,
                payload=edge,
            )
        for finding in result.findings:
            self.state_store.upsert(
                collection="findings",
                entity_id=finding.finding_id,
                project_key=project_key,
                payload=finding,
            )
        self.persist_approval_state()

    def persist_runtime_failure(self, *, run_id: str, project_key: str) -> None:
        """Persist failed run metadata and audit events for post-mortem debugging."""
        if self.state_store is None:
            return
        run = self.traces.runs.get(run_id)
        if run is not None:
            self.state_store.upsert(
                collection="agent_runs",
                entity_id=run.run_id,
                project_key=project_key,
                payload=run,
            )
        for step in self.traces.list_steps(run_id):
            self.state_store.upsert(
                collection="agent_step_traces",
                entity_id=step.step_id,
                project_key=project_key,
                payload=step,
            )
        for event in self.audit.events.values():
            if event.target_type == "run" and event.target_id == run_id:
                self._persist_audit_event(event)

    def _persist_audit_event(self, event: AuditEvent) -> None:
        """Persist a single audit event when a state store is configured."""
        if self.state_store is None:
            return
        self.state_store.upsert(
            collection="audit_events",
            entity_id=event.audit_id,
            project_key=event.project_key,
            payload=event,
        )

    def persist_approval_state(self) -> None:
        """Persist approval queue, graph deltas, feedback, and approved edges."""
        if self.state_store is None:
            return
        for approval in self.approvals.items.values():
            self.state_store.upsert(
                collection="approval_items",
                entity_id=approval.approval_id,
                project_key=approval.project_key,
                payload=approval,
            )
        for delta in self.approvals.deltas.values():
            self.state_store.upsert(
                collection="graph_deltas",
                entity_id=delta.delta_id,
                project_key=delta.project_key,
                payload=delta,
            )
        for feedback in self.approvals.feedback:
            self.state_store.upsert(
                collection="feedback_events",
                entity_id=feedback.feedback_id,
                payload=feedback,
            )
        for event in self.audit.events.values():
            self.state_store.upsert(
                collection="audit_events",
                entity_id=event.audit_id,
                project_key=event.project_key,
                payload=event,
            )
        for edge in self.graph.edges.values():
            project_key = self.graph.nodes[edge.source_node_id].project_key
            self.state_store.upsert(
                collection="graph_edges",
                entity_id=edge.edge_id,
                project_key=project_key,
                payload=edge,
            )

    def persist_finding(self, finding: Finding, project_key: str | None) -> None:
        """Persist one finding status/body update."""
        self.findings[finding.finding_id] = finding
        for run_id, analysis in list(self.analyses.items()):
            updated_findings = [
                finding if item.finding_id == finding.finding_id else item
                for item in analysis.findings
            ]
            self.analyses[run_id] = analysis.model_copy(update={"findings": updated_findings})
        if self.state_store is None:
            return
        self.state_store.upsert(
            collection="findings",
            entity_id=finding.finding_id,
            project_key=project_key,
            payload=finding,
        )

    def persist_replay_result(self, result: ReplayResult) -> None:
        """Persist replay metadata and diff for restart-safe debug lookup."""
        if self.state_store is None:
            return
        source_run = self.traces.runs.get(result.source_run_id)
        self.state_store.upsert(
            collection="replay_results",
            entity_id=result.replay_run_id,
            project_key=source_run.project_key if source_run is not None else None,
            payload=result,
        )

    def persist_replay_analysis_trace(self, result: AnalysisResult) -> None:
        """Persist replay run traces without mutating operational graph state."""
        if self.state_store is None:
            return
        project_key = result.run.project_key
        self.state_store.upsert(
            collection="agent_runs",
            entity_id=result.run.run_id,
            project_key=project_key,
            payload=result.run,
        )
        for step in result.steps:
            self.state_store.upsert(
                collection="agent_step_traces",
                entity_id=step.step_id,
                project_key=project_key,
                payload=step,
            )
        for llm_call in self.traces.llm_calls.values():
            if llm_call.run_id != result.run.run_id:
                continue
            self.state_store.upsert(
                collection="llm_call_traces",
                entity_id=llm_call.llm_call_id,
                project_key=project_key,
                payload=llm_call,
            )
        for artifact in result.artifacts:
            self.state_store.upsert(
                collection="source_artifacts",
                entity_id=artifact.artifact_id,
                project_key=project_key,
                payload=artifact,
            )
        for chunk in result.chunks:
            self.state_store.upsert(
                collection="artifact_chunks",
                entity_id=chunk.chunk_id,
                project_key=project_key,
                payload=chunk,
            )

    def record_idempotency_result(
        self,
        *,
        record_id: str,
        idempotency_key: str,
        command: str,
        project_key: str | None,
        request_hash: str,
        response: dict[str, Any],
    ) -> None:
        """Record a completed command response for idempotent API retry."""
        record = {
            "record_id": record_id,
            "idempotency_key": idempotency_key,
            "command": command,
            "project_key": project_key,
            "request_hash": request_hash,
            "response": response,
        }
        self.idempotency_results[record_id] = record
        if self.state_store is None:
            return
        self.state_store.upsert(
            collection="idempotency_results",
            entity_id=record_id,
            project_key=project_key,
            payload=record,
        )

    def record_registry_activation(
        self,
        *,
        activation_id: str,
        activation: dict[str, Any],
    ) -> None:
        """Record a reviewed model/prompt registry activation decision."""
        self.registry_activations[activation_id] = activation
        if self.state_store is None:
            return
        self.state_store.upsert(
            collection="registry_activations",
            entity_id=activation_id,
            project_key=None,
            payload=activation,
        )

    def record_improvement_decision(
        self,
        *,
        candidate_id: str,
        decision: dict[str, Any],
    ) -> None:
        """Record a controlled improvement promotion or rollback decision."""
        self.improvement_decisions[candidate_id] = decision
        if self.state_store is None:
            return
        self.state_store.upsert(
            collection="improvement_decisions",
            entity_id=candidate_id,
            project_key=None,
            payload=decision,
        )

    def archive_and_prune_audit(self) -> dict[str, object]:
        """Archive/prune audit events and mirror pruned rows into the state store."""
        result = self.audit.archive_and_prune(archive_writer=self.audit_archive_store)
        if self.state_store is not None:
            for audit_id in result.get("pruned_audit_ids", []):
                if isinstance(audit_id, str):
                    self.state_store.delete("audit_events", audit_id)
        return result

    def restore_from_state_store(self) -> None:
        """Hydrate runtime caches from the configured state store after restart."""
        if self.state_store is None:
            return
        for payload in self.state_store.list("agent_runs"):
            run = AgentRun.model_validate(payload)
            self.traces.runs[run.run_id] = run
        for payload in self.state_store.list("agent_step_traces"):
            step = AgentStepTrace.model_validate(payload)
            self.traces.steps[step.step_id] = step
        for payload in self.state_store.list("llm_call_traces"):
            llm_call = LLMCallTrace.model_validate(payload)
            self.traces.llm_calls[llm_call.llm_call_id] = llm_call
        for payload in self.state_store.list("replay_results"):
            replay = ReplayResult.model_validate(payload)
            self.replays[replay.replay_run_id] = replay
        for payload in self.state_store.list("source_sync_cursors"):
            cursor = SourceSyncCursorState.model_validate(payload)
            self.source_sync_cursors[cursor.cursor_id] = cursor
        for payload in self.state_store.list("findings"):
            finding = Finding.model_validate(payload)
            self.findings[finding.finding_id] = finding
        for payload in self.state_store.list("idempotency_results"):
            record_id = payload.get("record_id")
            if isinstance(record_id, str):
                self.idempotency_results[record_id] = payload
        for payload in self.state_store.list("registry_activations"):
            activation_id = payload.get("activation_id")
            if isinstance(activation_id, str):
                self.registry_activations[activation_id] = payload
        for payload in self.state_store.list("improvement_decisions"):
            candidate_id = payload.get("candidate_id")
            if isinstance(candidate_id, str):
                self.improvement_decisions[candidate_id] = payload
        for payload in self.state_store.list("approval_items"):
            approval = ApprovalItem.model_validate(payload)
            self.approvals.items[approval.approval_id] = approval
        for payload in self.state_store.list("graph_deltas"):
            delta = GraphDelta.model_validate(payload)
            self.approvals.deltas[delta.delta_id] = delta
        self.approvals.feedback = [
            FeedbackEvent.model_validate(payload)
            for payload in self.state_store.list("feedback_events")
        ]
        for payload in self.state_store.list("audit_events"):
            event = AuditEvent.model_validate(payload)
            self.audit.events[event.audit_id] = event
        nodes = [
            OntologyNode.model_validate(payload)
            for payload in self.state_store.list("graph_nodes")
        ]
        if nodes:
            self.graph.stage_baseline_nodes(nodes)
        for payload in self.state_store.list("graph_edges"):
            edge = TraceabilityEdge.model_validate(payload)
            self.graph.edges[edge.edge_id] = edge


def _run_actor_role(trigger_source: TriggerSource) -> str:
    if trigger_source in {"schedule", "system"}:
        return "system"
    return "developer"
