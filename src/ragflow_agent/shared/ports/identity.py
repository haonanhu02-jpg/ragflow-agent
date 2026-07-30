"""Identifier generation boundary."""

from typing import Protocol, runtime_checkable
from uuid import uuid4


@runtime_checkable
class IdGenerator(Protocol):
    """Generate opaque identifiers."""

    def new_id(self) -> str: ...


class Uuid4Generator:
    """Production-safe random identifier generator."""

    def new_id(self) -> str:
        return str(uuid4())
