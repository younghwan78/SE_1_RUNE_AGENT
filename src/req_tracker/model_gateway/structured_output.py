"""Structured output validation helpers."""

from typing import Any

from pydantic import BaseModel, ValidationError

from req_tracker.model_gateway.models import StructuredValidationResult


def validate_structured_output[TModel: BaseModel](
    output: dict[str, Any],
    response_model: type[TModel],
) -> tuple[TModel | None, StructuredValidationResult]:
    """Validate a model output dict against a Pydantic response model."""
    try:
        parsed = response_model.model_validate(output)
    except ValidationError as exc:
        return None, StructuredValidationResult(status="failed", error_message=str(exc))
    return parsed, StructuredValidationResult(status="passed")
