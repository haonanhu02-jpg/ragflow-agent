import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

_SCRIPT = Path(__file__).parents[3] / "scripts" / "check_repository_governance.py"
scan_repository = cast(
    Callable[[Path], dict[str, object]],
    runpy.run_path(str(_SCRIPT))["scan_repository"],
)


def test_repository_governance_scan_passes_and_records_intentional_license_absence() -> None:
    report = scan_repository(Path.cwd())
    assert report["passed"] is True
    assert report["ragflow_source_copied"] is False
    assert report["third_party_source_vendored"] is False
    assert report["project_license_policy"] == "intentionally_absent"
    assert report["project_license_required_for_completion"] is False
    assert report["project_license_file_present"] is False
