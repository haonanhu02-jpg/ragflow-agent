from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from ragflow_agent.config import AdvancedRagSettings, AppSettings, DatabaseSettings


def test_advanced_features_are_fail_closed() -> None:
    settings = AdvancedRagSettings()
    enabled_fields = [
        name for name, value in settings.model_dump().items() if name.endswith("_enabled") and value
    ]
    assert enabled_fields == []


def test_production_example_contains_no_real_secret_and_compose_is_non_root() -> None:
    example = Path("deploy/production.env.example").read_text(encoding="utf-8")
    compose = Path("deploy/docker-compose.prod.yml").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    edge = Path("deploy/edge/nginx.conf").read_text(encoding="utf-8")
    assert "REDACTED" in example
    assert "no-new-privileges:true" in compose
    assert "cap_drop" in compose
    assert "USER ragflow-agent" in dockerfile
    assert 'org.opencontainers.image.licenses="NOASSERTION"' in dockerfile
    assert "ssl_protocols TLSv1.2 TLSv1.3" in edge
    assert "limit_req zone=api_per_ip" in edge
    assert 'internal: true' in compose


def test_production_configuration_fails_fast_without_object_credentials() -> None:
    with pytest.raises(ValidationError, match="object store credentials"):
        AppSettings(
            environment="production",
            database=DatabaseSettings(url=SecretStr("postgresql+psycopg://test")),
        )
