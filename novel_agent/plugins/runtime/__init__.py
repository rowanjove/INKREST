"""INKREST Plugin Platform 2.0 Runtime Isolation Subsystem.

Provides:
- RPC message framing and serialization (rpc.py)
- Subprocess worker execution environment (worker.py)
- Process lifecycle supervision, hard timeouts, and auto-restart (supervisor.py)
- Circuit breaker failure rate protection and quarantine (circuit_breaker.py)
"""

from __future__ import annotations

from novel_agent.plugins.runtime.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from novel_agent.plugins.runtime.rpc import (
    RPCError,
    RPCNotification,
    RPCRequest,
    RPCResponse,
)
from novel_agent.plugins.runtime.supervisor import (
    RuntimeSupervisor,
    WorkerHandle,
)

__all__ = [
    "RPCRequest",
    "RPCResponse",
    "RPCNotification",
    "RPCError",
    "CircuitBreaker",
    "CircuitState",
    "RuntimeSupervisor",
    "WorkerHandle",
]
