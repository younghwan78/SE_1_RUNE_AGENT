"""Dummy/local end-to-end analysis workflow."""

from pydantic import BaseModel, ConfigDict

from req_tracker.adapters.base import SourceScope
from req_tracker.adapters.dummy.adapter import DummySourceAdapter
from req_tracker.approvals.models import ApprovalItem
from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.models import AgentRun, AgentStepTrace
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.evidence.spans import build_artifact_evidence
from req_tracker.findings.rules import analyze_findings
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.ingestion.chunking import chunk_artifact
from req_tracker.ingestion.masking import mask_text
from req_tracker.ingestion.normalization import normalize_raw_artifact
from req_tracker.ontology.models import (
    ArtifactChunk,
    Finding,
    OntologyNode,
    SourceArtifact,
    TraceabilityEdge,
)
from req_tracker.reasoning.extraction import extract_node
from req_tracker.reasoning.linking import link_edges
from req_tracker.vector.memory_backend import MemoryVectorBackend


class AnalysisResult(BaseModel):
    """End-to-end dummy analysis result."""

    model_config = ConfigDict(extra="forbid")

    run: AgentRun
    steps: list[AgentStepTrace]
    artifacts: list[SourceArtifact]
    chunks: list[ArtifactChunk]
    nodes: list[OntologyNode]
    candidate_edges: list[TraceabilityEdge]
    findings: list[Finding]
    approvals: list[ApprovalItem]


class LocalAnalysisWorkflow:
    """Local workflow using dummy source and in-memory backends."""

    def __init__(
        self,
        *,
        traces: InMemoryTraceRepository,
        artifact_store: LocalArtifactStore,
        graph: MemoryGraphBackend,
        vector: MemoryVectorBackend,
        approvals: ApprovalService,
    ) -> None:
        self.traces = traces
        self.artifact_store = artifact_store
        self.graph = graph
        self.vector = vector
        self.approvals = approvals
        self.adapter = DummySourceAdapter()

    def run(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str = "RUNE_CAM_ALPHA",
    ) -> AnalysisResult:
        """Run source fetch through approval staging."""
        self.traces.create_run(
            run_id=run_id,
            run_type="analysis",
            project_key=project_key,
            triggered_by="local",
            trigger_source="manual",
        )
        self.traces.mark_run_running(run_id)

        fetch_step = self.traces.start_step(
            step_id=f"step_{run_id}_source_fetch",
            run_id=run_id,
            stage_name="source_fetch",
            input_payload={"scenario": scenario},
        )
        fetch = self.adapter.fetch_incremental(
            SourceScope(project_key=project_key, scenario=scenario)
        )
        fetch_ref = self.artifact_store.write_json(run_id, "source_fetch", fetch)
        self.traces.finish_step(
            step_id=fetch_step.step_id,
            output_payload=fetch.model_dump(mode="json"),
            output_ref=fetch_ref.artifact_ref,
        )

        norm_step = self.traces.start_step(
            step_id=f"step_{run_id}_normalize",
            run_id=run_id,
            stage_name="normalize",
            input_payload=fetch.model_dump(mode="json"),
        )
        artifacts = [normalize_raw_artifact(raw) for raw in fetch.artifacts]
        evidence_by_external = {
            raw.external_id: build_artifact_evidence(artifact.artifact_id, raw)
            for raw, artifact in zip(fetch.artifacts, artifacts, strict=True)
        }
        norm_ref = self.artifact_store.write_json(run_id, "normalize", artifacts)
        self.traces.finish_step(
            step_id=norm_step.step_id,
            output_payload=[artifact.model_dump(mode="json") for artifact in artifacts],
            output_ref=norm_ref.artifact_ref,
        )

        chunk_step = self.traces.start_step(
            step_id=f"step_{run_id}_mask_chunk",
            run_id=run_id,
            stage_name="mask_chunk",
            input_payload=[artifact.artifact_id for artifact in artifacts],
        )
        chunks: list[ArtifactChunk] = []
        for raw, artifact in zip(fetch.artifacts, artifacts, strict=True):
            masked = mask_text(raw.body_text)
            chunks.extend(
                chunk_artifact(artifact, masked.text, evidence_by_external[raw.external_id])
            )
        self.vector.upsert(chunks)
        chunk_ref = self.artifact_store.write_json(run_id, "chunks", chunks)
        self.traces.finish_step(
            step_id=chunk_step.step_id,
            output_payload=[chunk.model_dump(mode="json") for chunk in chunks],
            output_ref=chunk_ref.artifact_ref,
        )

        extract_step = self.traces.start_step(
            step_id=f"step_{run_id}_extract_nodes",
            run_id=run_id,
            stage_name="extract_nodes",
            input_payload=[chunk.chunk_id for chunk in chunks],
        )
        nodes = [
            extract_node(raw, artifact, evidence_by_external[raw.external_id])
            for raw, artifact in zip(fetch.artifacts, artifacts, strict=True)
        ]
        self.graph.stage_baseline_nodes(nodes)
        self.traces.finish_step(
            step_id=extract_step.step_id,
            output_payload=[node.model_dump(mode="json") for node in nodes],
        )

        link_step = self.traces.start_step(
            step_id=f"step_{run_id}_link_edges",
            run_id=run_id,
            stage_name="link_edges",
            input_payload=[node.node_id for node in nodes],
        )
        edges = link_edges(fetch.artifacts, nodes, evidence_by_external)
        self.traces.finish_step(
            step_id=link_step.step_id,
            output_payload=[edge.model_dump(mode="json") for edge in edges],
        )

        finding_step = self.traces.start_step(
            step_id=f"step_{run_id}_detect_findings",
            run_id=run_id,
            stage_name="detect_findings",
            input_payload={"nodes": len(nodes), "edges": len(edges)},
        )
        findings = analyze_findings(nodes, edges)
        self.traces.finish_step(
            step_id=finding_step.step_id,
            output_payload=[finding.model_dump(mode="json") for finding in findings],
        )

        approval_step = self.traces.start_step(
            step_id=f"step_{run_id}_stage_approval",
            run_id=run_id,
            stage_name="stage_approval",
            input_payload=[edge.edge_id for edge in edges],
        )
        approvals = self.approvals.stage_edges(
            project_key=project_key,
            run_id=run_id,
            step_id=approval_step.step_id,
            edges=edges,
        )
        self.traces.finish_step(
            step_id=approval_step.step_id,
            output_payload=[approval.model_dump(mode="json") for approval in approvals],
        )
        completed = self.traces.complete_run(run_id)

        return AnalysisResult(
            run=completed,
            steps=self.traces.list_steps(run_id),
            artifacts=artifacts,
            chunks=chunks,
            nodes=nodes,
            candidate_edges=edges,
            findings=findings,
            approvals=approvals,
        )

