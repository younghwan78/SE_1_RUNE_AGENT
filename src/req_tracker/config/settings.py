"""Runtime settings."""

from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="local", validation_alias="REQ_TRACKER_ENV")
    datasource_mode: str = Field(default="dummy", validation_alias="DATASOURCE_MODE")
    graph_backend: str = Field(default="memory", validation_alias="GRAPH_BACKEND")
    vector_backend: str = Field(default="memory", validation_alias="VECTOR_BACKEND")
    model_gateway_mode: str = Field(default="dummy", validation_alias="MODEL_GATEWAY_MODE")
    artifact_store: str = Field(default="local", validation_alias="ARTIFACT_STORE")
    artifact_root: Path = Field(default=Path(".local_artifacts"), validation_alias="ARTIFACT_ROOT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    enable_docs: bool = Field(default=True, validation_alias="ENABLE_DOCS")

    def new_id(self, prefix: str) -> str:
        """Generate a compact runtime id with a stable prefix."""
        return f"{prefix}_{uuid4().hex[:12]}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()

