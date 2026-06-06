"""inkrest.plugin.json manifest parsing and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.plugins.base import PluginType

MANIFEST_FILENAMES = ("inkrest.plugin.json", "plugin.json")
PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
CORE_VERSION = "1.0.0"
VALID_PLUGIN_TYPES = {t.value for t in PluginType}


class ManifestError(ValueError):
    pass


def find_manifest_path(plugin_root: Path) -> Optional[Path]:
    root = Path(plugin_root)
    for name in MANIFEST_FILENAMES:
        path = root / name
        if path.is_file():
            return path
    return None


def load_manifest(plugin_root: Path) -> Dict[str, Any]:
    path = find_manifest_path(plugin_root)
    if not path:
        raise ManifestError(f"缺少清单文件（{', '.join(MANIFEST_FILENAMES)}）")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ManifestError(f"清单解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("清单必须是 JSON 对象")
    return validate_manifest(data, plugin_root)


def validate_manifest(data: Dict[str, Any], plugin_root: Path) -> Dict[str, Any]:
    pid = str(data.get("id") or data.get("name") or "").strip()
    if not pid or not PLUGIN_ID_RE.match(pid):
        raise ManifestError(
            "id 必填，且须为小写字母开头的 2–64 位标识（字母/数字/_/-）"
        )

    ptype = str(data.get("plugin_type") or "").strip()
    if ptype not in VALID_PLUGIN_TYPES:
        raise ManifestError(f"plugin_type 无效: {ptype}")

    version = str(data.get("version") or "0.1.0").strip()
    entry = str(data.get("entry") or "plugin:PLUGIN_CLASS").strip()
    if not entry:
        raise ManifestError("entry 不能为空")

    min_core = str(data.get("min_core_version") or "0.1.0").strip()
    if _version_tuple(min_core) > _version_tuple(CORE_VERSION):
        raise ManifestError(
            f"插件要求核心版本 {min_core}，当前为 {CORE_VERSION}"
        )

    requires = data.get("requires") or []
    if not isinstance(requires, list):
        raise ManifestError("requires 必须是字符串数组")
    requires = [str(r).strip() for r in requires if str(r).strip()]

    capabilities = data.get("capabilities") or []
    if not isinstance(capabilities, list):
        capabilities = []
    capabilities = [str(c).strip() for c in capabilities if str(c).strip()]

    extract_rules = data.get("extract") or []
    bundles = data.get("bundles") or []
    if not isinstance(extract_rules, list):
        raise ManifestError("extract 必须是数组")
    if not isinstance(bundles, list):
        raise ManifestError("bundles 必须是字符串数组")

    _validate_entry_path(plugin_root, entry)

    normalized = {
        "id": pid,
        "name": pid,
        "version": version,
        "display_name": str(data.get("display_name") or pid),
        "description": str(data.get("description") or ""),
        "author": str(data.get("author") or ""),
        "icon": str(data.get("icon") or ""),
        "plugin_type": ptype,
        "entry": entry,
        "min_core_version": min_core,
        "requires": requires,
        "capabilities": capabilities,
        "config_schema": data.get("config_schema") if isinstance(data.get("config_schema"), dict) else {},
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "extract": extract_rules,
        "bundles": [str(b).strip() for b in bundles if str(b).strip()],
        "digest": str(data.get("digest") or "").strip(),
    }
    return normalized


def _validate_entry_path(plugin_root: Path, entry: str) -> None:
    if entry.startswith("plugin:"):
        class_name = entry.split(":", 1)[1].strip()
        if not class_name:
            raise ManifestError("entry plugin: 后须指定类名")
        candidates = [plugin_root / "plugin.py", plugin_root / "__init__.py"]
        if not any(p.is_file() for p in candidates):
            raise ManifestError("entry 为 plugin: 时须存在 plugin.py 或 __init__.py")
        return
    if entry.startswith("package:"):
        rest = entry.split(":", 1)[1]
        parts = rest.rsplit(":", 1)
        if len(parts) != 2:
            raise ManifestError("entry package: 格式应为 package:模块路径:类名")
        mod_path, class_name = parts[0].strip(), parts[1].strip()
        if not mod_path or not class_name:
            raise ManifestError("entry package: 模块与类名均必填")
        rel = Path(*mod_path.split("."))
        py_file = plugin_root / f"{rel}.py"
        pkg_init = plugin_root / rel / "__init__.py"
        if not py_file.is_file() and not pkg_init.is_file():
            raise ManifestError(f"entry 指向的模块不存在: {mod_path}")
        return
    raise ManifestError("entry 须以 plugin: 或 package: 开头")


def manifest_to_plugin_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    """UI/API friendly dict from validated manifest."""
    return {
        "name": data["id"],
        "display_name": data.get("display_name") or data["id"],
        "version": data.get("version") or "0.1.0",
        "description": data.get("description") or "",
        "author": data.get("author") or "",
        "icon": data.get("icon") or "",
        "plugin_type": data.get("plugin_type") or "",
        "requires": data.get("requires") or [],
        "min_core_version": data.get("min_core_version") or "0.1.0",
        "config_schema": data.get("config_schema") or {},
        "capabilities": data.get("capabilities") or [],
        "tags": data.get("tags") or [],
    }


def _version_tuple(ver: str) -> Tuple[int, ...]:
    parts: List[int] = []
    for piece in str(ver).strip().split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts or [0])