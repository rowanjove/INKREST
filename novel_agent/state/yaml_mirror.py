"""Legacy YAML state mirror controls (SQLite is source of truth)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger("novel_agent.state.yaml_mirror")

_YAML_LIST_KEYS = ("events", "objects", "foreshadows", "hooks")


def is_yaml_mirror_enabled(root_dir: Path) -> bool:
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    if "yaml_mirror_enabled" in runtime:
        raw = runtime.get("yaml_mirror_enabled")
        if isinstance(raw, str):
            return raw.strip().lower() not in ("0", "false", "no", "off")
        return bool(raw)
    return True


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


def check_yaml_mirror_drift(root_dir: Path) -> List[str]:
    """Compare SQLite narrative counts with legacy YAML mirrors (best-effort)."""
    if not is_yaml_mirror_enabled(root_dir):
        return []
    state_dir = Path(root_dir) / "state"
    if not state_dir.is_dir():
        return []
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(root_dir)
        continuity = store.get_continuity_state()
    except Exception as exc:
        logger.warning("yaml mirror drift check skipped: %s", exc)
        return []

    sqlite_counts: Dict[str, int] = {
        "events": len(continuity.get("events") or []),
        "objects": len(continuity.get("objects") or []),
        "foreshadows": len(continuity.get("foreshadows") or []),
        "hooks": len(continuity.get("hooks") or []),
    }
    warnings: List[str] = []
    for key in _YAML_LIST_KEYS:
        yaml_count = _yaml_list_count(state_dir / f"{key}.yaml", key)
        if yaml_count < 0:
            continue
        sqlite_count = sqlite_counts.get(key, 0)
        if yaml_count != sqlite_count:
            warnings.append(
                f"state/{key}.yaml 条目数 ({yaml_count}) 与 SQLite ({sqlite_count}) 不一致"
            )
    return warnings