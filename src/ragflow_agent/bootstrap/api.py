"""API process entrypoint."""

import argparse

import uvicorn
from pydantic import SecretStr

from ragflow_agent.api import create_app
from ragflow_agent.config import (
    AppSettings,
    DatabaseSettings,
    ObjectStoreSettings,
    load_settings,
)
from ragflow_agent.knowledge.runtime import build_minimum_rag_runtime


def _check_settings() -> AppSettings:
    """Return non-secret settings for side-effect-free wiring validation."""
    return AppSettings(
        database=DatabaseSettings(
            url=SecretStr("postgresql+psycopg://check:check@localhost/check")
        ),
        object_store=ObjectStoreSettings(
            access_key=SecretStr("bootstrap-check"),
            secret_key=SecretStr("bootstrap-check"),
        ),
    )


def check_bootstrap() -> None:
    """Validate app construction without connecting to infrastructure."""
    settings = _check_settings()
    app = create_app(
        settings,
        minimum_rag_runtime=build_minimum_rag_runtime(settings),
    )
    paths = set(app.openapi()["paths"])
    required = {
        "/health/live",
        "/health/ready",
        "/v1/knowledge-bases",
        "/v1/knowledge-bases/{knowledge_base_id}/documents",
        "/v1/ingestion-jobs/{job_id}",
        "/v1/rag/query",
    }
    if not required.issubset(paths):
        raise RuntimeError(f"API bootstrap is missing routes: {sorted(required - paths)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ragflow-agent API")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate process wiring without starting a server",
    )
    args = parser.parse_args()

    if args.check:
        check_bootstrap()
        print("API bootstrap check passed")
        return

    settings = load_settings()
    runtime = build_minimum_rag_runtime(settings)
    uvicorn.run(
        create_app(settings, minimum_rag_runtime=runtime),
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.observability.log_level.lower(),
    )


if __name__ == "__main__":
    main()
