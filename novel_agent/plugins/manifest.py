"""inkrest.plugin.json manifest parsing and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.plugins.base import PluginType
from novel_agent.plugins.permissions import (
    effective_capabilities,
    validate_declared_capabilities,
)

MANIFEST_FILENAMES = ("inkrest.plugin.json", "plugin.json")
PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
CORE_VERSION = "1.0.0"
VALID_PLUGIN_TYPES = {t.value for t in PluginType}
LEGACY_CAPABILITY_MARKERS = {"hooks"}

CONTRIBUTION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,47}$")
VALID_SURFACES = {"library_sidebar", "project_sidebar"}
VALID_VISIBILITIES = {"visible", "collapsed", "hidden"}
ALLOWED_NAVIGATION_ICONS = {
    "library",
    "create",
    "overview",
    "planning",
    "manuscript",
    "production",
    "quality",
    "publishing",
    "settings",
    "extensions",
    "collection",
    "document",
    "inspection",
    "radar",
    "chart",
    "tools",
    "sparkles",
    "folder",
    "cpu",
    "edit",
    "list",
}
MAX_CONTRIBUTIONS_PER_SURFACE = 2


class ManifestError(ValueError):
    pass


_VIEW_HTML_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,120}\.html$")


def _validate_view_html(plugin_root: Path, html_rel: str) -> str:
    relative = str(html_rel or "").strip()
    if not relative:
        return ""
    if ".." in relative or "\\" in relative or relative.startswith("/"):
        raise ManifestError(f"导航视图 html 路径不合法: '{relative}'")
    if not _VIEW_HTML_RE.fullmatch(relative):
        raise ManifestError(
            f"导航视图 html 必须是插件目录内的 .html 相对路径: '{relative}'"
        )
    html_path = (Path(plugin_root) / relative).resolve()
    root = Path(plugin_root).resolve()
    if html_path != root and root not in html_path.parents:
        raise ManifestError(f"导航视图 html 超出插件目录: '{relative}'")
    if not html_path.is_file():
        raise ManifestError(f"导航视图 html 不存在: '{relative}'")
    return relative.replace("\\", "/")


def _validate_contributes(
    raw: Any, capabilities: List[str], plugin_root: Path
) -> Dict[str, Any]:
    if raw is None:
        return {"navigation": [], "commands": []}
    if not isinstance(raw, dict):
        raise ManifestError("contributes 必须是 JSON 对象")

    nav_raw = raw.get("navigation") or []
    if not isinstance(nav_raw, list):
        raise ManifestError("contributes.navigation 必须是数组")

    normalized_nav: List[Dict[str, Any]] = []
    seen_ids = set()
    surface_counts: Dict[str, int] = {}
    effective_cap_set = set(capabilities)

    for item in nav_raw:
        if not isinstance(item, dict):
            raise ManifestError("navigation 贡献项必须是对象")

        cid = str(item.get("id") or "").strip()
        if not cid or not CONTRIBUTION_ID_RE.match(cid):
            raise ManifestError(
                f"导航贡献项 id 无效: '{cid}'，必须为小写字母开头的 2–48 位标识（小写字母/数字/-）"
            )
        if cid in seen_ids:
            raise ManifestError(f"导航贡献项 id 重复: '{cid}'")
        seen_ids.add(cid)

        title = str(item.get("title") or "").strip()
        if len(title) < 2 or len(title) > 16 or "\n" in title or "\r" in title:
            raise ManifestError(f"导航贡献项 title 长度须在 2–16 字符之间且无换行: '{title}'")

        surface = str(item.get("surface") or "").strip()
        if surface == "both":
            raise ManifestError(
                "contributes.navigation 禁止使用 surface: 'both'，双区域插件须声明两条独立的 contribution"
            )
        if surface not in VALID_SURFACES:
            raise ManifestError(
                f"导航贡献项 surface 无效: '{surface}'，只允许 'library_sidebar' 或 'project_sidebar'"
            )

        surface_counts[surface] = surface_counts.get(surface, 0) + 1
        if surface_counts[surface] > MAX_CONTRIBUTIONS_PER_SURFACE:
            raise ManifestError(
                f"单个插件在 '{surface}' 上的导航入口不能超过 {MAX_CONTRIBUTIONS_PER_SURFACE} 个"
            )

        icon = str(item.get("icon") or "extensions").strip()
        if icon not in ALLOWED_NAVIGATION_ICONS:
            icon = "extensions"

        view = str(item.get("view") or "").strip()
        if not view or not CONTRIBUTION_ID_RE.match(view):
            raise ManifestError(f"导航贡献项 view 无效: '{view}'，须为合法内部标识")
        if any(bad in view for bad in (":", "/", "\\", "..")):
            raise ManifestError(f"导航贡献项 view 不能包含路径穿越或协议符号: '{view}'")

        order = item.get("order", 200)
        try:
            order = int(order)
        except (ValueError, TypeError):
            order = 200

        default_vis = str(item.get("default_visibility") or "visible").strip()
        if default_vis not in VALID_VISIBILITIES:
            default_vis = "visible"

        reqs = item.get("requires") or []
        if not isinstance(reqs, list):
            raise ManifestError("requires 必须是字符串数组")
        reqs_clean = [str(r).strip() for r in reqs if str(r).strip()]
        for req in reqs_clean:
            if req not in effective_cap_set:
                raise ManifestError(
                    f"导航贡献项 requires 包含未在插件 capabilities 中声明的权限: '{req}'"
                )

        normalized_nav.append({
            "id": cid,
            "title": title,
            "surface": surface,
            "icon": icon,
            "view": view,
            "html": _validate_view_html(plugin_root, str(item.get("html") or "")),
            "order": order,
            "default_visibility": default_vis,
            "requires": reqs_clean,
        })

    cmd_raw = raw.get("commands") or []
    if not isinstance(cmd_raw, list):
        raise ManifestError("contributes.commands 必须是数组")
    normalized_cmd: List[Dict[str, Any]] = []
    seen_cmd_ids = set()

    for item in cmd_raw:
        if not isinstance(item, dict):
            raise ManifestError("command 贡献项必须是对象")
        cmd_id = str(item.get("id") or "").strip()
        if not cmd_id or not CONTRIBUTION_ID_RE.match(cmd_id):
            raise ManifestError(f"命令贡献项 id 无效: '{cmd_id}'")
        if cmd_id in seen_cmd_ids:
            raise ManifestError(f"命令贡献项 id 重复: '{cmd_id}'")
        seen_cmd_ids.add(cmd_id)

        title = str(item.get("title") or "").strip()
        if not title:
            raise ManifestError(f"命令贡献项 title 不能为空: '{cmd_id}'")

        scope = str(item.get("scope") or "project").strip()
        if scope not in {"global", "project"}:
            scope = "project"

        normalized_cmd.append({
            "id": cmd_id,
            "title": title,
            "scope": scope,
        })

    return {
        "navigation": normalized_nav,
        "commands": normalized_cmd,
    }


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

    engines = data.get("engines")
    core_constraint = None
    if isinstance(engines, dict) and "inkrest" in engines:
        core_constraint = str(engines["inkrest"]).strip()
    elif "core_version" in data:
        core_constraint = str(data["core_version"]).strip()
    elif "min_core_version" in data:
        core_constraint = str(data["min_core_version"]).strip()

    if core_constraint:
        if not is_core_version_compatible(core_constraint, CORE_VERSION):
            raise ManifestError(
                f"插件要求核心版本 '{core_constraint}'，当前系统核心版本为 '{CORE_VERSION}'"
            )
    min_core = core_constraint or "0.1.0"

    requires = data.get("requires") or []
    if not isinstance(requires, list):
        raise ManifestError("requires 必须是字符串数组")
    requires = [str(r).strip() for r in requires if str(r).strip()]

    capabilities_declared = "capabilities" in data
    raw_capabilities = data.get("capabilities")
    legacy_capability_mode = bool(
        isinstance(raw_capabilities, list)
        and raw_capabilities
        and all(item in LEGACY_CAPABILITY_MARKERS for item in raw_capabilities)
    )
    if legacy_capability_mode:
        if len(raw_capabilities) != len(set(raw_capabilities)):
            raise ManifestError(f"重复插件权限: {raw_capabilities[0]}")
        declared_capabilities = []
    else:
        try:
            declared_capabilities = validate_declared_capabilities(raw_capabilities)
        except ValueError as exc:
            raise ManifestError(str(exc)) from exc
    capabilities = effective_capabilities(ptype, declared_capabilities)

    extract_rules = data.get("extract") or []
    bundles = data.get("bundles") or []
    if not isinstance(extract_rules, list):
        raise ManifestError("extract 必须是数组")
    if not isinstance(bundles, list):
        raise ManifestError("bundles 必须是字符串数组")

    _validate_entry_path(plugin_root, entry)
    contributes = _validate_contributes(data.get("contributes"), capabilities, plugin_root)

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
        "engines": engines if isinstance(engines, dict) else {"inkrest": core_constraint or f">={CORE_VERSION}"},
        "requires": requires,
        "capabilities": capabilities,
        "declared_capabilities": declared_capabilities,
        "contributes": contributes,
        "capability_mode": (
            "compatibility"
            if legacy_capability_mode
            else "explicit"
            if capabilities_declared
            else "inferred"
        ),
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
    engines = data.get("engines")
    min_core = data.get("min_core_version") or "0.1.0"
    return {
        "name": data["id"],
        "display_name": data.get("display_name") or data["id"],
        "version": data.get("version") or "0.1.0",
        "description": data.get("description") or "",
        "author": data.get("author") or "",
        "icon": data.get("icon") or "",
        "plugin_type": data.get("plugin_type") or "",
        "requires": data.get("requires") or [],
        "min_core_version": min_core,
        "engines": engines if isinstance(engines, dict) else {"inkrest": min_core},
        "config_schema": data.get("config_schema") or {},
        "capabilities": data.get("capabilities") or [],
        "declared_capabilities": data.get("declared_capabilities") or [],
        "contributes": data.get("contributes") or {"navigation": [], "commands": []},
        "capability_mode": data.get("capability_mode") or "inferred",
        "tags": data.get("tags") or [],
    }


def parse_semver_range(spec: str) -> str:
    """Normalize npm/VSCode-style SemVer range (^1.0.0, ~1.2.0, 1.0.0) into PEP-440 SpecifierSet format."""
    s = str(spec or "").strip()
    if not s or s == "*":
        return ">=0.0.0"
    if s.startswith("^"):
        v_str = s[1:].strip()
        v_tuple = _version_tuple(v_str)
        major = v_tuple[0] if len(v_tuple) > 0 else 0
        minor = v_tuple[1] if len(v_tuple) > 1 else 0
        if major > 0:
            return f">={v_str}, <{major + 1}.0.0"
        elif minor > 0:
            return f">={v_str}, <0.{minor + 1}.0"
        else:
            patch = v_tuple[2] if len(v_tuple) > 2 else 0
            return f"==0.0.{patch}"
    if s.startswith("~"):
        v_str = s[1:].strip()
        v_tuple = _version_tuple(v_str)
        major = v_tuple[0] if len(v_tuple) > 0 else 0
        minor = v_tuple[1] if len(v_tuple) > 1 else 0
        return f">={v_str}, <{major}.{minor + 1}.0"
    if not any(s.startswith(op) for op in ("<", ">", "=", "!")):
        return f">={s}"
    return s


def is_core_version_compatible(spec: str, current_version: str = CORE_VERSION) -> bool:
    """Check if current_version satisfies the SemVer / version constraint spec."""
    normalized_spec = parse_semver_range(spec)
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version
        return Version(current_version) in SpecifierSet(normalized_spec)
    except Exception:
        # Fallback to tuple comparison for simple strings
        req_tuple = _version_tuple(spec.lstrip("^~>=< "))
        curr_tuple = _version_tuple(current_version)
        if ">=" in spec or spec.startswith(("^", "~")):
            return curr_tuple >= req_tuple
        return curr_tuple >= req_tuple


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
