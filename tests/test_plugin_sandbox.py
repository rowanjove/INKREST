import os
import time

import pytest

from novel_agent.plugins.sandbox import run_callable_in_process


def _fast_hook() -> str:
    return "ok"


def _slow_hook() -> str:
    time.sleep(5)
    return "late"


def _env_probe() -> tuple[str | None, str | None]:
    return os.environ.get("OPENAI_API_KEY"), os.environ.get("PATH") or os.environ.get("SYSTEMROOT")


def test_sandbox_runs_fast_hook() -> None:
    assert run_callable_in_process(_fast_hook, timeout_seconds=2.0) == "ok"


def test_sandbox_kills_slow_hook() -> None:
    with pytest.raises(TimeoutError):
        run_callable_in_process(_slow_hook, timeout_seconds=0.3, default=None)


def test_sandbox_child_strips_secret_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    key, kept = run_callable_in_process(_env_probe, timeout_seconds=2.0)
    assert key is None
    assert kept


def test_untrusted_forbidden_unpickle_does_not_run_in_process(monkeypatch) -> None:
    ran = {"value": False}

    def hook() -> str:
        ran["value"] = True
        return "secret"

    hook.__module__ = "evil_plugin.hooks"
    monkeypatch.setattr("novel_agent.plugins.sandbox.pickle.dumps", lambda fn: b"blob")

    class FakeQueue:
        def empty(self):
            return False

        def get_nowait(self):
            return ("err", "UnpicklingError: Global 'evil_plugin.hooks.hook' is forbidden")

    class FakeProcess:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

        def join(self, timeout=None):
            return None

        def is_alive(self):
            return False

        def terminate(self):
            return None

    class FakeCtx:
        def Queue(self):
            return FakeQueue()

        def Process(self, **kwargs):
            return FakeProcess()

    monkeypatch.setattr("novel_agent.plugins.sandbox.mp.get_context", lambda name: FakeCtx())
    with pytest.raises(RuntimeError, match="forbidden"):
        run_callable_in_process(hook, timeout_seconds=1.0)
    assert ran["value"] is False


def test_unpicklable_untrusted_hook_does_not_run_in_process() -> None:
    def local_hook() -> str:
        return "secret"

    local_hook.__module__ = "evil_plugin.hooks"
    with pytest.raises(RuntimeError, match="not picklable"):
        run_callable_in_process(local_hook, timeout_seconds=1.0)