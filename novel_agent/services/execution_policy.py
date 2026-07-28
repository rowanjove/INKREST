"""Resolve web-layer and chapter-layer concurrency for a project."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from novel_agent.control.runtime_policy import resolve_runtime_policy

_LONG_SCALES = frozenset({"long", "epic", "infinite"})
_MAX_CHAPTER_TASKS_CAP = 8
_MAX_SCENE_WORKERS_CAP = 16


def resolve_max_concurrent_chapters(root_dir: Path) -> int:
    """
    Web TaskManager semaphore: how many chapter-level tasks may run at once.

    ``runtime.max_concurrent_chapters`` overrides scale defaults (1–8).
    Long/epic/infinite default to 1; shorter scales default to 2.
    """
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("max_concurrent_chapters")
    if raw is not None:
        try:
            return max(1, min(int(raw), _MAX_CHAPTER_TASKS_CAP))
        except (TypeError, ValueError):
            pass

    policy = resolve_runtime_policy(root_dir)
    if policy.scale in _LONG_SCALES:
        return 1
    return 2


def resolve_scene_max_workers(root_dir: Path) -> int:
    """Scene parallelism inside one chapter (ThreadPoolExecutor in generation)."""
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    try:
        workers = int(runtime.get("max_workers", 4))
    except (TypeError, ValueError):
        workers = 4
    return max(1, min(workers, _MAX_SCENE_WORKERS_CAP))


def build_execution_snapshot(root_dir: Path) -> Dict[str, Any]:
    """Serializable execution policy for APIs and readiness."""
    policy = resolve_runtime_policy(root_dir)
    return {
        "scale": policy.scale,
        "max_concurrent_chapters": resolve_max_concurrent_chapters(root_dir),
        "max_scene_workers": resolve_scene_max_workers(root_dir),
    }