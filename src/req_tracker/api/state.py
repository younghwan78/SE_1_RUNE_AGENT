"""Runtime state for local API execution."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from req_tracker.approvals.models import ApprovalItem, GraphDelta
from req_tracker.approvals.service import ApprovalService
from req_tracker.audit.archive import AuditArchiveWriter, LocalAuditArchiveStore
from req_tracker.audit.models import AuditEvent, AuditRetentionPolicy
from req_tracker.audit.service import AuditService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.models import AgentRun, AgentStepTrace, LLMCallTrace
from req_tracker.debug.replay import ReplayResult
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.graph.base import GraphBackend
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.ontology.models import OntologyNode, TraceabilityEdge
from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.scheduler.service import RunScheduler
from req_tracker.storage.state_store import StateStore
from req_tracker.vector.base import VectorBackend
from req_tracker.vector.memory_backend import MemoryVectorBackend
from req_tracker.workflows.analysis_graph import AnalysisResult, LocalAnalysisWorkflow


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
    replays: dict[str, ReplayResult]
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
            replays={},
            scheduler=RunScheduler(schedule_config),
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

    def run_analysis(self, *, run_id: str, project_key: str, scenario: str) -> AnalysisResult:
        """Run analysis and store the result."""
        result = self.workflow().run(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
        )
        self.analyses[run_id] = result
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
