"""Task domain model and state transition rules for the V2 worker kernel."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    CHAPTER = "chapter"
    CHAPTER_BATCH = "chapter_batch"
    NOVEL_PLAN = "novel_plan"
    CHAPTER_PLAN = "chapter_plan"
    NOVEL_RUN = "novel_run"
    ARC_RUN = "arc_run"
    NOVEL_CONTINUE = "novel_continue"
    NOVEL_AUTOPILOT = "novel_autopilot"
    EMBEDDING_SETUP = "embedding_setup"
    EXPORT = "export"


class TaskTransitionError(ValueError):
    """Raised when a task attempts an invalid state change."""


_TERMINAL_STATUSES = frozenset({TaskStatus.SUCCEEDED, TaskStatus.CANCELLED})
_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.CLAIMED, TaskStatus.CANCELLED}),
    TaskStatus.CLAIMED: frozenset(
        {
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.PENDING,
            TaskStatus.PAUSED,
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.PAUSED: frozenset({TaskStatus.CLAIMED, TaskStatus.CANCELLED}),
    TaskStatus.SUCCEEDED: frozenset(),
    TaskStatus.FAILED: frozenset({TaskStatus.CLAIMED}),
    TaskStatus.CANCELLED: frozenset(),
}


def _coerce_status(value: TaskStatus | str) -> TaskStatus:
    try:
        return TaskStatus(value)
    except ValueError as exc:
        raise TaskTransitionError(f"Unknown task status: {value!r}") from exc


def assert_task_transition(
    current: TaskStatus | str,
    target: TaskStatus | str,
    *,
    attempt: int,
    max_attempts: int,
) -> None:
    """Validate a state change without mutating persistence."""

    source = _coerce_status(current)
    destination = _coerce_status(target)
    if source in _TERMINAL_STATUSES:
        raise TaskTransitionError(f"Task status {source.value!r} is terminal")
    if source is TaskStatus.FAILED and destination is TaskStatus.CLAIMED:
        if attempt >= max_attempts:
            raise TaskTransitionError(
                f"Task exhausted its attempt budget ({attempt}/{max_attempts})"
            )
        return
    if destination not in _ALLOWED_TRANSITIONS[source]:
        raise TaskTransitionError(
            f"Illegal task transition: {source.value} -> {destination.value}"
        )


class TaskRecord(BaseModel):
    """Serializable task record at the domain boundary."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=64)
    task_type: TaskType
    status: TaskStatus
    payload_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] | None = None
    attempt: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=1, ge=1)
    claim_token: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None
    checkpoint: dict[str, Any] | None = None
    status_reason: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def validate_attempt_budget(self) -> "TaskRecord":
        if self.attempt > self.max_attempts:
            raise ValueError("attempt cannot exceed max_attempts")
        return self
