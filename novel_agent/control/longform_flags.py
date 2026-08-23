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


def longform_flags(root_dir: Path | None = None) -> Dict[str, bool]:
    flags = dict(DEFAULT_LONGFORM_FLAGS)
    if root_dir is None:
        return flags
    try:
        from novel_agent.pipeline import load_pipeline_settings

        runtime = load_pipeline_settings(Path(root_dir)).get("runtime") or {}
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
    }
