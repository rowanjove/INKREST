"""Runtime Supervisor for isolated plugin workers."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.logging_config import get_logger
from novel_agent.plugins.runtime.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from novel_agent.plugins.runtime.rpc import (
    RPCError,
    RPCRequest,
    RPCResponse,
    TIMEOUT_ERROR,
    decode_message,
    encode_message,
)
from novel_agent.plugins.runtime.worker import worker_process_main

logger = get_logger("plugins.supervisor")


@dataclass
class WorkerHandle:
    plugin_id: str
    entry_str: str
    plugin_root_str: str
    process: mp.Process
    in_queue: mp.Queue
    out_queue: mp.Queue
    circuit_breaker: CircuitBreaker
    pid: Optional[int] = None
    started_at: float = field(default_factory=time.time)

    def is_alive(self) -> bool:
        return bool(self.process and self.process.is_alive())


class RuntimeSupervisor:
    """Manages worker processes, RPC routing, hard timeouts, and fault protection."""

    def __init__(self) -> None:
        self._workers: Dict[str, WorkerHandle] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._mp_ctx = mp.get_context("spawn")

    def get_circuit_breaker(self, plugin_id: str) -> CircuitBreaker:
        if plugin_id not in self._circuit_breakers:
            self._circuit_breakers[plugin_id] = CircuitBreaker(plugin_id=plugin_id)
        return self._circuit_breakers[plugin_id]

    def start_worker(
        self,
        plugin_id: str,
        entry_str: str = "",
        plugin_root: Optional[Path] = None,
    ) -> WorkerHandle:
        """Spawn a new isolated worker process for the specified plugin."""
        # Terminate existing worker if any
        if plugin_id in self._workers:
            self.stop_worker(plugin_id)

        cb = self.get_circuit_breaker(plugin_id)
        if cb.state == CircuitState.QUARANTINED:
            raise CircuitOpenError(f"Plugin '{plugin_id}' is quarantined and cannot be started")

        in_queue = self._mp_ctx.Queue()
        out_queue = self._mp_ctx.Queue()
        root_str = str(plugin_root) if plugin_root else ""

        proc = self._mp_ctx.Process(
            target=worker_process_main,
            args=(in_queue, out_queue, plugin_id, entry_str, root_str),
            daemon=True,
        )
        proc.start()

        handle = WorkerHandle(
            plugin_id=plugin_id,
            entry_str=entry_str,
            plugin_root_str=root_str,
            process=proc,
            in_queue=in_queue,
            out_queue=out_queue,
            circuit_breaker=cb,
            pid=proc.pid,
            started_at=time.time(),
        )
        self._workers[plugin_id] = handle
        logger.info("Spawned plugin worker '%s' (PID %s)", plugin_id, proc.pid)
        return handle

    def call_rpc(
        self,
        plugin_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Any:
        """Call a method on a plugin worker via RPC with hard timeout enforcement."""
        cb = self.get_circuit_breaker(plugin_id)
        if not cb.allow_execution():
            raise CircuitOpenError(
                f"Execution rejected: Circuit is open for plugin '{plugin_id}' (Reason: {cb.last_failure_reason})"
            )

        handle = self._workers.get(plugin_id)
        if not handle or not handle.is_alive():
            # Auto-restart if dead and allowed
            if cb.allow_execution():
                handle = self.restart_worker(plugin_id)
            else:
                raise RuntimeError(f"Worker for plugin '{plugin_id}' is not running")

        req_id = str(uuid.uuid4())[:8]
        req = RPCRequest(id=req_id, method=method, params=params or {})

        # Send request
        try:
            handle.in_queue.put(req.to_dict())
        except Exception as exc:
            cb.record_crash(f"Failed sending to worker queue: {exc}")
            raise RuntimeError(f"Failed to communicate with worker for '{plugin_id}': {exc}") from exc

        # Wait for response with hard timeout
        try:
            raw_resp = handle.out_queue.get(timeout=timeout)
        except queue.Empty:
            # HARD TIMEOUT ENFORCEMENT
            logger.warning(
                "Plugin '%s' method '%s' exceeded timeout %.2fs. Terminating worker PID %s",
                plugin_id,
                method,
                timeout,
                handle.pid,
            )
            cb.record_timeout(f"Method '{method}' timed out ({timeout}s)")
            self._hard_kill(handle)
            raise TimeoutError(
                f"Plugin worker '{plugin_id}' exceeded timeout limit of {timeout}s and was terminated"
            ) from None

        # Check if process died during call
        if not handle.is_alive():
            cb.record_crash(f"Worker died during call to '{method}'")
            raise RuntimeError(f"Plugin worker '{plugin_id}' crashed during RPC call")

        # Parse response
        resp = decode_message(raw_resp)
        err = resp.get("error")
        if err:
            cb.record_error(err.get("message", "RPC error"))
            raise RPCError(code=err.get("code", -32603), message=err.get("message", "Unknown error"))

        cb.record_success()
        return resp.get("result")

    def _hard_kill(self, handle: WorkerHandle) -> None:
        """Forcefully terminate and clean up a worker process."""
        try:
            if handle.process.is_alive():
                handle.process.terminate()
                handle.process.join(0.5)
                if handle.process.is_alive():
                    handle.process.kill()
                    handle.process.join(0.2)
        except Exception as e:
            logger.error("Error killing worker for %s: %s", handle.plugin_id, e)
        finally:
            try:
                handle.in_queue.close()
                handle.out_queue.close()
            except Exception:
                pass

    def ping_worker(self, plugin_id: str, timeout: float = 2.0) -> bool:
        """Send a ping to verify worker liveness."""
        try:
            res = self.call_rpc(plugin_id, "system.ping", timeout=timeout)
            return bool(res and res.get("status") == "pong")
        except Exception:
            return False

    def restart_worker(self, plugin_id: str) -> WorkerHandle:
        """Restart a worker process for the plugin."""
        old_handle = self._workers.get(plugin_id)
        if not old_handle:
            raise KeyError(f"No existing worker handle found for '{plugin_id}'")

        entry_str = old_handle.entry_str
        root = Path(old_handle.plugin_root_str) if old_handle.plugin_root_str else None
        self.stop_worker(plugin_id)
        return self.start_worker(plugin_id, entry_str=entry_str, plugin_root=root)

    def stop_worker(self, plugin_id: str, timeout: float = 1.0) -> None:
        """Gracefully stop a worker process, falling back to termination."""
        handle = self._workers.pop(plugin_id, None)
        if not handle:
            return

        if handle.is_alive():
            try:
                handle.in_queue.put(None)  # Sentinel
                handle.process.join(timeout)
            except Exception:
                pass

        self._hard_kill(handle)

    def stop_all(self) -> None:
        """Stop all managed worker processes."""
        for pid in list(self._workers.keys()):
            self.stop_worker(pid)
