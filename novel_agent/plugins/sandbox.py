"""Optional subprocess isolation for pipeline hooks (Windows-friendly spawn)."""

from __future__ import annotations

import logging
import multiprocessing as mp
import pickle
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger("novel_agent.plugins.sandbox")

_TRUSTED_HOOK_MODULE_PREFIXES = (
    "novel_agent.plugins.",
    "builtins.",
    "test_plugin_sandbox",
    "tests.",
)


def _assert_trusted_hook_callable(fn: Callable[..., Any]) -> None:
    module = getattr(fn, "__module__", "") or ""
    if not any(module.startswith(prefix) for prefix in _TRUSTED_HOOK_MODULE_PREFIXES):
        raise RuntimeError(f"Untrusted sandbox hook module: {module or '<unknown>'}")


def _child_run(blob: bytes, out_queue: mp.Queue) -> None:
    try:
        fn = pickle.loads(blob)
        _assert_trusted_hook_callable(fn)
        out_queue.put(("ok", fn()))
    except Exception as exc:
        out_queue.put(("err", repr(exc)))


def run_callable_in_process(
    fn: Callable[[], T],
    timeout_seconds: float,
    default: Optional[T] = None,
) -> T:
    """Run picklable hook callable in a child process; kill on timeout."""
    try:
        blob = pickle.dumps(fn)
    except Exception:
        from novel_agent.plugins.hook_runner import call_hook_with_timeout

        return call_hook_with_timeout(fn, timeout_seconds, default)

    ctx = mp.get_context("spawn")
    out: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_child_run, args=(blob, out), daemon=True)
    proc.start()
    proc.join(timeout_seconds)
    if proc.is_alive():
        proc.terminate()
        proc.join(1)
        if default is not None:
            return default
        raise TimeoutError(f"Sandbox hook exceeded {timeout_seconds}s limit")
    if out.empty():
        if default is not None:
            return default
        raise TimeoutError(f"Sandbox hook produced no result within {timeout_seconds}s")
    status, payload = out.get_nowait()
    if status == "ok":
        return payload
    if default is not None:
        return default
    raise RuntimeError(payload)