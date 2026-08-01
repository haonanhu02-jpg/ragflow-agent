"""Repeatable isolated operations drill and production-exit report generator."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from ragflow_agent.operations.backup import create_backup, restore_backup
from ragflow_agent.operations.faults import exercise_fault
from ragflow_agent.operations.performance import summarize_performance
from ragflow_agent.operations.release import decide_release

FAULT_SCENARIOS = (
    "postgres_unavailable",
    "redis_unavailable",
    "minio_unavailable",
    "elasticsearch_unavailable",
    "worker_killed",
    "provider_timeout",
    "network_interrupted",
    "checkpoint_failed",
    "dlq_backlog",
)


def run_isolated_operations_drill() -> dict[str, object]:
    """Exercise hash-checked restore and deterministic fault/capacity paths."""
    with tempfile.TemporaryDirectory(prefix="ragflow-agent-phase10-") as temporary:
        root = Path(temporary)
        source = root / "authority"
        source.mkdir()
        payloads = {
            "postgres.dump": "synthetic tenant, checkpoint and memory rows",
            "minio-manifest.json": '{"objects":["synthetic/document"]}',
            "configuration.json": '{"version":"production-candidate-v1"}',
        }
        for relative, content in payloads.items():
            (source / relative).write_text(content, encoding="utf-8")
        started = perf_counter()
        manifest = create_backup(
            source,
            root / "backup",
            created_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        restored = root / "restored"
        restore_backup(root / "backup", restored)
        elapsed = perf_counter() - started
        restore_matches = all(
            (restored / relative).read_text(encoding="utf-8") == content
            for relative, content in payloads.items()
        )

    fault_results = []
    for scenario in FAULT_SCENARIOS:
        def inject(current: str = scenario) -> None:
            raise TimeoutError(current)

        fault_results.append(
            exercise_fault(scenario, inject=inject, recover=lambda: True, elapsed_seconds=1.0)
        )
    performance = summarize_performance(
        tuple(float(value) for value in range(1, 101)),
        errors=0,
        max_concurrency=32,
        backpressure_observed=True,
    )
    return {
        "schema_version": 1,
        "test_mode": "deterministic_and_isolated_local",
        "backup_restore": {
            "entries": len(manifest.entries),
            "hashes_validated": True,
            "empty_target_enforced": True,
            "restored_content_matches": restore_matches,
            "elapsed_seconds": elapsed,
            "rpo_hours_target": 24,
            "rto_hours_target": 4,
            "production_restore_proven": False,
        },
        "fault_drills": [
            {
                "scenario": item.scenario,
                "detected": item.detected,
                "recovered": item.recovered,
                "data_loss": item.data_loss,
                "elapsed_seconds": item.elapsed_seconds,
                "mode": "safe_fault_injection",
            }
            for item in fault_results
        ],
        "performance": {
            "sample_count": performance.sample_count,
            "p95_ms": performance.p95_ms,
            "error_rate": performance.error_rate,
            "max_concurrency": performance.max_concurrency,
            "backpressure_observed": performance.backpressure_observed,
            "cost_status": performance.cost_status,
            "production_capacity_proven": False,
        },
    }


def build_release_report(
    *,
    evaluation: dict[str, object],
    governance: dict[str, object],
    operations: dict[str, object],
    commit: str,
) -> dict[str, object]:
    """Return a fail-closed release report without upgrading local evidence."""
    evaluation_gate = evaluation.get("release_gate")
    quality_gate_passed = bool(
        isinstance(evaluation_gate, dict) and evaluation_gate.get("passed") is True
    )
    security_gate_passed = governance.get("passed") is True
    backup_restore = operations.get("backup_restore")
    recovery_gate_passed = bool(
        isinstance(backup_restore, dict)
        and backup_restore.get("restored_content_matches") is True
    )
    decision = decide_release(
        application_image=f"ragflow-agent:production-candidate@{commit}",
        configuration_version="production-candidate-v1",
        database_revision="20260801_0006",
        index_version="phase09-v1",
        quality_gate_passed=quality_gate_passed,
        security_gate_passed=security_gate_passed,
        recovery_gate_passed=recovery_gate_passed,
        real_provider_validated=False,
    )
    external_blockers = (
        "real_provider_validation",
        "project_license_declaration",
        "authenticated_image_vulnerability_scan",
        "production_credentials_and_idp",
        "representative_business_data_evaluation",
        "authorized_production_deployment",
        "sustained_monthly_slo_evidence",
        "isolated_production_backup_restore_evidence",
        "production_security_and_capacity_validation",
    )
    return {
        "schema_version": 1,
        "phase": "10",
        "production_exit": "not_allowed",
        "local_production_candidate_gates": {
            "quality": quality_gate_passed,
            "security": security_gate_passed,
            "isolated_recovery": recovery_gate_passed,
        },
        "decision_model_blockers": decision.blockers,
        "external_release_blockers": external_blockers,
        "artifacts": {
            "application_image": decision.application_image,
            "configuration_version": decision.configuration_version,
            "database_revision": decision.database_revision,
            "index_version": decision.index_version,
        },
        "roles": {
            "release_owner": decision.release_owner_role,
            "security_approver": decision.security_approver_role,
            "ops_oncall": decision.ops_oncall_role,
        },
        "scope": {
            "backend_api_worker_evaluation_candidate": "implemented",
            "ui_admin_console": "deferred_not_implemented",
            "real_production_project": "not_complete",
        },
    }


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--governance", type=Path, required=True)
    parser.add_argument("--operations-output", type=Path, required=True)
    parser.add_argument("--release-output", type=Path, required=True)
    parser.add_argument("--commit", default="working-tree")
    args = parser.parse_args()
    operations = run_isolated_operations_drill()
    _write_json(args.operations_output, operations)
    release = build_release_report(
        evaluation=_read_json(args.evaluation),
        governance=_read_json(args.governance),
        operations=operations,
        commit=args.commit,
    )
    _write_json(args.release_output, release)


if __name__ == "__main__":
    main()
