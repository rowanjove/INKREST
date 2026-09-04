"""Feature flags for the longform scale/quality milestones.

Each flag defaults to on for backward-compatible engineering paths.
Rollback: set the corresponding flag to False in project pipeline
`runtime.longform_flags` or this module; callers must keep the previous
API working when a flag is off.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

DEFAULT_LONGFORM_FLAGS: Dict[str, bool] = {
    "m0_benchmarks": True,
    "m1_scale_budget": True,
    "m1_catalog_pagination": True,
    "m1_streaming_export": True,
    "m1_vector_readiness": True,
    "m2_hybrid_retrieval": False,
    "m3_canon_engine": False,
    "m4_evaluation": False,
    "m5_adaptive_candidates": False,
}

# micro stays off. short is the implicit 20-chapter default when no outline
# scale_profile exists, so memory flags must turn on there or most books miss them.
_MEMORY_ON_SCALES = frozenset({"short", "medium", "long", "epic", "infinite"})
_MEMORY_FLAGS = ("m2_hybrid_retrieval", "m3_canon_engine")


def _project_scale(root_dir: Path) -> str:
    try:
        from novel_agent.control.scale_profile import load_outline_scale_profile, resolve_scale_profile

        raw = load_outline_scale_profile(root_dir)
        if isinstance(raw, dict) and raw.get("scale"):
            return str(raw.get("scale") or "medium")
        return str(resolve_scale_profile(target_chapters=20).get("scale") or "short")
    except Exception:
        return "short"


def longform_flags(root_dir: Path | None = None) -> Dict[str, bool]:
    flags = dict(DEFAULT_LONGFORM_FLAGS)
    if root_dir is None:
        return flags
    root = Path(root_dir)
    if _project_scale(root) in _MEMORY_ON_SCALES:
        for name in _MEMORY_FLAGS:
            flags[name] = True
    try:
        from novel_agent.pipeline import load_pipeline_settings

        runtime = load_pipeline_settings(root).get("runtime") or {}
        override = runtime.get("longform_flags") or {}
        if isinstance(override, dict):
            for key, value in override.items():
                if key in flags:
                    flags[key] = bool(value)
    except Exception:
        return flags
    return flags


def flag_enabled(name: str, root_dir: Path | None = None) -> bool:
    return bool(longform_flags(root_dir).get(name, False))


def as_dict() -> Dict[str, Any]:
    return {
        "defaults": dict(DEFAULT_LONGFORM_FLAGS),
        "rollback": "Set runtime.longform_flags.<name>=false in pipeline.yaml",
        "memory_on_scales": sorted(_MEMORY_ON_SCALES),
    }
