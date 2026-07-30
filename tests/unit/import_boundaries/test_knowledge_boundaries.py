"""Static Phase 03 knowledge dependency-direction checks."""

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[3] / "src" / "ragflow_agent"
KNOWLEDGE_ROOT = PACKAGE_ROOT / "knowledge"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_knowledge_domain_and_ports_do_not_import_frameworks_or_outer_layers() -> None:
    forbidden = (
        "boto3",
        "fastapi",
        "langchain",
        "langgraph",
        "redis",
        "sqlalchemy",
        "ragflow_agent.agent",
        "ragflow_agent.api",
        "ragflow_agent.bootstrap",
        "ragflow_agent.infrastructure",
        "ragflow_agent.worker",
    )
    violations: list[str] = []
    for root in (KNOWLEDGE_ROOT / "domain", KNOWLEDGE_ROOT / "ports"):
        for path in root.rglob("*.py"):
            for imported in _imports(path):
                if imported.startswith(forbidden):
                    violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {imported}")
    assert violations == []


def test_knowledge_application_does_not_import_adapters_or_process_entrypoints() -> None:
    forbidden = (
        "ragflow_agent.agent",
        "ragflow_agent.api",
        "ragflow_agent.bootstrap",
        "ragflow_agent.infrastructure",
        "ragflow_agent.knowledge.infrastructure",
        "ragflow_agent.worker",
    )
    violations: list[str] = []
    for path in (KNOWLEDGE_ROOT / "application").rglob("*.py"):
        for imported in _imports(path):
            if imported.startswith(forbidden):
                violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {imported}")
    assert violations == []
