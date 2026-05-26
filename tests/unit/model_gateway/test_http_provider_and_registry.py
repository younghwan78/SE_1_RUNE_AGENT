"""HTTP provider and file-backed model registry tests."""

import json
from pathlib import Path
from typing import Any

import pytest

from req_tracker.config.settings import Settings
from req_tracker.model_gateway import http_provider
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.http_provider import HttpJsonModelProvider
from req_tracker.model_gateway.models import ModelProfile, ModelRequest, PromptVersion
from req_tracker.model_gateway.providers import ModelProviderError
from req_tracker.model_gateway.registry import ModelRegistry, ModelRegistryError


def test_http_json_model_provider_sends_provider_neutral_payload() -> None:
    calls: list[dict[str, Any]] = []

    def transport(
        endpoint_url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        calls.append(
            {
                "endpoint_url": endpoint_url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "output": {"node_id": "CAM-REQ-001", "confidence_score": 0.91},
            "usage": {
                "input_tokens": 123,
                "output_tokens": 45,
                "cost_usd": 0.00123,
            },
        }

    provider = HttpJsonModelProvider(
        endpoint_url="https://models.example.com/v1/complete",
        api_key="secret",
        transport=transport,
    )

    response = provider.complete(
        ModelRequest(
            model_profile_id="internal-json",
            prompt_version_id="pv_node_v1",
            payload={"text": "camera latency"},
            data_classification="public_internal",
        ),
        _profile(),
        _prompt(),
    )

    assert calls[0]["endpoint_url"] == "https://models.example.com/v1/complete"
    assert calls[0]["headers"]["authorization"] == "Bearer secret"
    assert calls[0]["headers"]["content-type"] == "application/json; charset=utf-8"
    assert calls[0]["headers"]["x-model-profile-id"] == "internal-json"
    assert calls[0]["payload"]["provider"] == "internal"
    assert calls[0]["payload"]["prompt_template"] == "Extract nodes"
    assert calls[0]["payload"]["payload"] == {"text": "camera latency"}
    assert calls[0]["timeout_seconds"] == 30
    assert response.output == {"node_id": "CAM-REQ-001", "confidence_score": 0.91}
    assert response.input_tokens == 123
    assert response.output_tokens == 45
    assert response.cost_usd == 0.00123


def test_http_json_transport_preserves_korean_text_as_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"output":{"answer":"ok"}}'

    def fake_urlopen(req: Any, timeout: int) -> FakeResponse:
        captured["data"] = req.data
        captured["content_type"] = req.get_header("Content-type")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(http_provider.request, "urlopen", fake_urlopen)

    loaded = http_provider._urllib_transport(
        "https://models.example.com/v1/complete",
        {"content-type": "application/json; charset=utf-8"},
        {"payload": {"message": "한국어 요구사항을 설명해줘"}},
        30,
    )

    raw_body = captured["data"]
    assert isinstance(raw_body, bytes)
    assert "한국어".encode() in raw_body
    assert b"\\ud55c\\uad6d\\uc5b4" not in raw_body
    assert captured["content_type"] == "application/json; charset=utf-8"
    assert captured["timeout"] == 30
    assert json.loads(raw_body.decode("utf-8"))["payload"]["message"] == (
        "한국어 요구사항을 설명해줘"
    )
    assert loaded == {"output": {"answer": "ok"}}


def test_http_json_model_provider_reads_openai_style_usage_aliases() -> None:
    provider = HttpJsonModelProvider(
        endpoint_url="https://models.example.com/v1/complete",
        transport=lambda *_args: {
            "output": {"node_id": "CAM-REQ-001"},
            "usage": {
                "prompt_tokens": "12",
                "completion_tokens": 7,
                "cost_usd": "0.0004",
            },
        },
    )

    response = provider.complete(
        ModelRequest(
            model_profile_id="internal-json",
            prompt_version_id="pv_node_v1",
            payload={},
            data_classification="public_internal",
        ),
        _profile(),
        _prompt(),
    )

    assert response.input_tokens == 12
    assert response.output_tokens == 7
    assert response.cost_usd == 0.0004


def test_http_json_model_provider_rejects_non_object_output() -> None:
    provider = HttpJsonModelProvider(
        endpoint_url="https://models.example.com/v1/complete",
        transport=lambda *_args: {"output": "not-json-object"},
    )

    with pytest.raises(ModelProviderError):
        provider.complete(
            ModelRequest(
                model_profile_id="internal-json",
                prompt_version_id="pv_node_v1",
                payload={},
                data_classification="public_internal",
            ),
            _profile(),
            _prompt(),
        )


def test_model_registry_loads_profiles_and_active_prompt(tmp_path) -> None:  # type: ignore[no-untyped-def]
    profiles_path = tmp_path / "profiles.json"
    prompts_path = tmp_path / "prompts.json"
    profiles_path.write_text(f"[{_profile().model_dump_json()}]", encoding="utf-8")
    prompts_path.write_text(f"[{_prompt().model_dump_json()}]", encoding="utf-8")

    registry = ModelRegistry.from_json_files(
        profiles_path=profiles_path,
        prompts_path=prompts_path,
    )

    assert registry.get_profile("internal-json").model_name == "rune-internal"
    assert registry.active_prompt_for_task("node_extraction").prompt_version_id == "pv_node_v1"


def test_default_model_registry_files_load() -> None:
    settings = Settings()

    registry = ModelRegistry.from_json_files(
        profiles_path=Path(settings.model_profiles_path),
        prompts_path=Path(settings.prompt_versions_path),
    )

    assert registry.get_profile("dummy-local").provider == "dummy"
    assert (
        registry.active_prompt_for_task("node_extraction").prompt_version_id
        == "pv_node_extraction_v1"
    )
    assert (
        registry.active_prompt_for_task("edge_linking").prompt_version_id
        == "pv_edge_linking_v1"
    )
    assert (
        registry.active_prompt_for_task("soc_axis_classification").prompt_version_id
        == "pv_soc_axis_classification_v1"
    )


def test_model_registry_blocks_inactive_profile() -> None:
    registry = ModelRegistry(
        profiles=[_profile().model_copy(update={"is_active": False})],
        prompts=[_prompt()],
    )

    with pytest.raises(ModelRegistryError):
        registry.get_profile("internal-json")


def test_provider_factory_requires_endpoint_for_live_profiles() -> None:
    with pytest.raises(ValueError):
        provider_for_profile(_profile())

    provider = provider_for_profile(
        _profile(),
        endpoint_url="https://models.example.com/v1/complete",
        transport=lambda *_args: {"output": {}},
    )
    assert provider is not None


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="internal-json",
        provider="internal",
        model_name="rune-internal",
        endpoint_alias="internal-gateway",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=8192,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def _prompt() -> PromptVersion:
    return PromptVersion(
        prompt_version_id="pv_node_v1",
        task_name="node_extraction",
        template="Extract nodes",
        schema_version_ref="node_extraction.v1",
        retrieval_policy_id="ret_default",
        created_by="tester",
        status="active",
    )
