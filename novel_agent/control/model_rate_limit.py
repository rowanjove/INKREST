"""Process-wide model call rate limit for explicitly-enabled remote serving."""

from __future__ import annotations

import os
import threading
import time
from collections import deque

from novel_agent.exceptions import LLMRateLimitError

ALLOW_REMOTE_ENV = "NOVEL_AGENT_ALLOW_REMOTE"
MAX_REMOTE_CALLS_ENV = "NOVEL_AGENT_MAX_MODEL_CALLS_PER_MINUTE"
WINDOW_SECONDS = 60.0
# A chapter can legitimately fan out to dozens of role calls. Keep a useful
# safety default while allowing operators to tune the cap for their workload.
MAX_REMOTE_CALLS = 120

_lock = threading.Lock()
_timestamps: deque[float] = deque()


def _remote_enabled() -> bool:
    return os.environ.get(ALLOW_REMOTE_ENV, "").strip().lower() in {"1", "true", "yes"}


def reset_model_call_rate_limit() -> None:
    with _lock:
        _timestamps.clear()


def _max_remote_calls() -> int:
    raw = os.environ.get(MAX_REMOTE_CALLS_ENV, "").strip()
    if not raw:
        return MAX_REMOTE_CALLS
    try:
        configured = int(raw)
    except ValueError:
        return MAX_REMOTE_CALLS
    return max(1, configured)


def enforce_model_call_rate_limit(*, now: float | None = None) -> None:
    """Reject bursty LLM calls when the process is bound for remote clients."""
    if not _remote_enabled():
        return
    stamp = time.monotonic() if now is None else now
    with _lock:
        while _timestamps and stamp - _timestamps[0] > WINDOW_SECONDS:
            _timestamps.popleft()
        max_calls = _max_remote_calls()
        if len(_timestamps) >= max_calls:
            raise LLMRateLimitError(
                f"Remote model call rate limit exceeded ({max_calls}/{int(WINDOW_SECONDS)}s)"
            )
        _timestamps.append(stamp)
