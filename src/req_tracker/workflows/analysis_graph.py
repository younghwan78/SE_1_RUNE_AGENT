"""Dummy/local end-to-end analysis workflow."""

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.adapters.base import (
    SourceAdapter,
    SourceFetchResult,
    SourceScope,
    SourceSyncCursorState,
    SyncCursor,
    source_sync_cursor_id,
)
from req_tracker.adapters.dummy.adapter import DummySourceAdapter
from req_tracker.approvals.models import ApprovalItem
from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.hash import stable_hash
from req_tracker.debug.models import AgentRun, AgentStepTrace, RunType, TriggerSource
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.evidence.spans import build_artifact_evidence
from req_tracker.findings.rules import analyze_findings
from req_tracker.graph.base import GraphBackend
from req_tracker.ingestion.chunking import chunk_artifact
from req_tracker.ingestion.masking import mask_text
from req_tracker.ingestion.normalization import normalize_raw_artifact
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.dummy_provider import DummyModelProvider
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    PromptVersion,
    StructuredValidationResult,
)
from req_tracker.ontology.models import (
    ArtifactChunk,
    Finding,
    OntologyNode,
    SourceArtifact,
    TraceabilityEdge,
)
from req_tracker.reasoning.extraction import extract_node
from req_tracker.reasoning.linking import link_edges
from req_tracker.vector.base import VectorBackend


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
    source_cursor: SourceSyncCursorState


class IngestionResult(BaseModel):
    """Source fetch, normalization, masking, and chunking result."""

    model_config = ConfigDict(extra="forbid")

    run: AgentRun
    steps: list[AgentStepTrace]
    artifacts: list[SourceArtifact]
    chunks: list[ArtifactChunk]
    source_cursor: SourceSyncCursorState
    source_warnings: list[str] = Field(default_factory=list)


class EdgeReasoningOutput(BaseModel):
    """Structured output produced by the local dummy LLM reasoning stage."""

    model_config = ConfigDict(extra="forbid")

    candidate_edge_count: int = Field(ge=0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    counter_evidence_refs: list[str] = Field(default_factory=list)


class LocalAnalysisWorkflow:
    """Local workflow using dummy source and in-memory backends."""

    def __init__(
        self,
        *,
        traces: InMemoryTraceRepository,
        artifact_store: LocalArtifactStore,
        graph: GraphBackend,
        vector: VectorBackend,
        approvals: ApprovalService,
        source_adapter: SourceAdapter | None = None,
    ) -> None:
        self.traces = traces
        self.artifact_store = artifact_store
        self.graph = graph
        self.vector = vector
        self.approvals = approvals
        self.adapter = source_adapter or DummySourceAdapter()

    def ingest(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str = "RUNE_CAM_ALPHA",
        triggered_by: str = "local",
        trigger_source: TriggerSource = "manual",
    ) -> IngestionResult:
        """Run deterministic source ingestion stages only."""
        self.traces.create_run(
            run_id=run_id,
            run_type="ingestion",
            project_key=project_key,
            triggered_by=triggered_by,
            trigger_source=trigger_source,
        )
        self.traces.mark_run_running(run_id)
        fetch, artifacts, chunks, source_cursor = self._run_ingestion_stages(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
        )
        completed = self.traces.complete_run(run_id)
        return IngestionResult(
            run=completed,
            steps=self.traces.list_steps(run_id),
            artifacts=artifacts,
            chunks=chunks,
            source_cursor=source_cursor,
            source_warnings=fetch.source_warnings,
        )

    def run(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str = "RUNE_CAM_ALPHA",
        triggered_by: str = "local",
        trigger_source: TriggerSource = "manual",
        run_type: RunType = "analysis",
    ) -> AnalysisResult:
        """Run source fetch through approval staging."""
        self.traces.create_run(
            run_id=run_id,
            run_type=run_type,
            project_key=project_key,
            triggered_by=triggered_by,
            trigger_source=trigger_source,
        )
        self.traces.mark_run_running(run_id)
        fetch, artifacts, chunks, source_cursor = self._run_ingestion_stages(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
        )

        evidence_by_external = {
            raw.external_id: build_artifact_evidence(artifact.artifact_id, raw)
            for raw, artifact in zip(fetch.artifacts, artifacts, strict=True)
        }

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
            retrieval_context_ref="chunks",
            validation_status="passed",
            validation_result={
                "node_count": len(nodes),
                "evidence_required": True,
                "evidence_attached": all(node.evidence for node in nodes),
            },
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
            retrieval_context_ref="evidence_by_external",
            validation_status="passed",
            validation_result={
                "edge_count": len(edges),
                "evidence_attached": all(edge.evidence for edge in edges),
            },
        )

        llm_step = self.traces.start_step(
            step_id=f"step_{run_id}_llm_reason_edges",
            run_id=run_id,
            stage_name="llm_assisted_reasoning",
            input_payload={
                "candidate_edge_ids": [edge.edge_id for edge in edges],
                "model_profile_id": "dummy-local",
                "prompt_version_id": "pv_edge_linking_v1",
            },
            retrieval_context_ref="candidate_edges",
        )
        llm_reasoning, llm_validation = self._run_llm_edge_reasoning(
            run_id=run_id,
            step_id=llm_step.step_id,
            nodes=nodes,
            edges=edges,
        )
        self.traces.finish_step(
            step_id=llm_step.step_id,
            output_payload=llm_reasoning.model_dump(mode="json"),
            validation_status=llm_validation.status,
            validation_result=llm_validation.model_dump(mode="json"),
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
            validation_status="passed",
            validation_result={"finding_count": len(findings)},
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
            retrieval_context_ref="candidate_edges",
            validation_status="passed",
            validation_result={
                "approval_count": len(approvals),
                "graph_delta_preview_created": bool(approvals),
            },
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
            source_cursor=source_cursor,
        )

    def _run_ingestion_stages(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
    ) -> tuple[
        SourceFetchResult,
        list[SourceArtifact],
        list[ArtifactChunk],
        SourceSyncCursorState,
    ]:
        """Run shared deterministic ingestion stages for ingest and analyze."""
        fetch_step = self.traces.start_step(
            step_id=f"step_{run_id}_source_fetch",
            run_id=run_id,
            stage_name="source_fetch",
            input_payload={"scenario": scenario},
        )
        fetch = self._fetch_all(project_key=project_key, scenario=scenario)
        fetch_ref = self.artifact_store.write_json(run_id, "source_fetch", fetch)
        self.traces.finish_step(
            step_id=fetch_step.step_id,
            output_payload=fetch.model_dump(mode="json"),
            output_ref=fetch_ref.artifact_ref,
            validation_status="passed" if not fetch.partial_failure else "failed",
            validation_result={
                "artifact_count": len(fetch.artifacts),
                "page_count": fetch.page_count,
                "source_sync_cursor_id": source_sync_cursor_id(
                    source_type=self.adapter.source_type,
                    project_key=project_key,
                    scenario=scenario,
                ),
                "completed_cursor": (
                    fetch.completed_cursor.model_dump(mode="json")
                    if fetch.completed_cursor is not None
                    else None
                ),
                "next_cursor": (
                    fetch.next_cursor.model_dump(mode="json")
                    if fetch.next_cursor is not None
                    else None
                ),
                "source_warnings": fetch.source_warnings,
                "partial_failure": fetch.partial_failure,
            },
        )
        source_cursor = self._source_sync_cursor_state(
            run_id=run_id,
            project_key=project_key,
            scenario=scenario,
            fetch=fetch,
        )

        norm_step = self.traces.start_step(
            step_id=f"step_{run_id}_normalize",
            run_id=run_id,
            stage_name="normalize",
            input_payload=fetch.model_dump(mode="json"),
        )
        artifacts = [normalize_raw_artifact(raw) for raw in fetch.artifacts]
        self._record_input_snapshots(
            run_id=run_id,
            input_snapshot_ids=[artifact.artifact_id for artifact in artifacts],
        )
        evidence_by_external = {
            raw.external_id: build_artifact_evidence(artifact.artifact_id, raw)
            for raw, artifact in zip(fetch.artifacts, artifacts, strict=True)
        }
        norm_ref = self.artifact_store.write_json(run_id, "normalize", artifacts)
        self.traces.finish_step(
            step_id=norm_step.step_id,
            output_payload=[artifact.model_dump(mode="json") for artifact in artifacts],
            output_ref=norm_ref.artifact_ref,
            retrieval_context_ref=fetch_ref.artifact_ref,
            validation_status="passed",
            validation_result={
                "artifact_count": len(artifacts),
                "input_snapshot_ids": [artifact.artifact_id for artifact in artifacts],
            },
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
            retrieval_context_ref=norm_ref.artifact_ref,
            validation_status="passed",
            validation_result={
                "chunk_count": len(chunks),
                "masking_applied": True,
                "vector_upserted": True,
            },
        )
        return fetch, artifacts, chunks, source_cursor

    def _fetch_all(self, *, project_key: str, scenario: str) -> SourceFetchResult:
        """Fetch all source pages for a local analysis run."""
        scope = SourceScope(project_key=project_key, scenario=scenario)
        first_page = self.adapter.fetch_incremental(scope)
        artifacts = list(first_page.artifacts)
        warnings = list(first_page.source_warnings)
        partial_failure = first_page.partial_failure
        cursor = first_page.next_cursor
        page_count = 1
        while cursor is not None:
            page = self.adapter.fetch_incremental(scope, cursor)
            artifacts.extend(page.artifacts)
            warnings.extend(page.source_warnings)
            partial_failure = partial_failure or page.partial_failure
            cursor = page.next_cursor
            page_count += 1
        completed_cursor = SyncCursor(
            offset=len(artifacts),
            content_hash=stable_hash(artifacts),
        )
        return SourceFetchResult(
            artifacts=artifacts,
            next_cursor=None,
            initial_cursor=None,
            completed_cursor=completed_cursor,
            page_count=page_count,
            source_warnings=warnings,
            partial_failure=partial_failure,
        )

    def _source_sync_cursor_state(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        fetch: SourceFetchResult,
    ) -> SourceSyncCursorState:
        """Create the persisted source cursor snapshot for this fetch."""
        return SourceSyncCursorState(
            cursor_id=source_sync_cursor_id(
                source_type=self.adapter.source_type,
                project_key=project_key,
                scenario=scenario,
            ),
            source_type=self.adapter.source_type,
            project_key=project_key,
            scenario=scenario,
            run_id=run_id,
            initial_cursor=fetch.initial_cursor,
            completed_cursor=fetch.completed_cursor,
            next_cursor=fetch.next_cursor,
            artifact_count=len(fetch.artifacts),
            page_count=fetch.page_count,
            content_hash=stable_hash(fetch.artifacts),
            source_warnings=fetch.source_warnings,
            partial_failure=fetch.partial_failure,
        )

    def _run_llm_edge_reasoning(
        self,
        *,
        run_id: str,
        step_id: str,
        nodes: list[OntologyNode],
        edges: list[TraceabilityEdge],
    ) -> tuple[EdgeReasoningOutput, StructuredValidationResult]:
        """Run a deterministic dummy model-gateway call for traceable LLM reasoning."""
        profile = ModelProfile(
            model_profile_id="dummy-local",
            provider="dummy",
            model_name="deterministic-dummy",
            endpoint_alias="local-fixture",
            allowed_data_classes=[
                "public_internal",
                "restricted",
                "confidential",
                "no_external_llm",
            ],
            supports_json_schema=True,
            supports_tool_calling=False,
            max_context_tokens=8192,
            default_temperature=0.0,
            timeout_seconds=30,
        )
        prompt = PromptVersion(
            prompt_version_id="pv_edge_linking_v1",
            task_name="edge_linking",
            template="Propose MBSE traceability edges from approved source evidence.",
            schema_version_ref="ontology.v1.edge_linking",
            retrieval_policy_id="ret_dummy_v1",
            created_by="system",
            status="active",
        )
        provider = DummyModelProvider(
            fixtures={
                "edge_reasoning": {
                    "candidate_edge_count": len(edges),
                    "confidence_score": 0.82 if edges else 0.0,
                    "rationale": (
                        "Deterministic dummy LLM reviewed candidate edges "
                        "behind the model gateway."
                    ),
                    "counter_evidence_refs": [],
                }
            }
        )
        client = ModelGatewayClient(
            provider=provider,
            profile=profile,
            prompt=prompt,
            trace_repo=self.traces,
            artifact_store=self.artifact_store,
        )
        request = ModelRequest(
            model_profile_id=profile.model_profile_id,
            prompt_version_id=prompt.prompt_version_id,
            payload={
                "fixture_name": "edge_reasoning",
                "node_ids": [node.node_id for node in nodes],
                "candidate_edge_ids": [edge.edge_id for edge in edges],
            },
            data_classification="restricted",
            masking_applied=True,
            access_checked=True,
        )
        _response, parsed, validation = client.complete(
            run_id=run_id,
            step_id=step_id,
            request=request,
            response_model=EdgeReasoningOutput,
        )
        self._record_model_metadata(
            run_id=run_id,
            model_profile_id=profile.model_profile_id,
            prompt_version_id=prompt.prompt_version_id,
        )
        if parsed is None:
            raise RuntimeError(f"dummy LLM edge reasoning failed validation: {validation}")
        return parsed, validation

    def _record_model_metadata(
        self,
        *,
        run_id: str,
        model_profile_id: str,
        prompt_version_id: str,
    ) -> None:
        run = self.traces.runs[run_id]
        prompt_ids = list(dict.fromkeys([*run.prompt_version_ids, prompt_version_id]))
        self.traces.runs[run_id] = run.model_copy(
            update={
                "model_profile_id": model_profile_id,
                "prompt_version_ids": prompt_ids,
            }
        )

    def _record_input_snapshots(self, *, run_id: str, input_snapshot_ids: list[str]) -> None:
        run = self.traces.runs[run_id]
        self.traces.runs[run_id] = run.model_copy(
            update={"input_snapshot_ids": list(dict.fromkeys(input_snapshot_ids))}
        )
