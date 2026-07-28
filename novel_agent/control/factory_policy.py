"""Factory mode runtime effects (project_meta.factory_mode → pipeline behavior)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_FACTORY_MODE = "newbie_auto"

FACTORY_MODE_IDS = (
    "newbie_auto",
    "author_copilot",
    "platform_review",
    "longform_stable",
    "studio",
)

# Keys map to runtime_policy / quality / long_run resolvers (see module docstrings there).
FACTORY_RUNTIME_EFFECTS: Dict[str, Dict[str, Any]] = {
    "newbie_auto": {
        "quality_mode": "block_on_fail",
        "quality_auto_rewrite": True,
        "max_rewrites_override": 2,
    },
    "author_copilot": {
        "quality_mode": "report_only",
        "quality_auto_rewrite": False,
        "max_rewrites_override": 0,
        "audit_profile": "standard",
    },
    "platform_review": {
        "quality_mode": "block_on_fail",
        "quality_auto_rewrite": True,
        "audit_profile": "premium",
        "pipeline_tier": "premium",
        "max_rewrites_override": 2,
        "persona_evaluations": "on_fail_only",
    },
    "longform_stable": {
        "quality_mode": "block_on_fail",
        "quality_auto_rewrite": True,
        "audit_profile": "premium",
        "pipeline_tier": "premium",
        "require_vector_for_long_scale": True,
        "max_rewrites_override": 1,
    },
    "studio": {
        "quality_mode": "block_on_fail",
        "quality_auto_rewrite": True,
        "max_rewrites_override": 1,
        "batch_fail_streak_max": 3,
    },
}


def is_valid_factory_mode(mode: str) -> bool:
    return mode in FACTORY_MODE_IDS


def _read_project_meta(root_dir: Path) -> Dict[str, Any]:
    meta_path = Path(root_dir) / "config" / "project_meta.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_explicit_factory_mode(root_dir: Path) -> Optional[str]:
    """Return factory mode only when project_meta explicitly sets it."""
    data = _read_project_meta(root_dir)
    raw = str(data.get("factory_mode") or data.get("mode") or "").strip()
    if not raw:
        return None
    return raw if is_valid_factory_mode(raw) else None


def load_project_factory_mode(root_dir: Path) -> str:
    """Display/default factory mode (implicit default when unset)."""
    return read_explicit_factory_mode(root_dir) or DEFAULT_FACTORY_MODE


def resolve_factory_runtime_effects(root_dir: Path) -> Dict[str, Any]:
    """Runtime overrides; empty unless factory_mode is explicitly saved in project_meta."""
    mode = read_explicit_factory_mode(root_dir)
    if mode is None:
        return {"factory_mode": DEFAULT_FACTORY_MODE}
    base = dict(FACTORY_RUNTIME_EFFECTS.get(mode, FACTORY_RUNTIME_EFFECTS[DEFAULT_FACTORY_MODE]))
    base["factory_mode"] = mode
    return base


def factory_effect(root_dir: Path, key: str, default: Optional[Any] = None) -> Any:
    return resolve_factory_runtime_effects(root_dir).get(key, default)


def factory_requires_vector_for_long_scale(root_dir: Path) -> bool:
    return bool(factory_effect(root_dir, "require_vector_for_long_scale", False))