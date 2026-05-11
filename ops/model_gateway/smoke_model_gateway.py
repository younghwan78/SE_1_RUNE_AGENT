"""Local HTTP model gateway smoke harness.

The harness starts a disposable JSON-over-HTTP model gateway on localhost and
uses the production `HttpJsonModelProvider` plus `ModelGatewayClient` against it.
It validates a live-shaped fallback path without requiring a real company model
endpoint.
"""

import argparse
import json
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.http_provider import HttpJsonModelProvider
from req_tracker.model_gateway.models import ModelProfile, ModelRequest, PromptVersion


class SmokeNodeOutput(BaseModel):
    """Expected structured response for the smoke call."""

    node_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class _GatewayHandler(BaseHTTPRequestHandler):
    """Small deterministic model gateway for localhost smoke validation."""

    server_version = "RuneMockModelGateway/1.0"

    def do_POST(self) -> None:  # noqa: N802
        if self.path.endswith("/fail"):
            self._send_json({"error": "forced primary failure"}, status=503)
            return
        if not self.path.endswith("/complete"):
            self._send_json({"error": "not found"}, status=404)
            return
        length = int(self.headers.get("content-length", "0"))
        raw_body = self.rfile.read(length)
        try:
            request_payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=400)
            return
        if not isinstance(request_payload, dict):
            self._send_json({"error": "request must be object"}, status=400)
            return
        inner_payload = request_payload.get("payload", {})
        if not isinstance(inner_payload, dict):
            inner_payload = {}
        if inner_payload.get("simulate") == "invalid_output":
            self._send_json({"output": {"unexpected": True}})
            return
        self._send_json(
            {
                "output": {
                    "node_id": str(inner_payload.get("node_id", "SMOKE-NODE-001")),
                    "confidence_score": float(inner_payload.get("confidence_score", 0.91)),
                },
                "usage": {
                    "input_tokens": 18,
                    "output_tokens": 6,
                    "cost_usd": 0.0009,
                },
            }
        )

    def log_message(self, _format: str, *_args: object) -> None:
        """Suppress default HTTP request logs for stable smoke output."""

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def mock_model_gateway(port: int = 0) -> Iterator[str]:
    """Run a disposable local model gateway and yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", port), _GatewayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, bound_port = server.server_address
    try:
        yield f"http://{host}:{bound_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_model_gateway_smoke(*, port: int = 0, artifact_root: Path | None = None) -> dict[str, Any]:
    """Run the HTTP provider fallback smoke and return a structured summary."""
    with mock_model_gateway(port) as base_url:
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_repo = InMemoryTraceRepository()
            store_root = artifact_root or Path(temp_dir) / "artifacts"
            artifact_store = LocalArtifactStore(store_root)
            client = ModelGatewayClient(
                provider=HttpJsonModelProvider(endpoint_url=f"{base_url}/v1/fail"),
                profile=_profile("smoke-primary"),
                prompt=_prompt("pv_smoke_primary"),
                trace_repo=trace_repo,
                artifact_store=artifact_store,
                fallback_provider=HttpJsonModelProvider(endpoint_url=f"{base_url}/v1/complete"),
                fallback_profile=_profile("smoke-fallback"),
                fallback_prompt=_prompt("pv_smoke_fallback"),
            )
            response, parsed, validation = client.complete(
                run_id="run_model_gateway_smoke",
                step_id="step_model_gateway_smoke",
                request=ModelRequest(
                    model_profile_id="smoke-primary",
                    prompt_version_id="pv_smoke_primary",
                    payload={"node_id": "SMOKE-NODE-001"},
                    data_classification="public_internal",
                ),
                response_model=SmokeNodeOutput,
            )
            traces = sorted(trace_repo.llm_calls.values(), key=lambda item: item.retry_count)
            trace_statuses = [trace.validation_status for trace in traces]
            return {
                "passed": validation.status == "passed" and parsed is not None,
                "base_url": base_url,
                "fallback_used": response.model_profile_id == "smoke-fallback",
                "model_profile_id": response.model_profile_id,
                "prompt_version_id": response.prompt_version_id,
                "trace_count": len(traces),
                "trace_statuses": trace_statuses,
                "input_tokens_total": sum(trace.input_tokens or 0 for trace in traces),
                "output_tokens_total": sum(trace.output_tokens or 0 for trace in traces),
                "cost_usd_total": round(sum(trace.cost_usd or 0 for trace in traces), 6),
                "raw_response_refs": [trace.raw_response_ref for trace in traces],
                "error_messages": [trace.error_message for trace in traces],
                "output": None if parsed is None else parsed.model_dump(mode="json"),
                "schema_version": "v1",
            }


def main() -> int:
    """Run the local model gateway smoke harness."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    result = run_model_gateway_smoke(port=args.port, artifact_root=args.artifact_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] and result["fallback_used"] else 1


def _profile(profile_id: str) -> ModelProfile:
    return ModelProfile(
        model_profile_id=profile_id,
        provider="internal",
        model_name="rune-smoke-model",
        endpoint_alias="local-smoke-gateway",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=5,
    )


def _prompt(prompt_id: str) -> PromptVersion:
    return PromptVersion(
        prompt_version_id=prompt_id,
        task_name="node_extraction",
        template="Return one node as JSON.",
        schema_version_ref="smoke_node_output.v1",
        retrieval_policy_id="ret_smoke",
        created_by="ops",
        status="active",
    )


if __name__ == "__main__":
    raise SystemExit(main())
