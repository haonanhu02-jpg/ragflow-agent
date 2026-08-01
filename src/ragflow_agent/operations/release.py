"""Auditable release/rollback decision model with role separation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    allowed: bool
    release_owner_role: str
    security_approver_role: str
    ops_oncall_role: str
    blockers: tuple[str, ...]
    application_image: str
    configuration_version: str
    database_revision: str
    index_version: str


def decide_release(
    *,
    application_image: str,
    configuration_version: str,
    database_revision: str,
    index_version: str,
    quality_gate_passed: bool,
    security_gate_passed: bool,
    recovery_gate_passed: bool,
    real_provider_validated: bool,
) -> ReleaseDecision:
    blockers = []
    if not quality_gate_passed:
        blockers.append("quality_gate")
    if not security_gate_passed:
        blockers.append("security_gate")
    if not recovery_gate_passed:
        blockers.append("recovery_gate")
    if not real_provider_validated:
        blockers.append("real_provider_validation")
    return ReleaseDecision(
        allowed=not blockers,
        release_owner_role="release_owner",
        security_approver_role="security_approver",
        ops_oncall_role="ops_oncall",
        blockers=tuple(blockers),
        application_image=application_image,
        configuration_version=configuration_version,
        database_revision=database_revision,
        index_version=index_version,
    )
