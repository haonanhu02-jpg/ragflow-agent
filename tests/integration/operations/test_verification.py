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


def test_release_report_is_fail_closed_without_external_production_evidence() -> None:
    operations = run_isolated_operations_drill()
    report = build_release_report(
        evaluation={"release_gate": {"passed": True}},
        governance={"passed": True},
        operations=operations,
        commit="test-commit",
    )
    assert report["production_exit"] == "not_allowed"
    blockers = report["external_release_blockers"]
    assert isinstance(blockers, tuple)
    assert "real_provider_validation" in blockers
    assert "authenticated_image_vulnerability_scan" in blockers
    assert report["scope"] == {
        "backend_api_worker_evaluation_candidate": "implemented",
        "ui_admin_console": "deferred_not_implemented",
        "real_production_project": "not_complete",
    }
