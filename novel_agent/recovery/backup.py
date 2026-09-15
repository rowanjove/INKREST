"""Standard .inkrest-vault Backup and Verification Engine (Milestone B).

Packaging, SHA-256 integrity verification, pre-upgrade snapshots,
and safe restoration.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class BackupManifest:
    format: str = "inkrest-vault"
    format_version: int = 1
    app_version: str = "2.2.0"
    schema_version: int = 1
    crypto_version: int = 1
    created_at: str = field(default_factory=now_iso)
    vault_id: str = ""
    checksums: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "format": self.format,
            "format_version": self.format_version,
            "app_version": self.app_version,
            "schema_version": self.schema_version,
            "crypto_version": self.crypto_version,
            "created_at": self.created_at,
            "vault_id": self.vault_id,
            "checksums": self.checksums,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> BackupManifest:
        return cls(
            format=str(data.get("format", "inkrest-vault")),
            format_version=int(data.get("format_version", 1)),
            app_version=str(data.get("app_version", "2.2.0")),
            schema_version=int(data.get("schema_version", 1)),
            crypto_version=int(data.get("crypto_version", 1)),
            created_at=str(data.get("created_at", now_iso())),
            vault_id=str(data.get("vault_id", "")),
            checksums=dict(data.get("checksums", {})),  # type: ignore
        )


class BackupManager:
    """Creates, verifies, and restores standardized .inkrest-vault archives."""

    @staticmethod
    def create_backup(
        vault_dir: Path, output_file: Optional[Path] = None, vault_id: str = ""
    ) -> Path:
        vault_path = Path(vault_dir).resolve()
        backups_dir = vault_path / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = output_file or (backups_dir / f"vault_backup_{timestamp_str}.inkrest-vault")

        # Discover files to backup (excluding backups/ and cache/)
        files_to_backup: Dict[str, Path] = {}
        for root, dirs, files in vault_path.walk() if hasattr(vault_path, "walk") else _walk_compat(vault_path):
            rel_root = Path(root).relative_to(vault_path)
            # Skip backups and cache folders
            if any(part in ("backups", "cache") for part in rel_root.parts):
                continue
            for f in files:
                full_f = Path(root) / f
                if full_f.is_file():
                    rel_f = str(rel_root / f).replace("\\", "/")
                    files_to_backup[rel_f] = full_f

        # Calculate checksums
        checksums: Dict[str, str] = {}
        for rel_name, full_p in files_to_backup.items():
            checksums[rel_name] = compute_sha256(full_p)

        manifest = BackupManifest(
            vault_id=vault_id or vault_path.name,
            checksums=checksums,
        )

        temp_zip = out_path.with_suffix(".tmp")
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest.json
            zf.writestr(
                "manifest.json",
                json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            )
            # Write data files
            for rel_name, full_p in files_to_backup.items():
                zf.write(full_p, rel_name)

        temp_zip.replace(out_path)
        return out_path

    @staticmethod
    def verify_backup(backup_file: Path) -> Tuple[bool, str]:
        path = Path(backup_file)
        if not path.is_file():
            return False, f"备份文件不存在: {path}"

        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = set(zf.namelist())
                if "manifest.json" not in names:
                    return False, "缺少 manifest.json，不是合法的 .inkrest-vault 格式"

                manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
                manifest = BackupManifest.from_dict(manifest_data)
                if manifest.format != "inkrest-vault":
                    return False, f"不支持的备份格式: {manifest.format}"

                # Verify each file's checksum
                for rel_name, expected_sha in manifest.checksums.items():
                    if rel_name not in names:
                        return False, f"备份文件缺失内容项: {rel_name}"
                    content = zf.read(rel_name)
                    actual_sha = hashlib.sha256(content).hexdigest()
                    if actual_sha != expected_sha:
                        return False, f"校验和不匹配: {rel_name} (数据可能损坏)"

            return True, "备份校验和完全一致，验证成功"
        except Exception as exc:
            return False, f"备份文件解析失败: {exc}"

    @staticmethod
    def restore_backup(
        backup_file: Path, target_dir: Path, pre_snapshot: bool = True
    ) -> Tuple[bool, str]:
        valid, msg = BackupManager.verify_backup(backup_file)
        if not valid:
            return False, f"恢复失败：备份文件校验未通过 ({msg})"

        target_path = Path(target_dir).resolve()
        target_path.mkdir(parents=True, exist_ok=True)

        if pre_snapshot and any(target_path.iterdir()):
            BackupManager.create_pre_upgrade_snapshot(target_path)

        try:
            with zipfile.ZipFile(backup_file, "r") as zf:
                for member in zf.infolist():
                    if member.filename == "manifest.json":
                        continue
                    zf.extract(member, target_path)
            return True, "恢复完成"
        except Exception as exc:
            return False, f"恢复解压失败: {exc}"

    @staticmethod
    def create_pre_upgrade_snapshot(vault_dir: Path) -> Path:
        """Create a pre-upgrade safety snapshot."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_file = vault_dir / "backups" / f"pre_upgrade_snapshot_{timestamp_str}.inkrest-vault"
        return BackupManager.create_backup(vault_dir, snapshot_file)


def _walk_compat(path: Path):
    import os
    for root, dirs, files in os.walk(str(path)):
        yield root, dirs, files
