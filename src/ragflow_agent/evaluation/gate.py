"""Non-waivable security, permission, citation, and recovery release gates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReleaseThresholds:
    retrieval_recall_at_10: float = 0.90
    answer_faithfulness: float = 0.90
    citation_recall: float = 0.95
    max_internal_error_rate: float = 0.01


@dataclass(frozen=True, slots=True)
class GateResult:
    passed: bool
    failures: tuple[str, ...]


def evaluate_release_gate(
    report: dict[str, float | int], thresholds: ReleaseThresholds | None = None
) -> GateResult:
    limits = thresholds or ReleaseThresholds()
    failures: list[str] = []
    if int(report.get("cross_tenant_violations", 1)) != 0:
        failures.append("cross_tenant_violations")
    if int(report.get("critical_security_violations", 1)) != 0:
        failures.append("critical_security_violations")
    if int(report.get("recovery_failures", 1)) != 0:
        failures.append("recovery_failures")
    if float(report.get("retrieval_recall_at_10", 0)) < limits.retrieval_recall_at_10:
        failures.append("retrieval_recall_at_10")
    if float(report.get("answer_faithfulness", 0)) < limits.answer_faithfulness:
        failures.append("answer_faithfulness")
    if float(report.get("citation_recall", 0)) < limits.citation_recall:
        failures.append("citation_recall")
    if float(report.get("internal_error_rate", 1)) >= limits.max_internal_error_rate:
        failures.append("internal_error_rate")
    return GateResult(not failures, tuple(failures))
