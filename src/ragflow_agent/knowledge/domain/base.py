"""Shared immutable primitives for the knowledge domain."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class KnowledgeModel(BaseModel):
    """Immutable, strict and serialization-safe domain model."""

    model_config = ConfigDict(extra="forbid", frozen=True)
