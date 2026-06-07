"""Long-run (500+ chapter) runtime policy helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from novel_agent.control.runtime_policy import merge_scale_profile, resolve_runtime_policy
from novel_agent.control.scale_profile import load_outline_scale_profile
from novel_agent.pipeline import load_pipeline_settings

_DEFAULT_FAIL_STREAK = 5
_DEFAULT_SKIP_PAUSE = 1
_DEFAULT_CHAPTER_RETRY_MAX = 3
_DEFAULT_VECTOR_WINDOW = 80
_DEFAULT_HNSW_REBUILD_EVERY = 0


def _merged_scale(root_dir: Path) -> Dict[str, Any]:
    raw = load_outline_scale_profile(root_dir)
    if raw:
        return merge_scale_profile(raw)
    policy = resolve_runtime_policy(root_dir)
    return merge_scale_profile({"scale": policy.scale, "target_chapters": policy.target_chapters})


def resolve_compress_schedule(root_dir: Path) -> Tuple[int, int, int]:
    """(hot_every, warm_every, event_threshold). 0 disables that tier."""
    scale = _merged_scale(root_dir)
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    hot = int(runtime.get("compress_hot_every") or scale.get("compress_hot_every") or 0)
    warm = int(runtime.get("compress_warm_every") or scale.get("compress_warm_every") or 0)
    threshold = int(
        runtime.get("compress_event_threshold")
        or scale.get("compress_event_threshold")
        or 100
    )
    if hot <= 0 and scale.get("scale") in ("medium", "long", "epic", "infinite"):
        hot = 10
    return max(0, hot), max(0, warm), max(1, threshold)


def resolve_batch_fail_streak_max(root_dir: Path) -> int:
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("batch_fail_streak_max", _DEFAULT_FAIL_STREAK)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_FAIL_STREAK


def resolve_chapter_retry_max(root_dir: Path) -> int:
    """Max batch attempts per chapter before pausing (avoids token burn on one stuck chapter)."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("chapter_retry_max", _DEFAULT_CHAPTER_RETRY_MAX)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_CHAPTER_RETRY_MAX


def resolve_batch_skip_pause_max(root_dir: Path) -> int:
    """Pause whole batch after N consecutive chapter skips (retry queue). 0 = disabled."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("batch_skip_pause_max", _DEFAULT_SKIP_PAUSE)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_SKIP_PAUSE


def resolve_pause_on_quality_block(root_dir: Path) -> bool:
    """When True, first quality/gate failure pauses the batch (no silent skip-ahead)."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("pause_on_quality_block", True)
    if isinstance(raw, str):
        return raw.strip().lower() not in ("0", "false", "no", "off")
    return bool(raw)


def should_merge_review_stages(root_dir: Path) -> bool:
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    return bool(runtime.get("merge_review_stages", True))


def resolve_hnsw_rebuild_every(root_dir: Path) -> int:
    """Rebuild HNSW from SQLite every N chapters; 0 = only manual/API rebuild."""
    scale = _merged_scale(root_dir)
    scale_val = scale.get("hnsw_rebuild_every")
    if scale_val is not None:
        try:
            return max(0, int(scale_val))
        except (TypeError, ValueError):
            pass
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("hnsw_rebuild_every", _DEFAULT_HNSW_REBUILD_EVERY)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_HNSW_REBUILD_EVERY


def resolve_vector_search_window(root_dir: Path) -> int:
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("vector_search_window", _DEFAULT_VECTOR_WINDOW)
    try:
        return max(10, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_VECTOR_WINDOW


def resolve_audit_max_rewrites(root_dir: Path) -> int:
    """Audit paragraph rewrite iterations; epic/long default lighter."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    if "max_rewrites" in runtime:
        try:
            return max(0, int(runtime["max_rewrites"]))
        except (TypeError, ValueError):
            pass
    scale = str(_merged_scale(root_dir).get("scale") or "medium")
    if scale in ("epic", "infinite"):
        return 0
    if scale == "long":
        return 1
    return 2


def resolve_batch_inter_chapter_delay_sec(root_dir: Path) -> float:
    """Pause between chapters in batch/arc runs (rate-limit hygiene)."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = runtime.get("batch_inter_chapter_delay_sec", 0)
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def resolve_rate_limit_backoff(root_dir: Path) -> Tuple[float, int]:
    """(base_seconds, max_retries) for LLM 429 / rate limit."""
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    base = runtime.get("rate_limit_backoff_sec", 8)
    retries = runtime.get("rate_limit_max_retries", 4)
    try:
        base_f = max(1.0, float(base))
    except (TypeError, ValueError):
        base_f = 8.0
    try:
        retries_i = max(0, int(retries))
    except (TypeError, ValueError):
        retries_i = 4
    return base_f, retries_i


async def sleep_inter_chapter(root_dir: Path) -> None:
    delay = resolve_batch_inter_chapter_delay_sec(root_dir)
    if delay > 0:
        await asyncio.sleep(delay)


async def backoff_on_rate_limit(root_dir: Path, attempt: int) -> None:
    base, max_retries = resolve_rate_limit_backoff(root_dir)
    if attempt >= max_retries:
        return
    await asyncio.sleep(min(120.0, base * (2**attempt)))


def chapter_run_is_failure(result: Any) -> bool:
    """True when a chapter result should count toward batch circuit breaker."""
    warnings = getattr(result, "warnings", None) or []
    for msg in warnings:
        text = str(msg)
        if any(
            token in text
            for token in (
                "质量门禁未通过",
                "未通过审批",
                "quality_blocked",
            )
        ):
            return True
    audit = getattr(result, "audit", None) or {}
    if isinstance(audit, dict) and audit.get("risk_level") == "极高":
        return True
    return False