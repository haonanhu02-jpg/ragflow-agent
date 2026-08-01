from ragflow_agent.operations.release import decide_release


def test_release_is_blocked_without_real_provider_validation() -> None:
    decision = decide_release(
        application_image="sha256:synthetic",
        configuration_version="production-v1",
        database_revision="20260801_0006",
        index_version="index-v1",
        quality_gate_passed=True,
        security_gate_passed=True,
        recovery_gate_passed=True,
        real_provider_validated=False,
    )
    assert not decision.allowed
    assert decision.blockers == ("real_provider_validation",)
    assert decision.release_owner_role != decision.security_approver_role
