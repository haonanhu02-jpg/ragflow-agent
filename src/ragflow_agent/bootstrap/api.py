"""API process entrypoint."""

import argparse

import uvicorn
from pydantic import SecretStr

from ragflow_agent.api import create_app
from ragflow_agent.config import AppSettings, DatabaseSettings, load_settings


def _check_settings() -> AppSettings:
    """Return non-secret settings for side-effect-free wiring validation."""
    return AppSettings(
        database=DatabaseSettings(
            url=SecretStr("postgresql+psycopg://check:check@localhost/check")
        )
    )


def check_bootstrap() -> None:
    """Validate app construction without connecting to infrastructure."""
    app = create_app(_check_settings())
    paths = set(app.openapi()["paths"])
    required = {"/health/live", "/health/ready"}
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
    uvicorn.run(
        create_app(settings),
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.observability.log_level.lower(),
    )


if __name__ == "__main__":
    main()
