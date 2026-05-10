"""Model policy enforcement."""

from req_tracker.model_gateway.models import ModelProfile, ModelRequest


class ModelPolicyError(ValueError):
    """Raised when a model request violates policy."""


class ModelPolicy:
    """Validate whether a request may be sent to a model profile."""

    def assert_allowed(self, request: ModelRequest, profile: ModelProfile) -> None:
        """Raise if the model profile cannot receive this data classification."""
        if request.model_profile_id != profile.model_profile_id:
            raise ModelPolicyError("request model_profile_id does not match active profile")
        if request.data_classification not in profile.allowed_data_classes:
            raise ModelPolicyError(
                f"data classification '{request.data_classification}' is not allowed for "
                f"model profile '{profile.model_profile_id}'"
            )

