"""Timeout wrapper for pipeline hook plugins."""

from __future__ import annotations

import queue
import threading
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


def plugin_sandbox_enabled(root_dir: Any) -> bool:
    return bool(
        load_pipeline_settings(root_dir).get("runtime", {}).get("plugin_sandbox", False)
    )


def dispatch_hook(
    fn: Callable[[], T],
    root_dir: Any,
    timeout_seconds: float,
    default: Optional[T] = None,
) -> T:
    """Thread timeout by default; optional subprocess sandbox via runtime.plugin_sandbox."""
    if plugin_sandbox_enabled(root_dir):
        from novel_agent.plugins.sandbox import run_callable_in_process

        return run_callable_in_process(fn, timeout_seconds, default)
    return call_hook_with_timeout(fn, timeout_seconds, default)


def call_hook_with_timeout(
    fn: Callable[[], T],
    timeout_seconds: float,
    default: Optional[T] = None,
) -> T:
    """Run a hook callable with a hard timeout (sync hooks only)."""
    result_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=1)

    def _runner() -> None:
        try:
            result_queue.put(("ok", fn()))
        except Exception as exc:
            result_queue.put(("err", exc))

    thread = threading.Thread(target=_runner, name="novel-agent-hook", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        if default is not None:
            return default
        raise TimeoutError(f"Pipeline hook exceeded {timeout_seconds}s limit")

    status, payload = result_queue.get_nowait()
    if status == "err":
        raise payload
    return payload
