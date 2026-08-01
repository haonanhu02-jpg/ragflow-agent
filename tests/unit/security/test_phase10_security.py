from pathlib import Path

from ragflow_agent.config import AdvancedRagSettings


def test_advanced_features_are_fail_closed() -> None:
    settings = AdvancedRagSettings()
    enabled_fields = [
        name for name, value in settings.model_dump().items() if name.endswith("_enabled") and value
    ]
    assert enabled_fields == []


def test_production_example_contains_no_real_secret_and_compose_is_non_root() -> None:
    example = Path("deploy/.env.production.example").read_text(encoding="utf-8")
    compose = Path("deploy/docker-compose.prod.yml").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "REDACTED" in example
    assert "no-new-privileges:true" in compose
    assert "cap_drop" in compose
    assert "USER ragflow-agent" in dockerfile
