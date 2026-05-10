"""Eval metrics and gate contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

GateStatus = Literal["passed", "blocked"]


class EvalMetricReport(BaseModel):
    """Evaluation metric summary for one dataset candidate."""

    model_config = ConfigDict(extra="forbid")

    eval_run_id: str
    dataset_path: str
    reason_code: str
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    security_failures: int = Field(default=0, ge=0)
    replay_drift_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    schema_version: str = SCHEMA_VERSION


class EvalGatePolicy(BaseModel):
    """Policy required before an improvement can become active."""

    model_config = ConfigDict(extra="forbid")

    min_cases: int = Field(default=2, ge=1)
    min_pass_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    max_security_failures: int = Field(default=0, ge=0)
    max_replay_drift_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    schema_version: str = SCHEMA_VERSION


class EvalGateResult(BaseModel):
    """Decision report for controlled self-improvement activation."""

    model_config = ConfigDict(extra="forbid")

    eval_run_id: str
    status: GateStatus
    policy: EvalGatePolicy
    metrics: list[EvalMetricReport] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
