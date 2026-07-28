"""Legacy YAML state mirror controls (SQLite is source of truth)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal

import yaml

logger = logging.getLogger("novel_agent.state.yaml_mirror")

_YAML_LIST_KEYS = ("events", "objects", "foreshadows", "hooks")
YamlMirrorMode = Literal["write", "read_only", "off"]


def resolve_yaml_mirror_mode(root_dir: Path) -> YamlMirrorMode:
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw_mode = str(runtime.get("yaml_mirror_mode") or "").strip().lower()
    if raw_mode in ("write", "read_only", "off"):
        return raw_mode  # type: ignore[return-value]
    if "yaml_mirror_enabled" in runtime:
        raw = runtime.get("yaml_mirror_enabled")
        if isinstance(raw, str):
            enabled = raw.strip().lower() not in ("0", "false", "no", "off")
        else:
            enabled = bool(raw)
        return "write" if enabled else "off"
    return "read_only"


def is_yaml_mirror_enabled(root_dir: Path) -> bool:
    """True when SQLite writes are mirrored to state/*.yaml."""
    return resolve_yaml_mirror_mode(root_dir) == "write"


def is_yaml_mirror_readable(root_dir: Path) -> bool:
    """True when legacy YAML under state/ may still be read (write or read_only)."""
    return resolve_yaml_mirror_mode(root_dir) != "off"


def _yaml_list_count(path: Path, key: str) -> int:
    if not path.is_file():
        return 0
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return -1
    if not isinstance(data, dict):
        return -1
    items = data.get(key)
    return len(items) if isinstance(items, list) else 0


def _safe_write_yaml(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _collect_yaml_mirror_lists(store: Any) -> Dict[str, List[Any]]:
    """Map legacy state/*.yaml keys to SQLite list payloads."""
    continuity = store.get_continuity_state()
    return {
        "events": store.list_events(limit=10_000),
        "objects": continuity.get("objects") or [],
        "foreshadows": continuity.get("foreshadows") or [],
        "hooks": continuity.get("hooks") or [],
    }


def export_yaml_mirror(root_dir: Path) -> Dict[str, int]:
    """Export SQLite continuity lists to state/*.yaml (on-demand, does not enable writes)."""
    from novel_agent.state.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(root_dir)
    lists = _collect_yaml_mirror_lists(store)
    state_dir = Path(root_dir) / "state"
    counts: Dict[str, int] = {}
    for key in _YAML_LIST_KEYS:
        items = lists.get(key) or []
        if not isinstance(items, list):
            items = []
        _safe_write_yaml(state_dir / f"{key}.yaml", {key: items})
        counts[key] = len(items)
    logger.info("Exported YAML mirror to %s (%s)", state_dir, counts)
    return counts


def check_yaml_mirror_drift(root_dir: Path) -> List[str]:
    """Compare SQLite narrative counts with legacy YAML mirrors (best-effort)."""
    if not is_yaml_mirror_readable(root_dir):
        return []
    state_dir = Path(root_dir) / "state"
    if not state_dir.is_dir():
        return []
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(root_dir)
        lists = _collect_yaml_mirror_lists(store)
    except Exception as exc:
        logger.warning("yaml mirror drift check skipped: %s", exc)
        return []

    sqlite_counts: Dict[str, int] = {
        key: len(lists.get(key) or []) for key in _YAML_LIST_KEYS
    }
    warnings: List[str] = []
    mode = resolve_yaml_mirror_mode(root_dir)

    for key in _YAML_LIST_KEYS:
        yaml_count = _yaml_list_count(state_dir / f"{key}.yaml", key)
        if yaml_count < 0:
            continue
        sqlite_count = sqlite_counts.get(key, 0)
        if mode == "write":
            if yaml_count != sqlite_count:
                warnings.append(
                    f"state/{key}.yaml 条目数 ({yaml_count}) 与 SQLite ({sqlite_count}) 不一致"
                )
        elif mode == "read_only":
            if sqlite_count == 0 and yaml_count > 0:
                warnings.append(
                    f"检测到 SQLite 状态为空，但 state/{key}.yaml 镜像中存在数据 ({yaml_count}条)。"
                    f"若您是从旧版迁移，请运行导入以同步状态。"
                )
    return warnings