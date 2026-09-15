"""Tests for INKREST Plugin Platform 2.0 Runtime Isolation Subsystem.

Covers:
- JSON-RPC 2.0 protocol serialization and parsing
- CircuitBreaker failure state machine and quarantine protection
- Subprocess worker execution, RPC method invocation, and ping liveness
- Hard Timeout: Subprocess worker is killed when exceeding timeout limit
- Auto-restart of workers after termination
"""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from novel_agent.plugins.runtime.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from novel_agent.plugins.runtime.rpc import (
    RPCError,
    RPCRequest,
    RPCResponse,
    decode_message,
    encode_message,
)
from novel_agent.plugins.runtime.supervisor import RuntimeSupervisor


def test_rpc_serialization_and_parsing() -> None:
    req = RPCRequest(id=101, method="hook.before_outline", params={"genre": "scifi"})
    encoded = encode_message(req)
    decoded = decode_message(encoded)
    assert decoded["id"] == 101
    assert decoded["method"] == "hook.before_outline"
    assert decoded["params"]["genre"] == "scifi"

    resp = RPCResponse(id=101, result={"outline_ok": True})
    decoded_resp = decode_message(encode_message(resp))
    assert decoded_resp["result"]["outline_ok"] is True

    err = RPCResponse(id=101, error=RPCError(code=-32601, message="Not Found"))
    decoded_err = decode_message(encode_message(err))
    assert decoded_err["error"]["code"] == -32601


def test_circuit_breaker_transitions() -> None:
    cb = CircuitBreaker(
        plugin_id="flaky-plugin",
        consecutive_timeout_threshold=2,
        cooldown_seconds=0.2,
        max_crashes=2,
    )
    assert cb.allow_execution() is True
    assert cb.state == CircuitState.ACTIVE

    # First timeout -> DEGRADED
    cb.record_timeout("first timeout")
    assert cb.state == CircuitState.DEGRADED
    assert cb.allow_execution() is True

    # Second timeout -> CIRCUIT_OPEN
    cb.record_timeout("second timeout")
    assert cb.state == CircuitState.CIRCUIT_OPEN
    assert cb.allow_execution() is False

    # Wait for cooldown -> PROBING
    time.sleep(0.25)
    assert cb.allow_execution() is True
    assert cb.state == CircuitState.PROBING

    # Successful probe -> ACTIVE
    cb.record_success()
    assert cb.state == CircuitState.ACTIVE

    # Repeated crashes -> QUARANTINED
    cb.record_crash("Crash 1")
    assert cb.state == CircuitState.CIRCUIT_OPEN
    cb.record_crash("Crash 2")
    assert cb.state == CircuitState.QUARANTINED
    assert cb.allow_execution() is False


def test_runtime_supervisor_ping_and_execution(tmp_path: Path) -> None:
    # Create a simple plugin file
    plugin_file = tmp_path / "simple_plugin.py"
    plugin_file.write_text(
        """
class SimplePlugin:
    def echo(self, text):
        return f"echo: {text}"
    def add(self, a, b):
        return a + b
""".strip(),
        encoding="utf-8",
    )

    supervisor = RuntimeSupervisor()
    try:
        handle = supervisor.start_worker(
            plugin_id="simple_plugin",
            entry_str="simple_plugin:SimplePlugin",
            plugin_root=tmp_path,
        )
        assert handle.is_alive() is True

        # Test system.ping
        assert supervisor.ping_worker("simple_plugin") is True

        # Test RPC execution
        res = supervisor.call_rpc(
            "simple_plugin",
            "plugin.echo",
            params={"args": ["hello"]},
            timeout=5.0,
        )
        assert res == "echo: hello"

        res_add = supervisor.call_rpc(
            "simple_plugin",
            "plugin.add",
            params={"args": [10, 25]},
            timeout=5.0,
        )
        assert res_add == 35

    finally:
        supervisor.stop_all()


def test_runtime_supervisor_hard_timeout_kills_worker(tmp_path: Path) -> None:
    # Create a plugin with a blocking infinite sleep hook
    plugin_file = tmp_path / "slow_plugin.py"
    plugin_file.write_text(
        """
import time
class SlowPlugin:
    def block_forever(self):
        time.sleep(30)
        return "unreachable"
""".strip(),
        encoding="utf-8",
    )

    supervisor = RuntimeSupervisor()
    try:
        handle = supervisor.start_worker(
            plugin_id="slow_plugin",
            entry_str="slow_plugin:SlowPlugin",
            plugin_root=tmp_path,
        )
        worker_proc = handle.process

        # Invoking slow method with a short timeout of 0.3s
        with pytest.raises(TimeoutError, match="exceeded timeout limit"):
            supervisor.call_rpc(
                "slow_plugin",
                "plugin.block_forever",
                timeout=0.3,
            )

        # HARD TIMEOUT VERIFICATION:
        # Worker process must have been forcefully terminated by the supervisor!
        time.sleep(0.1)
        assert worker_proc.is_alive() is False

        # Circuit breaker has recorded the timeout
        cb = supervisor.get_circuit_breaker("slow_plugin")
        assert cb.consecutive_timeouts == 1

    finally:
        supervisor.stop_all()


def test_runtime_supervisor_auto_restart(tmp_path: Path) -> None:
    plugin_file = tmp_path / "recover_plugin.py"
    plugin_file.write_text(
        """
class RecoverPlugin:
    def ping(self):
        return "alive"
""".strip(),
        encoding="utf-8",
    )

    supervisor = RuntimeSupervisor()
    try:
        handle = supervisor.start_worker(
            plugin_id="recover_plugin",
            entry_str="recover_plugin:RecoverPlugin",
            plugin_root=tmp_path,
        )
        first_pid = handle.pid

        # Force kill the worker process to simulate a sudden crash
        handle.process.terminate()
        handle.process.join(0.5)
        assert handle.is_alive() is False

        # Next call should auto-restart the worker
        res = supervisor.call_rpc("recover_plugin", "plugin.ping", timeout=5.0)
        assert res == "alive"

        # Verify new worker PID
        new_handle = supervisor._workers["recover_plugin"]
        assert new_handle.is_alive() is True
        assert new_handle.pid != first_pid

    finally:
        supervisor.stop_all()
