"""Validated configuration shared by the API and ingestion worker bootstraps."""

from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrozenSettingsModel(BaseModel):
    """Base class for immutable nested settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ApiSettings(FrozenSettingsModel):
    """HTTP process settings."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    service_name: str = "ragflow-agent-api"


class WorkerSettings(FrozenSettingsModel):
    """Ingestion worker process settings."""

    poll_interval_seconds: float = Field(default=1.0, gt=0, le=60)
    heartbeat_interval_seconds: float = Field(default=10.0, gt=0, le=300)
    service_name: str = "ragflow-agent-ingestion-worker"
    max_tries: int = Field(default=6, ge=1, le=20)
    job_timeout_seconds: int = Field(default=300, ge=1, le=86_400)


class DatabaseSettings(FrozenSettingsModel):
    """PostgreSQL connection settings."""

    url: SecretStr
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=200)
    pool_timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class QueueSettings(FrozenSettingsModel):
    """Redis/ARQ queue settings."""

    url: SecretStr = SecretStr("redis://localhost:6379/0")
    namespace: str = "ragflow-agent"
    queue_name: str = "arq:ragflow-agent:ingestion"


class ObjectStoreSettings(FrozenSettingsModel):
    """S3-compatible object storage settings."""

    endpoint_url: str = "http://localhost:9000"
    bucket: str = "ragflow-agent"
    access_key: SecretStr | None = None
    secret_key: SecretStr | None = None
    secure: bool = False

    @model_validator(mode="after")
    def credentials_must_be_a_pair(self) -> Self:
        """Reject partial credentials before an adapter is constructed."""
        if (self.access_key is None) != (self.secret_key is None):
            raise ValueError("object store access_key and secret_key must be configured together")
        return self


class SearchSettings(FrozenSettingsModel):
    """Elasticsearch adapter configuration."""

    backend: Literal["elasticsearch"] = "elasticsearch"
    url: SecretStr = SecretStr("http://localhost:9200")
    index_name: str = "ragflow-agent-chunks-v1"
    request_timeout_seconds: float = Field(default=30, gt=0, le=300)
    verify_certs: bool = True


class ModelSettings(FrozenSettingsModel):
    """OpenAI-compatible provider configuration behind internal ports."""

    provider: Literal["openai-compatible"] = "openai-compatible"
    chat_model: str = "deepseek-chat"
    chat_base_url: str = "https://api.deepseek.com"
    chat_api_key: SecretStr | None = None
    embedding_model: str = "BAAI/bge-m3"
    embedding_base_url: str = "http://localhost:8080/v1"
    embedding_api_key: SecretStr | None = None
    embedding_dimensions: int = Field(default=1024, ge=1, le=65_536)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_base_url: str | None = None
    reranker_api_key: SecretStr | None = None
    request_timeout_seconds: float = Field(default=60, gt=0, le=600)

    @field_validator("chat_api_key", "embedding_api_key", "reranker_api_key", mode="before")
    @classmethod
    def blank_credentials_are_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("reranker_base_url", mode="before")
    @classmethod
    def blank_reranker_url_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class RetrievalSettings(FrozenSettingsModel):
    """Phase 06 online retrieval profile and bounded fallback policy."""

    config_version: str = "retrieval-v2"
    rrf_k: int = Field(default=60, ge=1, le=10_000)
    candidate_top_k: int = Field(default=100, ge=1, le=10_000)
    rerank_candidate_count: int = Field(default=30, ge=1, le=1_000)
    final_top_k: int = Field(default=10, ge=1, le=1_000)
    fusion_threshold: float = Field(default=0.0, ge=0)
    fallback_threshold_floor: float = Field(default=0.0, ge=0)
    max_fallback_attempts: int = Field(default=4, ge=0, le=4)
    fallback_candidate_multiplier: int = Field(default=2, ge=1, le=10)
    per_document_limit: int = Field(default=4, ge=1, le=100)
    reranker_timeout_seconds: float = Field(default=5, gt=0, le=120)
    rewrite_enabled: bool = True
    translation_enabled: bool = True
    keyword_expansion_enabled: bool = True
    max_query_variants: int = Field(default=8, ge=1, le=32)
    max_query_characters: int = Field(default=8_000, ge=1, le=100_000)

    @model_validator(mode="after")
    def candidate_windows_are_ordered(self) -> Self:
        if self.final_top_k > self.rerank_candidate_count:
            raise ValueError("final_top_k cannot exceed rerank_candidate_count")
        if self.rerank_candidate_count > self.candidate_top_k:
            raise ValueError("rerank_candidate_count cannot exceed candidate_top_k")
        if self.fallback_threshold_floor > self.fusion_threshold:
            raise ValueError("fallback threshold floor cannot exceed the normal threshold")
        return self


class RetrievalTraceSettings(FrozenSettingsModel):
    """Content-minimized trace retention and privileged access profile."""

    retention_days: int = Field(default=30, ge=1, le=365)
    aggregate_retention_days: int = Field(default=180, ge=1, le=3_650)
    detailed_roles: tuple[str, ...] = ("retrieval_debug", "operations")

    @model_validator(mode="after")
    def aggregate_retention_is_not_shorter(self) -> Self:
        if self.aggregate_retention_days < self.retention_days:
            raise ValueError("aggregate retention cannot be shorter than full trace retention")
        return self


class LifecycleSettings(FrozenSettingsModel):
    """Bounded Phase 07 version, retry, retention, and batch policy."""

    max_attempts: int = Field(default=6, ge=1, le=20)
    concurrency_attempts: int = Field(default=3, ge=1, le=10)
    retry_base_seconds: float = Field(default=1, gt=0, le=60)
    retry_max_seconds: float = Field(default=300, gt=0, le=3_600)
    operation_timeout_seconds: int = Field(default=3_600, ge=1, le=86_400)
    history_retention_days: int = Field(default=30, ge=1, le=3_650)
    soft_delete_retention_days: int = Field(default=30, ge=1, le=3_650)
    previous_index_retention_days: int = Field(default=7, ge=1, le=365)
    purge_completion_hours: int = Field(default=24, ge=1, le=168)
    outbox_batch_size: int = Field(default=100, ge=1, le=10_000)
    reconcile_batch_size: int = Field(default=100, ge=1, le=10_000)
    batch_size: int = Field(default=100, ge=1, le=10_000)
    batch_concurrency: int = Field(default=2, ge=1, le=100)

    @model_validator(mode="after")
    def retry_profile_is_ordered(self) -> Self:
        if self.concurrency_attempts > self.max_attempts:
            raise ValueError("concurrency attempts cannot exceed lifecycle max attempts")
        if self.retry_base_seconds > self.retry_max_seconds:
            raise ValueError("retry base cannot exceed retry maximum")
        return self


class AgenticRagSettings(FrozenSettingsModel):
    """Server-enforced Phase 08 Agentic RAG policy profile."""

    max_agent_iterations: int = Field(default=8, ge=1, le=64)
    max_model_calls: int = Field(default=6, ge=1, le=64)
    max_retrieval_rounds: int = Field(default=3, ge=1, le=8)
    max_tool_attempts: int = Field(default=10, ge=1, le=100)
    max_total_tokens: int = Field(default=50_000, ge=1, le=2_000_000)
    max_generated_tokens: int = Field(default=8_000, ge=1, le=200_000)
    finalization_token_reserve: int = Field(default=1_500, ge=0, le=100_000)
    max_active_runtime_seconds: float = Field(default=120, gt=0, le=3_600)
    model_timeout_seconds: float = Field(default=45, gt=0, le=600)
    tool_timeout_seconds: float = Field(default=15, gt=0, le=300)
    max_known_cost_usd: float = Field(default=0.50, ge=0, le=1_000)
    model_input_cost_per_million_tokens_usd: float | None = Field(default=None, ge=0, le=100_000)
    model_output_cost_per_million_tokens_usd: float | None = Field(default=None, ge=0, le=100_000)
    approval_ttl_minutes: int = Field(default=30, ge=1, le=1_440)
    memory_ttl_days: int = Field(default=90, ge=1, le=365)
    memory_cleanup_hours: int = Field(default=24, ge=1, le=168)
    sql_max_rows: int = Field(default=200, ge=1, le=10_000)
    sql_timeout_seconds: float = Field(default=5, gt=0, le=120)
    api_connect_timeout_seconds: float = Field(default=5, gt=0, le=60)
    api_read_timeout_seconds: float = Field(default=15, gt=0, le=300)
    api_max_response_bytes: int = Field(default=1_000_000, ge=1, le=20_000_000)
    evidence_min_score: float = Field(default=0.0, ge=0)
    sql_database_url: SecretStr | None = None

    @field_validator("sql_database_url", mode="before")
    @classmethod
    def blank_sql_database_url_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def budget_and_retention_are_consistent(self) -> Self:
        if self.finalization_token_reserve > self.max_total_tokens:
            raise ValueError("finalization token reserve cannot exceed total token budget")
        if self.memory_cleanup_hours > 24:
            raise ValueError("memory cleanup must complete within 24 hours")
        if (self.model_input_cost_per_million_tokens_usd is None) != (
            self.model_output_cost_per_million_tokens_usd is None
        ):
            raise ValueError("model input and output rates must be configured together")
        return self


class IngestionSettings(FrozenSettingsModel):
    """Bounded upload, parser, OCR, chunk, and index profile."""

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    chunk_max_tokens: int = Field(default=384, ge=16, le=8192)
    chunk_overlap_tokens: int = Field(default=48, ge=0, le=2048)
    parser_timeout_seconds: float = Field(default=30, gt=0, le=300)
    ocr_languages: str = "eng"
    tesseract_command: str | None = None
    ooxml_max_entries: int = Field(default=5_000, ge=1)
    ooxml_max_uncompressed_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    ooxml_max_compression_ratio: float = Field(default=100, ge=1)
    pdf_max_pages: int = Field(default=2_000, ge=1)
    image_max_pixels: int = Field(default=40_000_000, ge=1)
    xlsx_max_sheets: int = Field(default=64, ge=1)
    xlsx_max_rows_per_sheet: int = Field(default=100_000, ge=1)
    xlsx_max_nonempty_cells: int = Field(default=1_000_000, ge=1)

    @field_validator("ocr_languages")
    @classmethod
    def ocr_languages_are_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ocr_languages must not be blank")
        return normalized

    @field_validator("tesseract_command", mode="before")
    @classmethod
    def blank_tesseract_command_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def overlap_is_smaller_than_chunk(self) -> Self:
        if self.chunk_overlap_tokens >= self.chunk_max_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_max_tokens")
        return self


class ObservabilitySettings(FrozenSettingsModel):
    """Vendor-neutral logging, metrics, and OpenTelemetry settings."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = True
    metrics_enabled: bool = True
    otel_enabled: bool = False
    otlp_endpoint: str | None = None
    trace_retention_days: int = Field(default=30, ge=1, le=365)
    metrics_retention_days: int = Field(default=90, ge=1, le=3_650)


class AdvancedRagSettings(FrozenSettingsModel):
    """Server-owned Phase 09 feature flags and hard resource ceilings."""

    keywords_enabled: bool = False
    questions_enabled: bool = False
    summaries_enabled: bool = False
    toc_enabled: bool = False
    parent_child_enabled: bool = False
    multimodal_enabled: bool = False
    graphrag_enabled: bool = False
    raptor_enabled: bool = False
    temporal_enabled: bool = False
    max_source_chunks: int = Field(default=5_000, ge=1, le=5_000)
    max_active_runtime_seconds: int = Field(default=900, ge=1, le=900)
    max_provider_calls: int = Field(default=500, ge=1, le=500)
    max_generated_tokens: int = Field(default=300_000, ge=1, le=300_000)
    max_keywords_per_chunk: int = Field(default=10, ge=1, le=10)
    max_questions_per_chunk: int = Field(default=5, ge=1, le=5)
    max_chunk_summary_tokens: int = Field(default=512, ge=1, le=512)
    max_document_summary_tokens: int = Field(default=1_500, ge=1, le=1_500)
    max_parent_context_tokens: int = Field(default=6_000, ge=1, le=6_000)
    max_graph_entities: int = Field(default=20_000, ge=1, le=20_000)
    max_graph_edges: int = Field(default=50_000, ge=1, le=50_000)
    max_raptor_levels: int = Field(default=4, ge=1, le=4)
    max_image_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=20 * 1024 * 1024)
    max_image_pixels: int = Field(default=25_000_000, ge=1, le=25_000_000)
    max_audio_seconds: int = Field(default=30 * 60, ge=1, le=30 * 60)
    max_timeseries_points: int = Field(default=1_000_000, ge=1, le=1_000_000)


class ProductionSettings(FrozenSettingsModel):
    """Phase 10 production-candidate SLO and recovery objectives."""

    availability_target: float = Field(default=0.995, ge=0, le=1)
    readiness_p95_ms: int = Field(default=500, ge=1)
    non_llm_api_p95_ms: int = Field(default=1_000, ge=1)
    retrieval_p95_ms: int = Field(default=2_000, ge=1)
    fixed_rag_p95_ms: int = Field(default=20_000, ge=1)
    internal_error_rate_target: float = Field(default=0.01, ge=0, le=1)
    backlog_alert_seconds: int = Field(default=300, ge=1)
    rpo_hours: int = Field(default=24, ge=1)
    rto_hours: int = Field(default=4, ge=1)
    backup_retention_days: int = Field(default=30, ge=1)
    release_owner_role: str = "release_owner"
    security_approver_role: str = "security_approver"
    ops_oncall_role: str = "ops_oncall"


class AppSettings(BaseSettings):
    """Root settings object loaded only at process bootstrap boundaries."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="RAGFLOW_AGENT_",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    api: ApiSettings = Field(default_factory=ApiSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    database: DatabaseSettings
    queue: QueueSettings = Field(default_factory=QueueSettings)
    object_store: ObjectStoreSettings = Field(default_factory=ObjectStoreSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    retrieval_trace: RetrievalTraceSettings = Field(default_factory=RetrievalTraceSettings)
    lifecycle: LifecycleSettings = Field(default_factory=LifecycleSettings)
    agentic_rag: AgenticRagSettings = Field(default_factory=AgenticRagSettings)
    advanced_rag: AdvancedRagSettings = Field(default_factory=AdvancedRagSettings)
    production: ProductionSettings = Field(default_factory=ProductionSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @model_validator(mode="after")
    def production_infrastructure_secrets_are_explicit(self) -> Self:
        """Fail fast when a production process lacks required object credentials."""
        if self.environment == "production" and (
            self.object_store.access_key is None or self.object_store.secret_key is None
        ):
            raise ValueError("production object store credentials must be configured")
        return self

    def redacted_dict(self) -> dict[str, object]:
        """Return a JSON-compatible view where SecretStr values stay redacted."""
        return cast(dict[str, object], self.model_dump(mode="json"))


def load_settings(*, env_file: str | Path | None = ".env") -> AppSettings:
    """Load settings from the process environment and an optional env file."""
    # pydantic-settings accepts this bootstrap-only keyword at runtime, but its
    # dataclass transform does not expose it in the generated mypy signature.
    return AppSettings(_env_file=env_file)  # type: ignore[call-arg]
