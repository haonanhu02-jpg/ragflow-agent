"""Selector event loop for psycopg on Windows lifecycle E2E."""

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
