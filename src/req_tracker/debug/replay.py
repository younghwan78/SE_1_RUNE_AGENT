"""Replay service for local analysis runs."""

from pydantic import BaseModel, ConfigDict

from req_tracker.debug.diff import ReplayDiffReport, diff_analysis_results
from req_tracker.workflows.analysis_graph import AnalysisResult, LocalAnalysisWorkflow


class ReplayResult(BaseModel):
    """Replay result and diff."""

    model_config = ConfigDict(extra="forbid")

    source_run_id: str
    replay_run_id: str
    replay_mode: str
    diff: ReplayDiffReport


class ReplayService:
    """Run local replay and compare outputs."""

    def __init__(
        self, workflow: LocalAnalysisWorkflow, analyses: dict[str, AnalysisResult]
    ) -> None:
        self._workflow = workflow
        self._analyses = analyses

    def replay(
        self,
        *,
        source_run_id: str,
        replay_run_id: str,
        project_key: str,
        scenario: str,
        replay_mode: str = "same_model_same_prompt",
    ) -> ReplayResult:
        """Replay an analysis run and compare with the source run."""
        before = self._analyses[source_run_id]
        after = self._workflow.run(
            run_id=replay_run_id,
            project_key=project_key,
            scenario=scenario,
            triggered_by="replay",
            trigger_source="system",
        )
        self._analyses[replay_run_id] = after
        diff = diff_analysis_results(
            source_run_id=source_run_id,
            replay_run_id=replay_run_id,
            before=before,
            after=after,
        )
        return ReplayResult(
            source_run_id=source_run_id,
            replay_run_id=replay_run_id,
            replay_mode=replay_mode,
            diff=diff,
        )
