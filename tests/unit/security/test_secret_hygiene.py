"""Regression tests for repository credential scanning."""

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

_SCRIPT = Path(__file__).parents[3] / "scripts" / "check_secret_hygiene.py"
scan_text = cast(Callable[[str], list[str]], runpy.run_path(str(_SCRIPT))["scan_text"])


def test_runtime_secret_references_are_not_reported() -> None:
    assert scan_text("api_key = settings.chat_api_key") == []


def test_wrapped_literal_secret_is_reported() -> None:
    assert scan_text('api_key=SecretStr("not-a-placeholder")') == ["credential-assignment"]


def test_known_bootstrap_placeholder_is_allowed() -> None:
    assert scan_text('secret_key=SecretStr("bootstrap-check")') == []
