"""Runtime state for local API execution."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.vector.memory_backend import MemoryVectorBackend
from req_tracker.workflows.analysis_graph import AnalysisResult, LocalAnalysisWorkflow


class RuntimeState(BaseModel):
    """In-memory runtime state for local/dummy mode."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    traces: InMemoryTraceRepository
    artifact_store: LocalArtifactStore
    graph: MemoryGraphBackend
    vector: MemoryVectorBackend
    approvals: ApprovalService
    analyses: dict[str, AnalysisResult]

    @classmethod
    def create(cls, artifact_root: Path) -> "RuntimeState":
        """Create a local runtime state."""
        return cls(
            traces=InMemoryTraceRepository(),
            artifact_store=LocalArtifactStore(artifact_root),
            graph=MemoryGraphBackend(),
            vector=MemoryVectorBackend(),
            approvals=ApprovalService(),
            analyses={},
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

