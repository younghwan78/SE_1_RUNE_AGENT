"""Runtime state for local API execution."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.scheduler.service import RunScheduler
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
    scheduler: RunScheduler

    @classmethod
    def create(
        cls,
        artifact_root: Path,
        schedule_config: ScheduleConfig | None = None,
    ) -> "RuntimeState":
        """Create a local runtime state."""
        return cls(
            traces=InMemoryTraceRepository(),
            artifact_store=LocalArtifactStore(artifact_root),
            graph=MemoryGraphBackend(),
            vector=MemoryVectorBackend(),
            approvals=ApprovalService(),
            analyses={},
            scheduler=RunScheduler(schedule_config),
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
        return result
