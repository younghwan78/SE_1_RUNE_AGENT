"""Model gateway data contracts."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

Provider = Literal["internal", "openai", "anthropic", "azure", "local", "dummy"]
PromptTask = Literal[
    "node_extraction",
    "edge_linking",
    "finding_reasoning",
    "impact_analysis",
    "answer_generation",
]
PromptStatus = Literal["draft", "eval_ready", "canary", "active", "retired"]


class GatewayModel(BaseModel):
    """Base model for model gateway contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ModelProfile(GatewayModel):
    """Model endpoint/profile configuration."""

    model_profile_id: str
    provider: Provider
    model_name: str
    endpoint_alias: str
    allowed_data_classes: list[str] = Field(default_factory=list)
    supports_json_schema: bool
    supports_tool_calling: bool
    max_context_tokens: int = Field(gt=0)
    default_temperature: float = Field(ge=0.0, le=2.0)
    timeout_seconds: int = Field(gt=0)
    is_active: bool = True
    schema_version: str = SCHEMA_VERSION


class PromptVersion(GatewayModel):
    """Versioned prompt template metadata."""

    prompt_version_id: str
    task_name: PromptTask
    template: str
    schema_version_ref: str
    retrieval_policy_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: PromptStatus = "draft"
    schema_version: str = SCHEMA_VERSION


class ModelRequest(GatewayModel):
    """Request passed through the model gateway."""

    model_profile_id: str
    prompt_version_id: str
    payload: dict[str, Any]
    data_classification: str
    schema_version: str = SCHEMA_VERSION


class ModelResponse(GatewayModel):
    """Response returned from the model gateway."""

    model_profile_id: str
    prompt_version_id: str
    raw_response_ref: str | None = None
    parsed_output_ref: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = Field(ge=0)
    schema_version: str = SCHEMA_VERSION


class StructuredValidationResult(GatewayModel):
    """Structured output validation result."""

    status: Literal["passed", "failed", "repaired"]
    error_message: str | None = None
    repaired_output: dict[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

