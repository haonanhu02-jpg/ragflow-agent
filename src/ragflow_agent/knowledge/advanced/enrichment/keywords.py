"""Deterministic keyword extraction with bounded, source-bound output."""

import re
from collections import Counter
from datetime import datetime

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedCapability
from ragflow_agent.knowledge.advanced.enrichment.common import artifact_from_chunk
from ragflow_agent.knowledge.domain.chunk import ChunkRecord

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.UNICODE)
_STOP = frozenset(
    {"the", "and", "for", "with", "that", "this", "from", "into", "以及", "一个", "进行"}
)


class KeywordExtractor:
    def extract(
        self,
        chunk: ChunkRecord,
        *,
        build_version: str,
        created_at: datetime,
        limit: int = 10,
    ) -> AdvancedArtifact:
        if not 1 <= limit <= 10:
            raise ValueError("keyword limit must be between 1 and 10")
        tokens = [item.casefold() for item in _TOKEN.findall(chunk.content)]
        positions: dict[str, int] = {}
        for position, token in enumerate(tokens):
            positions.setdefault(token, position)
        counts = Counter(token for token in tokens if token not in _STOP)
        ranked = sorted(counts, key=lambda item: (-counts[item], positions[item], item))[:limit]
        text = "\n".join(ranked) if ranked else chunk.content[:80]
        return artifact_from_chunk(
            chunk,
            capability=AdvancedCapability.KEYWORDS,
            build_version=build_version,
            text=text,
            created_at=created_at,
            attributes=(("keyword_count", str(len(ranked))),),
        )
