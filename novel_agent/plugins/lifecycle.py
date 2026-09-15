"""Plugin lifecycle state machine and diagnostic model.

Implements INKREST Plugin Platform 2.0 lifecycle states:
- Normal progression: DISCOVERED -> VALIDATED -> INSTALLED -> TRUST_PENDING
                      -> RESOLVING -> READY -> ACTIVATING -> ACTIVE -> DISABLED
- Degraded / Fault states: DEGRADED, FAILED, QUARANTINED, INCOMPATIBLE,
                           DEPENDENCY_MISSING, PERMISSION_REQUIRED,
                           MIGRATION_REQUIRED, CRASHED, CIRCUIT_OPEN
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set


class PluginState(str, Enum):
    # Normal lifecycle states
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    INSTALLED = "installed"
    TRUST_PENDING = "trust_pending"
    RESOLVING = "resolving"
    READY = "ready"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DISABLED = "disabled"
    UNINSTALLED = "uninstalled"

    # Degraded / exceptional states
    DEGRADED = "degraded"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    INCOMPATIBLE = "incompatible"
    DEPENDENCY_MISSING = "dependency_missing"
    PERMISSION_REQUIRED = "permission_required"
    MIGRATION_REQUIRED = "migration_required"
    CRASHED = "crashed"
    CIRCUIT_OPEN = "circuit_open"


# Valid state transitions
VALID_TRANSITIONS: Dict[PluginState, Set[PluginState]] = {
    PluginState.DISCOVERED: {
        PluginState.VALIDATED,
        PluginState.INCOMPATIBLE,
        PluginState.FAILED,
    },
    PluginState.VALIDATED: {
        PluginState.INSTALLED,
        PluginState.TRUST_PENDING,
        PluginState.FAILED,
    },
    PluginState.INSTALLED: {
        PluginState.TRUST_PENDING,
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
        PluginState.FAILED,
    },
    PluginState.TRUST_PENDING: {
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
        PluginState.FAILED,
    },
    PluginState.RESOLVING: {
        PluginState.READY,
        PluginState.DEPENDENCY_MISSING,
        PluginState.PERMISSION_REQUIRED,
        PluginState.MIGRATION_REQUIRED,
        PluginState.DISABLED,
        PluginState.FAILED,
    },
    PluginState.READY: {
        PluginState.ACTIVATING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
        PluginState.FAILED,
    },
    PluginState.ACTIVATING: {
        PluginState.ACTIVE,
        PluginState.DEGRADED,
        PluginState.FAILED,
        PluginState.CRASHED,
    },
    PluginState.ACTIVE: {
        PluginState.DEGRADED,
        PluginState.DISABLED,
        PluginState.FAILED,
        PluginState.CRASHED,
        PluginState.CIRCUIT_OPEN,
        PluginState.UNINSTALLED,
    },
    PluginState.DEGRADED: {
        PluginState.ACTIVE,
        PluginState.DISABLED,
        PluginState.FAILED,
        PluginState.CRASHED,
        PluginState.CIRCUIT_OPEN,
        PluginState.QUARANTINED,
    },
    PluginState.DISABLED: {
        PluginState.RESOLVING,
        PluginState.ACTIVATING,
        PluginState.READY,
        PluginState.UNINSTALLED,
        PluginState.FAILED,
    },
    PluginState.CIRCUIT_OPEN: {
        PluginState.READY,
        PluginState.ACTIVATING,
        PluginState.QUARANTINED,
        PluginState.DISABLED,
        PluginState.FAILED,
    },
    PluginState.CRASHED: {
        PluginState.ACTIVATING,
        PluginState.QUARANTINED,
        PluginState.DISABLED,
        PluginState.FAILED,
    },
    PluginState.FAILED: {
        PluginState.VALIDATED,
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
    },
    PluginState.QUARANTINED: {
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
    },
    PluginState.INCOMPATIBLE: {
        PluginState.UNINSTALLED,
    },
    PluginState.DEPENDENCY_MISSING: {
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
    },
    PluginState.PERMISSION_REQUIRED: {
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
    },
    PluginState.MIGRATION_REQUIRED: {
        PluginState.RESOLVING,
        PluginState.DISABLED,
        PluginState.UNINSTALLED,
    },
    PluginState.UNINSTALLED: set(),
}


@dataclass
class PluginDiagnostics:
    plugin_id: str
    status: PluginState = PluginState.DISCOVERED
    reason: str = ""
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    last_healthy_time: Optional[float] = None
    active_since: Optional[float] = None
    worker_pid: Optional[int] = None
    crash_count: int = 0
    timeout_count: int = 0
    restart_count: int = 0
    history: list[Dict[str, Any]] = field(default_factory=list)

    def transition(
        self,
        to_state: PluginState,
        reason: str = "",
        error: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Record transition to new state with history."""
        now = time.time()
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if not force and to_state not in allowed and to_state != self.status:
            # We record a warning but allow graceful recovery if needed
            reason = f"Unconventional transition ({self.status.value} -> {to_state.value}): {reason}".strip()

        prev_state = self.status
        self.status = to_state
        self.reason = reason
        if error:
            self.last_error = error
            self.last_error_time = now

        if to_state == PluginState.ACTIVE:
            self.active_since = now
            self.last_healthy_time = now
        elif to_state in (PluginState.DISABLED, PluginState.UNINSTALLED, PluginState.FAILED):
            self.active_since = None

        self.history.append({
            "from": prev_state.value,
            "to": to_state.value,
            "reason": reason,
            "error": error,
            "timestamp": now,
        })
        # Keep last 50 history entries
        if len(self.history) > 50:
            self.history = self.history[-50:]

    def record_healthy(self) -> None:
        self.last_healthy_time = time.time()

    def record_timeout(self, message: str = "") -> None:
        self.timeout_count += 1
        self.last_error = message or f"Timeout recorded (#{self.timeout_count})"
        self.last_error_time = time.time()

    def record_crash(self, message: str = "") -> None:
        self.crash_count += 1
        self.last_error = message or f"Crash recorded (#{self.crash_count})"
        self.last_error_time = time.time()
        self.transition(PluginState.CRASHED, reason=f"Plugin worker crashed (#{self.crash_count})", error=self.last_error)

    def record_restart(self) -> None:
        self.restart_count += 1

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["state"] = self.status.value
        return data
