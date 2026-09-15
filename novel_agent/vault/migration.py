"""Legacy workspace migration to Default Local Vault (Milestone A).

Ensures existing users seamlessly upgrade without losing projects,
without manual configuration, and with zero downtime or data loss.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import List, Optional

from novel_agent.vault.manager import VaultManager
from novel_agent.vault.models import VaultMetadata, now_iso


def migrate_legacy_workspace(
    root_dir: Path, vault_manager: Optional[VaultManager] = None
) -> Optional[VaultMetadata]:
    """Scan root_dir for unpartitioned legacy projects and migrate into Default Local Vault."""
    root = Path(root_dir).resolve()
    mgr = vault_manager or VaultManager(root)

    # If vaults already exist and default vault is present, check if legacy migration was done
    migration_marker = mgr.global_dir / "migration.json"
    default_vault = mgr.get_default_vault()

    legacy_projects_dir = root / "projects"
    has_legacy_projects = (
        legacy_projects_dir.is_dir()
        and any(legacy_projects_dir.iterdir())
    )

    if not has_legacy_projects and default_vault:
        return default_vault

    if not default_vault:
        # Create Default Local Vault (no PIN by default for zero-friction upgrade)
        default_vault, _ = mgr.create_vault(
            name="默认创作空间",
            pin=None,
            is_default=True,
        )

    migrated_projects: List[str] = []
    if has_legacy_projects:
        vault_projects_dir = mgr.get_projects_dir(default_vault.vault_id)

        for item in legacy_projects_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                target_dir = vault_projects_dir / item.name
                if not target_dir.exists():
                    # Copy tree to preserve original while populating vault
                    shutil.copytree(str(item), str(target_dir))
                    migrated_projects.append(item.name)

        # Update registry.db
        registry_path = mgr._vault_dir(default_vault.vault_id) / "registry.db"
        if registry_path.exists() and migrated_projects:
            conn = sqlite3.connect(registry_path)
            try:
                conn.execute(
                    """
                    create table if not exists registered_projects (
                        project_name text primary key,
                        migrated_at text not null
                    )
                    """
                )
                for p_name in migrated_projects:
                    conn.execute(
                        "insert or ignore into registered_projects (project_name, migrated_at) values (?, ?)",
                        (p_name, now_iso()),
                    )
                conn.commit()
            finally:
                conn.close()

    # Record migration log
    migration_marker.write_text(
        json.dumps(
            {
                "migrated_at": now_iso(),
                "default_vault_id": default_vault.vault_id,
                "migrated_projects": migrated_projects,
                "status": "success",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return default_vault
