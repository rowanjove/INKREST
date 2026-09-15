"""Unit tests for BackupManager, .inkrest-vault format, and SHA-256 verification."""

import json
import sqlite3
import zipfile
from pathlib import Path
from novel_agent.recovery.backup import BackupManager


def test_backup_create_verify_restore(tmp_path: Path):
    vault_dir = tmp_path / "mock_vault"
    vault_dir.mkdir()
    (vault_dir / "projects" / "novel1").mkdir(parents=True)
    db_file = vault_dir / "projects" / "novel1" / "project.db"

    conn = sqlite3.connect(db_file)
    try:
        conn.execute("create table test (id int)")
        conn.execute("insert into test values (42)")
        conn.commit()
    finally:
        conn.close()

    (vault_dir / "account.json").write_text(json.dumps({"name": "Test Vault"}), encoding="utf-8")

    # 1. Create backup
    backup_file = BackupManager.create_backup(vault_dir)
    assert backup_file.is_file()
    assert backup_file.suffix == ".inkrest-vault"

    # 2. Verify backup
    valid, msg = BackupManager.verify_backup(backup_file)
    assert valid is True

    # 3. Tamper test: modify internal file without updating manifest
    tampered_file = tmp_path / "tampered.inkrest-vault"
    with zipfile.ZipFile(backup_file, "r") as src_zf:
        with zipfile.ZipFile(tampered_file, "w") as dst_zf:
            for item in src_zf.infolist():
                data = src_zf.read(item.filename)
                if item.filename == "account.json":
                    data = b'{"name": "Tampered"}'
                dst_zf.writestr(item, data)

    tampered_valid, tamper_msg = BackupManager.verify_backup(tampered_file)
    assert tampered_valid is False
    assert "校验和不匹配" in tamper_msg

    # 4. Restore to new location
    restore_dir = tmp_path / "restored_vault"
    ok, r_msg = BackupManager.restore_backup(backup_file, restore_dir, pre_snapshot=False)
    assert ok is True

    restored_db = restore_dir / "projects" / "novel1" / "project.db"
    assert restored_db.is_file()
    c2 = sqlite3.connect(restored_db)
    try:
        val = c2.execute("select id from test").fetchone()[0]
        assert val == 42
    finally:
        c2.close()
