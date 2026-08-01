"""Bounded candidate-question generation with deterministic fallback."""

import re
from datetime import datetime

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedCapability
from ragflow_agent.knowledge.advanced.enrichment.common import artifact_from_chunk
from ragflow_agent.knowledge.domain.chunk import ChunkRecord

_SENTENCE = re.compile(r"(?<=[。.!?])\s+")


class QuestionGenerator:
    def generate(
        self,
        chunk: ChunkRecord,
        *,
        build_version: str,
        created_at: datetime,
        limit: int = 5,
    ) -> AdvancedArtifact:
        if not 1 <= limit <= 5:
            raise ValueError("question limit must be between 1 and 5")
        sentences = [
            item.strip(" 。.!?") for item in _SENTENCE.split(chunk.content) if item.strip()
        ]
        questions: list[str] = []
        for sentence in sentences:
            subject = sentence[:72]
            candidate = f"文档对“{subject}”说明了什么?"
            if candidate not in questions:
                questions.append(candidate)
            if len(questions) == limit:
                break
        if not questions:
            questions.append("该片段的主要信息是什么?")
        return artifact_from_chunk(
            chunk,
            capability=AdvancedCapability.QUESTIONS,
            build_version=build_version,
            text="\n".join(questions),
            created_at=created_at,
            attributes=(("question_count", str(len(questions))),),
        )
