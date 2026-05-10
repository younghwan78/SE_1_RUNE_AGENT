"""Object-level replay diff helpers."""

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.workflows.analysis_graph import AnalysisResult


class ObjectDiff(BaseModel):
    """Added, removed, and changed ids for one object type."""

    model_config = ConfigDict(extra="forbid")

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)


class ReplayDiffReport(BaseModel):
    """Replay diff summary."""

    model_config = ConfigDict(extra="forbid")

    source_run_id: str
    replay_run_id: str
    node_diff: ObjectDiff
    edge_diff: ObjectDiff
    finding_diff: ObjectDiff
    approval_diff: ObjectDiff


def diff_analysis_results(
    *,
    source_run_id: str,
    replay_run_id: str,
    before: AnalysisResult,
    after: AnalysisResult,
) -> ReplayDiffReport:
    """Compare two analysis results by stable ids and content."""
    return ReplayDiffReport(
        source_run_id=source_run_id,
        replay_run_id=replay_run_id,
        node_diff=_diff_objects(
            {node.node_id: node.model_dump(mode="json") for node in before.nodes},
            {node.node_id: node.model_dump(mode="json") for node in after.nodes},
        ),
        edge_diff=_diff_objects(
            {edge.edge_id: edge.model_dump(mode="json") for edge in before.candidate_edges},
            {edge.edge_id: edge.model_dump(mode="json") for edge in after.candidate_edges},
        ),
        finding_diff=_diff_objects(
            {finding.finding_id: finding.model_dump(mode="json") for finding in before.findings},
            {finding.finding_id: finding.model_dump(mode="json") for finding in after.findings},
        ),
        approval_diff=_diff_objects(
            {
                approval.approval_id: approval.model_dump(mode="json")
                for approval in before.approvals
            },
            {
                approval.approval_id: approval.model_dump(mode="json")
                for approval in after.approvals
            },
        ),
    )


def _diff_objects(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
) -> ObjectDiff:
    before_ids = set(before)
    after_ids = set(after)
    shared = before_ids & after_ids
    return ObjectDiff(
        added=sorted(after_ids - before_ids),
        removed=sorted(before_ids - after_ids),
        changed=sorted(item_id for item_id in shared if before[item_id] != after[item_id]),
    )
