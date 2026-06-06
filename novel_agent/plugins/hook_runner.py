"""Timeout wrapper for pipeline hook plugins."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, Optional, TypeVar

from novel_agent.pipeline import load_pipeline_settings

T = TypeVar("T")

DEFAULT_HOOK_TIMEOUT_SECONDS = 30.0


def resolve_hook_timeout_seconds(root_dir: Any) -> float:
    raw = load_pipeline_settings(root_dir).get("runtime", {}).get(
        "hook_timeout_seconds", DEFAULT_HOOK_TIMEOUT_SECONDS
    )
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = DEFAULT_HOOK_TIMEOUT_SECONDS
    return max(1.0, timeout)


def call_hook_with_timeout(
    fn: Callable[[], T],
    timeout_seconds: float,
    default: Optional[T] = None,
) -> T:
    """Run a hook callable with a hard timeout (sync hooks only)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            if default is not None:
                return default
            raise TimeoutError(
                f"Pipeline hook exceeded {timeout_seconds}s limit"
            ) from exc