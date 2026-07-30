"""Validated configuration shared by the API and ingestion worker bootstraps."""

from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
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


class DatabaseSettings(FrozenSettingsModel):
    """PostgreSQL connection settings."""

    url: SecretStr
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=200)
    pool_timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class QueueSettings(FrozenSettingsModel):
    """Queue endpoint settings without selecting final delivery semantics."""

    url: SecretStr = SecretStr("redis://localhost:6379/0")
    namespace: str = "ragflow-agent"


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
    """Search configuration that preserves the unresolved backend decision."""

    backend: Literal["unconfigured"] = "unconfigured"
    url: SecretStr | None = None


class ModelSettings(FrozenSettingsModel):
    """Provider-neutral model configuration placeholder."""

    provider: str | None = None
    api_key: SecretStr | None = None


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
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    def redacted_dict(self) -> dict[str, object]:
        """Return a JSON-compatible view where SecretStr values stay redacted."""
        return cast(dict[str, object], self.model_dump(mode="json"))


def load_settings(*, env_file: str | Path | None = ".env") -> AppSettings:
    """Load settings from the process environment and an optional env file."""
    # pydantic-settings accepts this bootstrap-only keyword at runtime, but its
    # dataclass transform does not expose it in the generated mypy signature.
    return AppSettings(_env_file=env_file)  # type: ignore[call-arg]
