"""Circuit Breaker pattern for plugin execution fault tolerance."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional


class CircuitState(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    PROBING = "probing"
    QUARANTINED = "quarantined"


class CircuitOpenError(RuntimeError):
    """Raised when an operation is blocked by an open or quarantined circuit breaker."""
    pass


class CircuitBreaker:
    """Manages failure rates and circuit state for an individual plugin."""

    def __init__(
        self,
        plugin_id: str,
        consecutive_timeout_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        max_crashes: int = 3,
        error_threshold: int = 10,
        error_window_seconds: float = 600.0,
    ) -> None:
        self.plugin_id = plugin_id
        self.consecutive_timeout_threshold = consecutive_timeout_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_crashes = max_crashes
        self.error_threshold = error_threshold
        self.error_window_seconds = error_window_seconds

        self.state: CircuitState = CircuitState.ACTIVE
        self.consecutive_timeouts: int = 0
        self.recent_errors: List[float] = []
        self.crash_count: int = 0
        self.opened_at: Optional[float] = None
        self.last_failure_reason: str = ""

    def allow_execution(self) -> bool:
        """Determine if an execution request should be permitted."""
        if self.state == CircuitState.QUARANTINED:
            return False

        if self.state == CircuitState.CIRCUIT_OPEN:
            now = time.time()
            if self.opened_at and (now - self.opened_at) >= self.cooldown_seconds:
                # Cooldown expired, enter probing mode
                self.state = CircuitState.PROBING
                return True
            return False

        return True

    def record_success(self) -> None:
        """Record successful execution."""
        self.consecutive_timeouts = 0
        if self.state in (CircuitState.DEGRADED, CircuitState.PROBING):
            self.state = CircuitState.ACTIVE

    def record_timeout(self, message: str = "") -> None:
        """Record execution timeout."""
        self.consecutive_timeouts += 1
        self.last_failure_reason = message or f"Timeout recorded ({self.consecutive_timeouts})"

        if self.consecutive_timeouts >= self.consecutive_timeout_threshold:
            self._trip(reason=f"Exceeded {self.consecutive_timeout_threshold} consecutive timeouts")
        elif self.state == CircuitState.ACTIVE:
            self.state = CircuitState.DEGRADED

    def record_error(self, message: str = "") -> None:
        """Record execution exception."""
        now = time.time()
        self.recent_errors.append(now)
        # Prune errors outside window
        cutoff = now - self.error_window_seconds
        self.recent_errors = [t for t in self.recent_errors if t >= cutoff]
        self.last_failure_reason = message or "Exception occurred"

        if len(self.recent_errors) >= self.error_threshold:
            self._trip(reason=f"Exceeded {self.error_threshold} errors within {self.error_window_seconds}s")
        elif self.state == CircuitState.ACTIVE and len(self.recent_errors) >= 3:
            self.state = CircuitState.DEGRADED

    def record_crash(self, message: str = "") -> None:
        """Record worker process crash."""
        self.crash_count += 1
        self.last_failure_reason = message or f"Worker process crashed (#{self.crash_count})"

        if self.crash_count >= self.max_crashes:
            self.state = CircuitState.QUARANTINED
        else:
            self._trip(reason=f"Worker crash (#{self.crash_count})")

    def _trip(self, reason: str) -> None:
        self.state = CircuitState.CIRCUIT_OPEN
        self.opened_at = time.time()
        self.last_failure_reason = reason

    def reset(self) -> None:
        """Explicitly reset the circuit breaker to active state."""
        self.state = CircuitState.ACTIVE
        self.consecutive_timeouts = 0
        self.recent_errors.clear()
        self.crash_count = 0
        self.opened_at = None
        self.last_failure_reason = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "state": self.state.value,
            "consecutive_timeouts": self.consecutive_timeouts,
            "recent_errors_count": len(self.recent_errors),
            "crash_count": self.crash_count,
            "opened_at": self.opened_at,
            "last_failure_reason": self.last_failure_reason,
        }
