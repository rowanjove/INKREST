"""Unit tests for VaultManager lifecycle, isolation, and legacy migration."""

from pathlib import Path
import sqlite3

from novel_agent.vault.manager import VaultManager
from novel_agent.vault.migration import migrate_legacy_workspace
from novel_agent.vault.models import VaultStatus


def test_vault_creation_and_physical_isolation(tmp_path: Path):
    mgr = VaultManager(tmp_path)

    v1, _ = mgr.create_vault(name="空间一", is_default=True)
    v2, _ = mgr.create_vault(name="空间二", is_default=False)

    assert v1.vault_id != v2.vault_id
    assert v1.is_default is True
    assert v2.is_default is False

    # Check physical directory isolation
    dir1 = mgr.get_projects_dir(v1.vault_id)
    dir2 = mgr.get_projects_dir(v2.vault_id)
    assert dir1 != dir2
    assert dir1.is_dir()
    assert dir2.is_dir()

    # List vaults
    vaults = mgr.list_vaults()
    assert len(vaults) == 2
    ids = {v.vault_id for v in vaults}
    assert v1.vault_id in ids and v2.vault_id in ids

    # Default vault lookup
    def_vault = mgr.get_default_vault()
    assert def_vault is not None
    assert def_vault.vault_id == v1.vault_id


def test_pin_protection_and_recovery_flow(tmp_path: Path):
    mgr = VaultManager(tmp_path)

    v, rec_key = mgr.create_vault(name="加密空间", pin="123456")
    assert v.pin_enabled is True
    assert rec_key is not None
    assert rec_key.startswith("IRK-")

    # Initially locked
    assert mgr.get_vault_status(v.vault_id) == VaultStatus.LOCKED
    assert mgr.get_vault_key(v.vault_id) is None

    # Unlock with wrong PIN
    assert mgr.unlock_vault(v.vault_id, "wrong") is False
    assert mgr.get_vault_status(v.vault_id) == VaultStatus.LOCKED

    # Unlock with correct PIN
    assert mgr.unlock_vault(v.vault_id, "123456") is True
    assert mgr.get_vault_status(v.vault_id) == VaultStatus.UNLOCKED
    key1 = mgr.get_vault_key(v.vault_id)
    assert key1 is not None and len(key1) == 32

    # Lock vault
    mgr.lock_vault(v.vault_id)
    assert mgr.get_vault_status(v.vault_id) == VaultStatus.LOCKED
    assert mgr.get_vault_key(v.vault_id) is None

    # Unlock with recovery key
    assert mgr.unlock_with_recovery_key(v.vault_id, rec_key) is True
    assert mgr.get_vault_status(v.vault_id) == VaultStatus.UNLOCKED
    key2 = mgr.get_vault_key(v.vault_id)
    assert key2 == key1

    # Change PIN
    assert mgr.change_pin(v.vault_id, old_pin="123456", new_pin="654321") is True
    mgr.lock_vault(v.vault_id)

    # Old PIN fails, new PIN succeeds
    assert mgr.unlock_vault(v.vault_id, "123456") is False
    assert mgr.unlock_vault(v.vault_id, "654321") is True
    assert mgr.get_vault_key(v.vault_id) == key1


def test_legacy_workspace_migration(tmp_path: Path):
    # Setup mock legacy workspace
    legacy_projects_dir = tmp_path / "projects"
    novel_dir = legacy_projects_dir / "my_epic_novel"
    novel_dir.mkdir(parents=True)
    db_file = novel_dir / "project.db"

    conn = sqlite3.connect(db_file)
    try:
        conn.execute("create table documents (id text primary key, title text)")
        conn.execute("insert into documents values ('doc-1', '第一章 启程')")
        conn.commit()
    finally:
        conn.close()

    # Run migration
    default_vault = migrate_legacy_workspace(tmp_path)
    assert default_vault is not None
    assert default_vault.is_default is True
    assert default_vault.name == "默认创作空间"

    # Verify project exists in new isolated vault directory
    mgr = VaultManager(tmp_path)
    vault_project_dir = mgr.get_projects_dir(default_vault.vault_id) / "my_epic_novel"
    assert vault_project_dir.is_dir()
    migrated_db = vault_project_dir / "project.db"
    assert migrated_db.is_file()

    # Verify data intact
    check_conn = sqlite3.connect(migrated_db)
    try:
        row = check_conn.execute("select title from documents where id='doc-1'").fetchone()
        assert row[0] == "第一章 启程"
    finally:
        check_conn.close()

    # Idempotent second run
    vault_again = migrate_legacy_workspace(tmp_path, mgr)
    assert vault_again.vault_id == default_vault.vault_id
