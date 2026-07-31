"""Deterministic evidence sufficiency and untrusted-content policy."""

from __future__ import annotations

import re
from collections import defaultdict

from ragflow_agent.agent.domain.agentic import (
    EvidenceDecision,
    EvidenceItem,
    EvidenceStatus,
    QueryPlan,
)

_PROMPT_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+)?previous",
        r"system\s+prompt",
        r"developer\s+message",
        r"reveal\s+.*(secret|token|password)",
        r"忽略.{0,12}(之前|以上|系统).{0,12}(指令|规则)",
        r"泄露.{0,12}(密钥|口令|系统提示)",
    )
)


def contains_prompt_injection(value: str) -> bool:
    """Flag common instruction-smuggling text without executing it."""
    return any(pattern.search(value) is not None for pattern in _PROMPT_INJECTION_PATTERNS)


class EvidenceSufficiencyPolicy:
    """Server-side final decision; LLM output cannot override this result."""

    def __init__(self, *, minimum_normalized_score: float = 0.0) -> None:
        if not 0 <= minimum_normalized_score <= 1:
            raise ValueError("minimum normalized evidence score must be within [0, 1]")
        self._minimum_score = minimum_normalized_score

    def evaluate(
        self,
        *,
        tenant_id: str,
        plan: QueryPlan,
        evidence: tuple[EvidenceItem, ...],
    ) -> EvidenceDecision:
        eligible = tuple(
            item
            for item in evidence
            if item.tenant_id == tenant_id
            and item.authorized
            and item.active_version
            and item.normalized_score >= self._minimum_score
            and not item.injection_detected
            and not contains_prompt_injection(item.excerpt)
            and (item.source_kind != "knowledge" or item.citation is not None)
        )
        by_step: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in eligible:
            by_step[item.step_id].append(item)

        critical = tuple(step.step_id for step in plan.steps if step.critical)
        covered = tuple(step for step in critical if by_step.get(step))
        missing = tuple(step for step in critical if not by_step.get(step))

        stances: dict[str, set[str]] = defaultdict(set)
        for item in eligible:
            if item.fact_key and item.stance:
                stances[item.fact_key].add(item.stance.strip().lower())
        conflicts = tuple(sorted(key for key, values in stances.items() if len(values) > 1))
        ids = tuple(item.evidence_id for item in eligible)
        if conflicts:
            return EvidenceDecision(
                status=EvidenceStatus.CONFLICTING_EVIDENCE,
                covered_critical_steps=covered,
                missing_critical_steps=missing,
                conflicting_fact_keys=conflicts,
                eligible_evidence_ids=ids,
                reason="unresolved critical evidence conflict",
            )
        if not eligible:
            return EvidenceDecision(
                status=EvidenceStatus.NO_EVIDENCE,
                missing_critical_steps=critical,
                reason="no authorized eligible evidence",
            )
        if missing:
            return EvidenceDecision(
                status=EvidenceStatus.PARTIAL_EVIDENCE,
                covered_critical_steps=covered,
                missing_critical_steps=missing,
                eligible_evidence_ids=ids,
                reason="critical subquestions are not fully covered",
            )
        return EvidenceDecision(
            status=EvidenceStatus.SUFFICIENT,
            covered_critical_steps=covered,
            eligible_evidence_ids=ids,
            reason="all critical subquestions have eligible cited evidence",
        )
