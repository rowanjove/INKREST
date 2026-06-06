"""Pipeline defaults for long/epic scale — synced from outline, not a separate UI action."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from novel_agent.control.scale_profile import load_outline_scale_profile
from novel_agent.pipeline import (
    GLOBAL_SHARED_SECTIONS,
    load_pipeline_settings,
    load_project_pipeline_file,
    resolve_global_config_dir,
    write_pipeline_file,
)

LONG_FORM_SCALES = frozenset({"long", "epic", "infinite"})

LONG_FORM_PIPELINE_PATCH: Dict[str, Any] = {
    "runtime": {
        "batch_fail_streak_max": 5,
        "vector_search_window": 80,
        "hnsw_rebuild_every": 50,
        "merge_review_stages": True,
    },
    "chapter": {
        "persona_evaluations": "auto",
        "quality_mode": "block_on_fail",
        "quality_auto_rewrite": True,
    },
    "quality": {
        "gate_mode": "unified",
        "auto_rewrite": True,
    },
    "embedding": {
        "backend": "chromadb",
    },
}


def _resolve_scale(root_dir: Path, scale: str = "") -> str:
    if scale:
        return scale.strip().lower()
    profile = load_outline_scale_profile(root_dir) or {}
    return str(profile.get("scale") or "").strip().lower()


def sync_pipeline_for_scale(root_dir: Path, scale: str = "") -> Tuple[bool, str]:
    """
    When project scale is long/epic/infinite, merge pipeline tuning into pipeline.yaml.
    Returns (applied, scale). Idempotent — safe on create/outline save/plan novel.
    """
    root = Path(root_dir)
    resolved = _resolve_scale(root, scale)
    if resolved not in LONG_FORM_SCALES:
        return False, resolved

    current = load_pipeline_settings(root)
    for section, values in LONG_FORM_PIPELINE_PATCH.items():
        if not isinstance(values, dict):
            continue
        block = dict(current.get(section) or {})
        for key, val in values.items():
            if key not in block or block.get(key) in (None, "", []):
                block[key] = val
            elif section == "runtime" and key in (
                "batch_fail_streak_max",
                "vector_search_window",
                "hnsw_rebuild_every",
                "merge_review_stages",
            ):
                block[key] = val
            elif section == "chapter" and key == "persona_evaluations" and block.get(key) in (
                "full",
                None,
            ):
                block[key] = val
        current[section] = block

    emb = current.get("embedding") or {}
    if str(emb.get("provider") or "stub").strip().lower() == "stub":
        emb = dict(emb)
        emb.setdefault(
            "_scale_sync_note",
            "长篇体量已同步流水线默认项；请将 embedding.provider 改为非 stub 以启用语义检索",
        )
        current["embedding"] = emb

    config_path = root / "config" / "pipeline.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    global_dir = resolve_global_config_dir(root)
    if global_dir:
        on_disk = load_project_pipeline_file(root)
        for section, values in LONG_FORM_PIPELINE_PATCH.items():
            if section in GLOBAL_SHARED_SECTIONS:
                continue
            if not isinstance(values, dict):
                continue
            block = dict(on_disk.get(section) or current.get(section) or {})
            for key, val in values.items():
                if key not in block or block.get(key) in (None, "", []):
                    block[key] = val
                elif section == "runtime" and key in (
                    "batch_fail_streak_max",
                    "vector_search_window",
                    "hnsw_rebuild_every",
                    "merge_review_stages",
                ):
                    block[key] = val
                elif section == "chapter" and key == "persona_evaluations" and block.get(key) in (
                    "full",
                    None,
                ):
                    block[key] = val
            on_disk[section] = block
        for key in GLOBAL_SHARED_SECTIONS:
            on_disk.pop(key, None)
        write_pipeline_file(config_path, on_disk)
    else:
        write_pipeline_file(config_path, current)
    return True, resolved


def apply_long_form_preset(root_dir: Path, *, scale: str = "") -> Tuple[Dict[str, Any], str]:
    """Backward-compatible alias: sync from explicit scale or outline profile only."""
    _, resolved = sync_pipeline_for_scale(root_dir, scale=scale)
    return load_pipeline_settings(root_dir), resolved