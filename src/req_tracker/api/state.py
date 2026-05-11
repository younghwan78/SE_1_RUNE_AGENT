"""Runtime state for local API execution."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from req_tracker.approvals.service import ApprovalService
from req_tracker.audit.models import AuditRetentionPolicy
from req_tracker.audit.service import AuditService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.graph.base import GraphBackend
from req_tracker.graph.memory_backend import MemoryGraphBackend
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
    analyses: dict[str, AnalysisResult]
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
    ) -> "RuntimeState":
        """Create a local runtime state."""
        return cls(
            traces=InMemoryTraceRepository(),
            artifact_store=LocalArtifactStore(artifact_root),
            graph=graph or MemoryGraphBackend(),
            vector=vector or MemoryVectorBackend(),
            approvals=ApprovalService(),
            audit=AuditService(audit_policy),
            analyses={},
            scheduler=RunScheduler(schedule_config),
            state_store=state_store,
        )

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
