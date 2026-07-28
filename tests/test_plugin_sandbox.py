import time

import pytest

from novel_agent.plugins.sandbox import run_callable_in_process


def _fast_hook() -> str:
    return "ok"


def _slow_hook() -> str:
    time.sleep(5)
    return "late"


def test_sandbox_runs_fast_hook() -> None:
    assert run_callable_in_process(_fast_hook, timeout_seconds=2.0) == "ok"


def test_sandbox_kills_slow_hook() -> None:
    with pytest.raises(TimeoutError):
        run_callable_in_process(_slow_hook, timeout_seconds=0.3, default=None)