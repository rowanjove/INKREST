"""Install and uninstall ZIP-distributed plugins."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.logging_config import get_logger
from novel_agent.plugins.manifest import (
    find_manifest_path,
    load_manifest,
    validate_manifest,
    ManifestError,
)

logger = get_logger("plugins.installer")

MAX_ZIP_BYTES = 20 * 1024 * 1024
INSTALL_RECORD = ".inkrest-install.json"


def _plugins_dir(root_dir: Path) -> Path:
    return Path(root_dir) / "plugins"


def _safe_join(base: Path, *parts: str) -> Path:
    target = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError:
        raise ManifestError("非法路径（禁止跳出插件目录）")
    return target


def _normalize_zip_root(staging: Path) -> Path:
    """If zip has single top-level folder, use it as plugin root."""
    entries = [p for p in staging.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir() and not find_manifest_path(staging):
        return entries[0]
    return staging


def _extract_zip_safe(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.endswith("/"):
                continue
            if ".." in name.split("/"):
                raise ManifestError(f"ZIP 含非法路径: {name}")
            target = _safe_join(dest, *name.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def _extract_nested_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inkrest-bundle-") as tmp:
        tmp_path = Path(tmp)
        _extract_zip_safe(zip_path, tmp_path)
        for item in tmp_path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(tmp_path)
                out = _safe_join(dest, *rel.parts)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, out)


def _apply_extract_rules(plugin_root: Path, rules: List[Any]) -> List[str]:
    written: List[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        src_rel = str(rule.get("from") or "").strip().replace("\\", "/")
        to_rel = str(rule.get("to") or "").strip().replace("\\", "/")
        if not src_rel or not to_rel:
            continue
        src = _safe_join(plugin_root, *src_rel.split("/"))
        dest = _safe_join(plugin_root, *to_rel.split("/"))
        if not src.exists():
            logger.warning("extract 源不存在: %s", src_rel)
            continue
        if src.suffix.lower() == ".zip" and src.is_file():
            _extract_nested_zip(src, dest)
        elif src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        written.append(str(dest.relative_to(plugin_root)))
    return written


def _apply_bundles(plugin_root: Path, bundles: List[str]) -> List[str]:
    written: List[str] = []
    for rel in bundles:
        rel = rel.replace("\\", "/")
        bundle_path = _safe_join(plugin_root, *rel.split("/"))
        if not bundle_path.is_file() or bundle_path.suffix.lower() != ".zip":
            logger.warning("bundle 非 zip 文件: %s", rel)
            continue
        name = bundle_path.stem
        dest = _safe_join(plugin_root, "data", name)
        _extract_nested_zip(bundle_path, dest)
        written.append(str(dest.relative_to(plugin_root)))
    return written


def _collect_files(root: Path) -> List[str]:
    files: List[str] = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(files)


def _parse_version(ver: str) -> Tuple[int, ...]:
    parts: List[int] = []
    for piece in str(ver).split("."):
        m = re.match(r"(\d+)", piece)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts or [0])


def install_plugin_zip(root_dir: Path, zip_bytes: bytes, *, replace: bool = False) -> Dict[str, Any]:
    """Validate and install a plugin archive into plugins/<id>/."""
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ManifestError(f"ZIP 超过大小上限（{MAX_ZIP_BYTES // 1024 // 1024}MB）")

    plugins_root = _plugins_dir(root_dir)
    plugins_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="inkrest-plugin-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(zip_bytes)
        staging = tmp_path / "staging"
        _extract_zip_safe(zip_path, staging)
        plugin_src = _normalize_zip_root(staging)
        manifest = load_manifest(plugin_src)
        plugin_id = manifest["id"]
        target = plugins_root / plugin_id

        if target.exists():
            if not replace:
                record_path = target / INSTALL_RECORD
                old_ver = "0.0.0"
                if record_path.is_file():
                    try:
                        old_ver = json.loads(record_path.read_text(encoding="utf-8")).get(
                            "version", old_ver
                        )
                    except (json.JSONDecodeError, OSError):
                        pass
                if _parse_version(manifest["version"]) <= _parse_version(old_ver):
                    raise ManifestError(
                        f"已安装 {plugin_id} v{old_ver}，新包 v{manifest['version']} 未更高"
                    )
            shutil.rmtree(target)

        shutil.copytree(plugin_src, target)
        bundle_files = _apply_bundles(target, manifest.get("bundles") or [])
        extract_files = _apply_extract_rules(target, manifest.get("extract") or [])
        all_files = _collect_files(target)

        install_record = {
            "id": plugin_id,
            "version": manifest["version"],
            "installed_files": all_files,
            "bundle_targets": bundle_files,
            "extract_targets": extract_files,
        }
        (target / INSTALL_RECORD).write_text(
            json.dumps(install_record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "id": plugin_id,
        "version": manifest["version"],
        "display_name": manifest.get("display_name") or plugin_id,
        "plugin_type": manifest.get("plugin_type"),
        "trusted": False,
        "message": "插件已安装，请在列表中信任并启用后生效。",
    }


def uninstall_plugin(root_dir: Path, plugin_id: str) -> bool:
    """Remove plugin directory and registry entry (caller updates yaml)."""
    target = _plugins_dir(root_dir) / plugin_id
    if not target.exists():
        legacy_py = _plugins_dir(root_dir) / f"{plugin_id}.py"
        if legacy_py.is_file():
            legacy_py.unlink()
            return True
        return False
    shutil.rmtree(target)
    return True


def read_install_record(plugin_dir: Path) -> Dict[str, Any]:
    path = plugin_dir / INSTALL_RECORD
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}
