from ragflow_agent.operations.verification import (
    FAULT_SCENARIOS,
    build_release_report,
    run_isolated_operations_drill,
)


def test_operations_drill_covers_recovery_faults_and_capacity() -> None:
    report = run_isolated_operations_drill()
    backup = report["backup_restore"]
    faults = report["fault_drills"]
    performance = report["performance"]
    assert isinstance(backup, dict) and backup["restored_content_matches"] is True
    assert isinstance(faults, list) and {item["scenario"] for item in faults} == set(
        FAULT_SCENARIOS
    )
    assert all(item["detected"] and item["recovered"] for item in faults)
    assert isinstance(performance, dict) and performance["backpressure_observed"] is True
    assert performance["production_capacity_proven"] is False


def test_release_report_marks_verified_local_or_self_managed_scope_ready() -> None:
    operations = run_isolated_operations_drill()
    report = build_release_report(
        evaluation={"release_gate": {"passed": True}},
        governance={"passed": True},
        operations=operations,
        commit="test-commit",
    )
    assert report["production_exit"] == "local_or_self_managed_ready"
    assert report["completion_status"] == "completed"
    blockers = report["decision_model_blockers"]
    assert isinstance(blockers, tuple)
    assert blockers == ()
    runtime_requirements = report["runtime_requirements"]
    assert isinstance(runtime_requirements, tuple)
    assert "user_supplied_chat_model_configuration" in runtime_requirements
    optional_extensions = report["optional_future_extensions"]
    assert isinstance(optional_extensions, tuple)
    assert "authenticated_docker_scout_scan" in optional_extensions
    assert report["intentional_scope_choices"] == ("project_top_level_license_absent",)
    assert report["scope"] == {
        "agent_rag_backend_source": "completed",
        "local_or_self_managed_deployment": "ready",
        "provider_runtime_configuration": "operator_supplied",
        "ui_admin_console": "deferred_not_required",
    }
