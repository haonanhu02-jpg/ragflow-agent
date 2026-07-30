"""Platform-compatible event loop for async psycopg Checkpointer tests."""

import asyncio
import selectors
from collections.abc import Callable, Mapping

import pytest


def _selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    del config, item
    return {"selector": _selector_loop}
