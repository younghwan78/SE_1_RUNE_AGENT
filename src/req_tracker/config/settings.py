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
        populate_by_name=True,
    )

    environment: str = Field(default="local", validation_alias="REQ_TRACKER_ENV")
    datasource_mode: str = Field(default="dummy", validation_alias="DATASOURCE_MODE")
    source_export_path: Path = Field(default=Path(""), validation_alias="SOURCE_EXPORT_PATH")
    jira_base_url: str = Field(default="", validation_alias="JIRA_BASE_URL")
    jira_token: str = Field(default="", validation_alias="JIRA_TOKEN")
    jira_jql: str = Field(default="", validation_alias="JIRA_JQL")
    confluence_base_url: str = Field(default="", validation_alias="CONFLUENCE_BASE_URL")
    confluence_token: str = Field(default="", validation_alias="CONFLUENCE_TOKEN")
    confluence_space_key: str = Field(default="", validation_alias="CONFLUENCE_SPACE_KEY")
    confluence_cql: str = Field(default="", validation_alias="CONFLUENCE_CQL")
    graph_backend: str = Field(default="memory", validation_alias="GRAPH_BACKEND")
    neo4j_uri: str = Field(default="", validation_alias="NEO4J_URI")
    neo4j_username: str = Field(default="neo4j", validation_alias="NEO4J_USERNAME")
    neo4j_password: str = Field(default="", validation_alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", validation_alias="NEO4J_DATABASE")
    vector_backend: str = Field(default="memory", validation_alias="VECTOR_BACKEND")
    qdrant_url: str = Field(default="", validation_alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", validation_alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="rune_chunks", validation_alias="QDRANT_COLLECTION")
    qdrant_vector_size: int = Field(default=64, ge=8, validation_alias="QDRANT_VECTOR_SIZE")
    auth_mode: str = Field(default="local", validation_alias="AUTH_MODE")
    api_key: str = Field(default="", validation_alias="API_KEY")
    trusted_proxy_secret: str = Field(default="", validation_alias="TRUSTED_PROXY_SECRET")
    trusted_default_role: str = Field(default="viewer", validation_alias="TRUSTED_DEFAULT_ROLE")
    trusted_group_role_map: dict[str, str] = Field(
        default_factory=lambda: {
            "rune-viewers": "viewer",
            "rune-developers": "developer",
            "rune-operators": "operator",
            "rune-admins": "admin",
        },
        validation_alias="TRUSTED_GROUP_ROLE_MAP",
    )
    audit_retention_days: int = Field(default=365, ge=1, validation_alias="AUDIT_RETENTION_DAYS")
    audit_max_events: int = Field(default=100_000, ge=1, validation_alias="AUDIT_MAX_EVENTS")
    model_gateway_mode: str = Field(default="dummy", validation_alias="MODEL_GATEWAY_MODE")
    model_gateway_endpoint_url: str = Field(
        default="",
        validation_alias="MODEL_GATEWAY_ENDPOINT_URL",
    )
    model_gateway_api_key: str = Field(default="", validation_alias="MODEL_GATEWAY_API_KEY")
    model_gateway_claude_command: str = Field(
        default="",
        validation_alias="MODEL_GATEWAY_CLAUDE_COMMAND",
    )
    model_profiles_path: Path = Field(
        default=Path("config/model_profiles.json"),
        validation_alias="MODEL_PROFILES_PATH",
    )
    prompt_versions_path: Path = Field(
        default=Path("config/prompt_versions.json"),
        validation_alias="PROMPT_VERSIONS_PATH",
    )
    soc_query_planner_mode: str = Field(
        default="deterministic",
        validation_alias="SOC_QUERY_PLANNER_MODE",
    )
    soc_query_planner_model_profile_id: str = Field(
        default="dummy-local",
        validation_alias="SOC_QUERY_PLANNER_MODEL_PROFILE_ID",
    )
    soc_query_tool_planner_mode: str = Field(
        default="deterministic",
        validation_alias="SOC_QUERY_TOOL_PLANNER_MODE",
    )
    soc_query_tool_planner_model_profile_id: str = Field(
        default="dummy-local",
        validation_alias="SOC_QUERY_TOOL_PLANNER_MODEL_PROFILE_ID",
    )
    soc_answer_assembler_mode: str = Field(
        default="deterministic",
        validation_alias="SOC_ANSWER_ASSEMBLER_MODE",
    )
    soc_answer_assembler_model_profile_id: str = Field(
        default="dummy-local",
        validation_alias="SOC_ANSWER_ASSEMBLER_MODEL_PROFILE_ID",
    )
    soc_reranker_mode: str = Field(
        default="deterministic",
        validation_alias="SOC_RERANKER_MODE",
    )
    soc_reranker_model_profile_id: str = Field(
        default="dummy-local",
        validation_alias="SOC_RERANKER_MODEL_PROFILE_ID",
    )
    soc_cross_encoder_model_name: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        validation_alias="SOC_CROSS_ENCODER_MODEL_NAME",
    )
    soc_embedding_model_name: str = Field(
        default="BAAI/bge-m3",
        validation_alias="SOC_EMBEDDING_MODEL_NAME",
    )
    soc_embedding_dimensions: int = Field(
        default=1024,
        ge=1,
        validation_alias="SOC_EMBEDDING_DIMENSIONS",
    )
    soc_retrieval_backend: str = Field(
        default="fixture",
        validation_alias="SOC_RETRIEVAL_BACKEND",
    )
    artifact_store: str = Field(default="local", validation_alias="ARTIFACT_STORE")
    artifact_root: Path = Field(default=Path(".local_artifacts"), validation_alias="ARTIFACT_ROOT")
    state_store: str = Field(default="memory", validation_alias="STATE_STORE")
    sqlite_state_path: Path = Field(
        default=Path(".local_state/rune_state.sqlite3"),
        validation_alias="SQLITE_STATE_PATH",
    )
    postgres_dsn: str = Field(default="", validation_alias="POSTGRES_DSN")
    postgres_migration_profile: str = Field(
        default="core",
        validation_alias="POSTGRES_MIGRATION_PROFILE",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    otel_enabled: bool = Field(default=False, validation_alias="OTEL_ENABLED")
    otel_service_name: str = Field(
        default="rune-agent-api",
        validation_alias="OTEL_SERVICE_NAME",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_exporter_otlp_insecure: bool = Field(
        default=True,
        validation_alias="OTEL_EXPORTER_OTLP_INSECURE",
    )
    enable_docs: bool = Field(default=True, validation_alias="ENABLE_DOCS")
    scheduler_enabled: bool = Field(default=False, validation_alias="SCHEDULER_ENABLED")
    scheduler_interval_seconds: int = Field(
        default=3600,
        ge=1,
        validation_alias="SCHEDULER_INTERVAL_SECONDS",
    )
    scheduler_project_key: str = Field(
        default="RUNE_CAM_ALPHA",
        validation_alias="SCHEDULER_PROJECT_KEY",
    )
    scheduler_scenario: str = Field(
        default="RUNE_MULTI_SOURCE",
        validation_alias="SCHEDULER_SCENARIO",
    )
    scheduler_lease_name: str = Field(
        default="rune-periodic-analysis",
        validation_alias="SCHEDULER_LEASE_NAME",
    )
    scheduler_lease_ttl_seconds: int = Field(
        default=300,
        ge=30,
        validation_alias="SCHEDULER_LEASE_TTL_SECONDS",
    )

    def new_id(self, prefix: str) -> str:
        """Generate a compact runtime id with a stable prefix."""
        return f"{prefix}_{uuid4().hex[:12]}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
