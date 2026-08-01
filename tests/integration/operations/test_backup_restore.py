from datetime import UTC, datetime
from pathlib import Path

import pytest

from ragflow_agent.operations.backup import create_backup, restore_backup


def test_isolated_backup_restore_validates_hashes_and_refuses_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "authority"
    source.mkdir()
    (source / "postgres.dump").write_text("tenant-a metadata", encoding="utf-8")
    (source / "minio").mkdir()
    (source / "minio" / "document.txt").write_text("synthetic document", encoding="utf-8")
    (source / "checkpoint.json").write_text('{"run":"r1"}', encoding="utf-8")
    (source / "memory.json").write_text('{"consent":true}', encoding="utf-8")
    backup = tmp_path / "backup"
    manifest = create_backup(source, backup, created_at=datetime(2026, 8, 1, tzinfo=UTC))
    assert len(manifest.entries) == 4
    restored = tmp_path / "restored"
    restored_manifest = restore_backup(backup, restored)
    assert restored_manifest == manifest
    assert (restored / "postgres.dump").read_text(encoding="utf-8") == "tenant-a metadata"
    with pytest.raises(ValueError, match="empty"):
        restore_backup(backup, restored)


def test_tampered_backup_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "authority"
    source.mkdir()
    (source / "postgres.dump").write_text("original", encoding="utf-8")
    backup = tmp_path / "backup"
    create_backup(source, backup, created_at=datetime(2026, 8, 1, tzinfo=UTC))
    (backup / "payload" / "postgres.dump").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="failed validation"):
        restore_backup(backup, tmp_path / "restored")
