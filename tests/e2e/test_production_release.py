from ragflow_agent.operations.release import decide_release


def test_release_allows_local_or_self_managed_deployment_without_repository_credentials() -> None:
    decision = decide_release(
        application_image="sha256:synthetic",
        configuration_version="production-v1",
        database_revision="20260801_0006",
        index_version="index-v1",
        quality_gate_passed=True,
        security_gate_passed=True,
        recovery_gate_passed=True,
    )
    assert decision.allowed
    assert decision.blockers == ()
    assert decision.release_owner_role != decision.security_approver_role


def test_release_remains_fail_closed_for_required_local_gates() -> None:
    decision = decide_release(
        application_image="sha256:synthetic",
        configuration_version="production-v1",
        database_revision="20260801_0006",
        index_version="index-v1",
        quality_gate_passed=False,
        security_gate_passed=True,
        recovery_gate_passed=True,
    )
    assert not decision.allowed
    assert decision.blockers == ("quality_gate",)
