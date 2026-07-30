"""Static import-direction checks for the Phase 01 package skeleton."""

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[3] / "src" / "ragflow_agent"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_shared_foundation_does_not_depend_on_outer_layers() -> None:
    forbidden = (
        "ragflow_agent.api",
        "ragflow_agent.bootstrap",
        "ragflow_agent.infrastructure",
        "ragflow_agent.worker",
    )
    violations: list[str] = []
    for path in (PACKAGE_ROOT / "shared").rglob("*.py"):
        for imported in _imports(path):
            if imported.startswith(forbidden):
                violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {imported}")
    assert violations == []


def test_infrastructure_does_not_import_process_entrypoints() -> None:
    forbidden = ("ragflow_agent.api", "ragflow_agent.bootstrap", "ragflow_agent.worker")
    violations: list[str] = []
    for path in (PACKAGE_ROOT / "infrastructure").rglob("*.py"):
        for imported in _imports(path):
            if imported.startswith(forbidden):
                violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {imported}")
    assert violations == []


def test_worker_does_not_import_api_routes_or_internal_http_clients() -> None:
    forbidden = ("ragflow_agent.api", "fastapi", "httpx", "httpx2")
    violations: list[str] = []
    worker_roots = [PACKAGE_ROOT / "worker", PACKAGE_ROOT / "bootstrap" / "ingestion_worker.py"]
    for root in worker_roots:
        paths = root.rglob("*.py") if root.is_dir() else [root]
        for path in paths:
            for imported in _imports(path):
                if imported.startswith(forbidden):
                    violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {imported}")
    assert violations == []
