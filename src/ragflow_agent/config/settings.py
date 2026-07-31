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
    max_tries: int = Field(default=3, ge=1, le=20)
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
    request_timeout_seconds: float = Field(default=60, gt=0, le=600)

    @field_validator("chat_api_key", "embedding_api_key", mode="before")
    @classmethod
    def blank_credentials_are_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


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
    """Logging and trace settings."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = True


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
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    def redacted_dict(self) -> dict[str, object]:
        """Return a JSON-compatible view where SecretStr values stay redacted."""
        return cast(dict[str, object], self.model_dump(mode="json"))


def load_settings(*, env_file: str | Path | None = ".env") -> AppSettings:
    """Load settings from the process environment and an optional env file."""
    # pydantic-settings accepts this bootstrap-only keyword at runtime, but its
    # dataclass transform does not expose it in the generated mypy signature.
    return AppSettings(_env_file=env_file)  # type: ignore[call-arg]
