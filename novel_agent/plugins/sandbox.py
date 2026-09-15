"""Optional subprocess isolation for pipeline hooks (Windows-friendly spawn)."""

from __future__ import annotations

import logging
import multiprocessing as mp
import io
import os
import pickle
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger("novel_agent.plugins.sandbox")

_TRUSTED_HOOK_MODULE_PREFIXES = (
    "novel_agent.",
    "builtins.",
    "test_plugin_sandbox",
    "tests.",
)
_UNTRUSTED_HOOK_MODULE_PREFIXES = (
    "novel_agent.plugins.local.",
)


def _is_trusted_hook_module(module: str) -> bool:
    name = module or ""
    if any(name.startswith(prefix) for prefix in _UNTRUSTED_HOOK_MODULE_PREFIXES):
        return False
    return any(name.startswith(prefix) for prefix in _TRUSTED_HOOK_MODULE_PREFIXES)

_KEEP_ENV_KEYS = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "PROGRAMDATA",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONUTF8",
        "PYTHONIOENCODING",
    }
)
_STRIP_ENV_FRAGMENTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL")


def _assert_trusted_hook_callable(fn: Callable[..., Any]) -> None:
    module = getattr(fn, "__module__", "") or ""
    if not _is_trusted_hook_module(module):
        raise RuntimeError(f"Untrusted sandbox hook module: {module or '<unknown>'}")


class _RestrictedUnpickler(pickle.Unpickler):
    """Safely unpickle callables, blocking arbitrary code execution during deserialization."""

    def find_class(self, module: str, name: str) -> Any:
        if _is_trusted_hook_module(module):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Global '{module}.{name}' is forbidden in sandbox unpickler")


def _scrub_hook_environ() -> None:
    """Drop secrets and unrelated env from the hook child. Not an OS sandbox."""
    for key in list(os.environ):
        upper = key.upper()
        if any(fragment in upper for fragment in _STRIP_ENV_FRAGMENTS):
            os.environ.pop(key, None)
            continue
        if upper not in _KEEP_ENV_KEYS and not upper.startswith("PYTHON"):
            os.environ.pop(key, None)


def _child_run(blob: bytes, out_queue: mp.Queue) -> None:
    try:
        _scrub_hook_environ()
        unpickler = _RestrictedUnpickler(io.BytesIO(blob))
        fn = unpickler.load()
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
        module = getattr(fn, "__module__", "") or ""
        if _is_trusted_hook_module(module):
            from novel_agent.plugins.hook_runner import call_hook_with_timeout

            return call_hook_with_timeout(fn, timeout_seconds, default)
        raise RuntimeError(
            f"Hook is not picklable for sandbox isolation: {module or '<unknown>'}"
        ) from None

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
    payload_text = str(payload)
    if "forbidden" in payload_text.lower() or "UnpicklingError" in payload_text:
        module = getattr(fn, "__module__", "") or ""
        if _is_trusted_hook_module(module):
            from novel_agent.plugins.hook_runner import call_hook_with_timeout

            return call_hook_with_timeout(fn, timeout_seconds, default)
        raise RuntimeError(payload)
    if default is not None:
        return default
    raise RuntimeError(payload)