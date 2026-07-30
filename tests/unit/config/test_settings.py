"""Tests for typed bootstrap configuration."""

import json

import pytest
from pydantic import SecretStr, ValidationError

from ragflow_agent.config import (
    ApiSettings,
    AppSettings,
    DatabaseSettings,
    ModelSettings,
    ObjectStoreSettings,
    load_settings,
)


def make_settings() -> AppSettings:
    """Build settings without reading the developer environment."""
    return AppSettings(
        database=DatabaseSettings(
            url=SecretStr("postgresql+psycopg://user:top-secret@localhost/app")
        ),
    )


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGFLOW_AGENT_DATABASE__URL", raising=False)
    with pytest.raises(ValidationError):
        AppSettings.model_validate({})


def test_defaults_are_typed_and_immutable() -> None:
    settings = make_settings()

    assert settings.api.port == 8000
    assert settings.worker.service_name == "ragflow-agent-ingestion-worker"
    assert settings.search.backend == "elasticsearch"
    assert settings.models.chat_model == "deepseek-chat"
    assert settings.models.embedding_model == "BAAI/bge-m3"
    with pytest.raises(ValidationError):
        settings.api.port = 9000


def test_invalid_port_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ApiSettings(port=70000)


def test_object_store_credentials_must_be_a_pair() -> None:
    with pytest.raises(ValidationError, match="configured together"):
        ObjectStoreSettings(access_key=SecretStr("only-one"))


def test_nested_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "RAGFLOW_AGENT_DATABASE__URL",
        "postgresql+psycopg://env-user:env-secret@db/env-db",
    )
    monkeypatch.setenv("RAGFLOW_AGENT_API__PORT", "8100")
    monkeypatch.setenv("RAGFLOW_AGENT_OBSERVABILITY__JSON_LOGS", "false")

    settings = load_settings(env_file=None)

    assert settings.api.port == 8100
    assert settings.observability.json_logs is False


def test_secret_values_are_redacted() -> None:
    settings = make_settings()

    rendered = json.dumps(settings.redacted_dict())

    assert "top-secret" not in rendered
    assert "**********" in rendered


def test_blank_optional_model_credentials_are_unconfigured() -> None:
    settings = ModelSettings.model_validate(
        {"chat_api_key": "", "embedding_api_key": "   "}
    )

    assert settings.chat_api_key is None
    assert settings.embedding_api_key is None
