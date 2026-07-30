"""PostgreSQL Agent test helpers."""

import os

import pytest


def checkpoint_database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value
