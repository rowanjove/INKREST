"""Transactional V2 task repository with idempotency, claims, and leases."""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from novel_agent.domain.tasks import (
    TaskRecord,
    TaskStatus,
    TaskTransitionError,
    TaskType,
    assert_task_transition,
)
from novel_agent.state.schema_version import LegacySchemaError, SchemaState
from novel_agent.state.sqlite_schema import safe_connection


class TaskConflictError(RuntimeError):
    """Raised when an idempotency key is reused for different work."""


class TaskOwnershipError(RuntimeError):
    """Raised when a worker mutates a task without its active claim token."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _dump_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("Task JSON fields must contain objects")
    return loaded


class TaskRepository:
    def __init__(self, db_path: Path, schema_state: SchemaState):
        self.db_path = Path(db_path)
        self.schema_state = schema_state

    def _require_v2(self) -> None:
        if self.schema_state is not SchemaState.V2:
            raise LegacySchemaError(
                "V2 task operations require an explicit backup and reset of legacy data"
            )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TaskRecord:
        values = dict(row)
        values["payload_json"] = _load_json(values.get("payload_json")) or {}
        values["result_json"] = _load_json(values.get("result_json"))
        values["checkpoint"] = _load_json(values.get("checkpoint"))
        return TaskRecord.model_validate(values)

    def get_task(self, task_id: str) -> TaskRecord | None:
        self._require_v2()
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select id, project_id, task_type, status, payload_json, result_json,
                       attempt, max_attempts, claim_token, lease_expires_at,
                       heartbeat_at, checkpoint, status_reason, created_at,
                       started_at, finished_at
                from tasks where id = ?
                """,
                (task_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_tasks(
        self,
        *,
        project_id: str | None = None,
        statuses: set[TaskStatus] | None = None,
        limit: int = 50,
    ) -> list[TaskRecord]:
        self._require_v2()
        clauses: list[str] = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if statuses:
            ordered = sorted(status.value for status in statuses)
            clauses.append(f"status in ({','.join('?' for _ in ordered)})")
            params.extend(ordered)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                select id, project_id, task_type, status, payload_json, result_json,
                       attempt, max_attempts, claim_token, lease_expires_at,
                       heartbeat_at, checkpoint, status_reason, created_at,
                       started_at, finished_at
                from tasks {where}
                order by created_at desc limit ?
                """,
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def create_task(
        self,
        *,
        task_id: str,
        project_id: str,
        task_type: TaskType | str,
        payload: dict[str, Any],
        max_attempts: int = 1,
    ) -> TaskRecord:
        self._require_v2()
        normalized_type = TaskType(task_type)
        payload_json = _dump_json(payload)
        now = _utcnow().isoformat()
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                """
                select id, project_id, task_type, status, payload_json, result_json,
                       attempt, max_attempts, claim_token, lease_expires_at,
                       heartbeat_at, checkpoint, status_reason, created_at,
                       started_at, finished_at
                from tasks where id = ?
                """,
                (task_id,),
            ).fetchone()
            if existing:
                record = self._row_to_record(existing)
                if (
                    record.project_id != project_id
                    or record.task_type is not normalized_type
                    or record.payload_json != payload
                    or record.max_attempts != max_attempts
                ):
                    raise TaskConflictError(
                        f"Task id {task_id!r} was reused with a different payload"
                    )
                return record
            conn.execute(
                """
                insert into tasks (
                  id, project_id, task_type, status, payload_json,
                  attempt, max_attempts, created_at
                ) values (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    task_id,
                    project_id,
                    normalized_type.value,
                    TaskStatus.PENDING.value,
                    payload_json,
                    max_attempts,
                    now,
                ),
            )
        task = self.get_task(task_id)
        if task is None:
            raise RuntimeError(f"Task {task_id!r} disappeared after creation")
        return task

    def claim_task(
        self,
        task_id: str,
        *,
        lease_seconds: int = 60,
    ) -> TaskRecord | None:
        self._require_v2()
        now = _utcnow()
        token = secrets.token_urlsafe(24)
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("begin immediate")
            row = conn.execute(
                """
                select status, attempt, max_attempts from tasks where id = ?
                """,
                (task_id,),
            ).fetchone()
            if not row:
                return None
            status = TaskStatus(row["status"])
            if status not in {TaskStatus.PENDING, TaskStatus.FAILED}:
                return None
            try:
                assert_task_transition(
                    status,
                    TaskStatus.CLAIMED,
                    attempt=int(row["attempt"]),
                    max_attempts=int(row["max_attempts"]),
                )
            except TaskTransitionError:
                return None
            lease_expires_at = (now + timedelta(seconds=lease_seconds)).isoformat()
            updated = conn.execute(
                """
                update tasks set
                  status = ?,
                  attempt = attempt + 1,
                  claim_token = ?,
                  lease_expires_at = ?,
                  heartbeat_at = ?,
                  status_reason = null,
                  finished_at = null
                where id = ? and status = ? and attempt = ?
                """,
                (
                    TaskStatus.CLAIMED.value,
                    token,
                    lease_expires_at,
                    now.isoformat(),
                    task_id,
                    status.value,
                    int(row["attempt"]),
                ),
            )
            if updated.rowcount != 1:
                return None
            self._record_event(
                conn,
                task_id,
                status,
                TaskStatus.CLAIMED,
                reason="worker_claimed",
            )
        return self.get_task(task_id)

    def start_task(self, task_id: str, claim_token: str) -> TaskRecord:
        self._require_v2()
        now = _utcnow().isoformat()
        with safe_connection(self.db_path) as conn:
            updated = conn.execute(
                """
                update tasks set status = ?, started_at = coalesce(started_at, ?)
                where id = ? and status = ? and claim_token = ?
                """,
                (
                    TaskStatus.RUNNING.value,
                    now,
                    task_id,
                    TaskStatus.CLAIMED.value,
                    claim_token,
                ),
            )
            if updated.rowcount != 1:
                raise TaskOwnershipError("Task is not claimed by this worker")
            self._record_event(
                conn,
                task_id,
                TaskStatus.CLAIMED,
                TaskStatus.RUNNING,
                reason="worker_started",
            )
        return self._required_task(task_id)

    def heartbeat(
        self,
        task_id: str,
        claim_token: str,
        *,
        checkpoint: dict[str, Any] | None = None,
        lease_seconds: int = 60,
    ) -> TaskRecord:
        self._require_v2()
        now = _utcnow()
        updated_checkpoint = _dump_json(checkpoint)
        with safe_connection(self.db_path) as conn:
            if checkpoint is None:
                updated = conn.execute(
                    """
                    update tasks set heartbeat_at = ?, lease_expires_at = ?
                    where id = ? and claim_token = ?
                      and status in (?, ?)
                    """,
                    (
                        now.isoformat(),
                        (now + timedelta(seconds=lease_seconds)).isoformat(),
                        task_id,
                        claim_token,
                        TaskStatus.CLAIMED.value,
                        TaskStatus.RUNNING.value,
                    ),
                )
            else:
                updated = conn.execute(
                    """
                    update tasks set
                      heartbeat_at = ?, lease_expires_at = ?, checkpoint = ?
                    where id = ? and claim_token = ?
                      and status in (?, ?)
                    """,
                    (
                        now.isoformat(),
                        (now + timedelta(seconds=lease_seconds)).isoformat(),
                        updated_checkpoint,
                        task_id,
                        claim_token,
                        TaskStatus.CLAIMED.value,
                        TaskStatus.RUNNING.value,
                    ),
                )
            if updated.rowcount != 1:
                raise TaskOwnershipError("Task lease is not owned by this worker")
        return self._required_task(task_id)

    def finish_task(
        self,
        task_id: str,
        claim_token: str,
        *,
        status: TaskStatus | str,
        result: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> TaskRecord:
        self._require_v2()
        target = TaskStatus(status)
        if target not in {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.PAUSED,
        }:
            raise TaskTransitionError(f"Invalid worker completion status: {target.value}")
        current = self._required_task(task_id)
        if current.claim_token != claim_token:
            raise TaskOwnershipError("Task lease is not owned by this worker")
        assert_task_transition(
            current.status,
            target,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
        )
        finished_at = (
            _utcnow().isoformat()
            if target in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}
            else None
        )
        with safe_connection(self.db_path) as conn:
            updated = conn.execute(
                """
                update tasks set
                  status = ?, result_json = coalesce(?, result_json),
                  status_reason = ?, claim_token = null,
                  lease_expires_at = null, finished_at = ?
                where id = ? and status = ? and claim_token = ?
                """,
                (
                    target.value,
                    _dump_json(result),
                    reason,
                    finished_at,
                    task_id,
                    current.status.value,
                    claim_token,
                ),
            )
            if updated.rowcount != 1:
                raise TaskOwnershipError("Task changed before completion")
            self._record_event(
                conn,
                task_id,
                current.status,
                target,
                reason=reason,
            )
        return self._required_task(task_id)

    def cancel_task(self, task_id: str, *, reason: str = "user_cancelled") -> TaskRecord:
        self._require_v2()
        current = self._required_task(task_id)
        if current.status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
            raise TaskTransitionError(
                f"Task status {current.status.value!r} is terminal"
            )
        if current.status is TaskStatus.FAILED:
            raise TaskTransitionError("Failed tasks cannot be cancelled")
        assert_task_transition(
            current.status,
            TaskStatus.CANCELLED,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
        )
        with safe_connection(self.db_path) as conn:
            updated = conn.execute(
                """
                update tasks set
                  status = ?, status_reason = ?, claim_token = null,
                  lease_expires_at = null, finished_at = ?
                where id = ? and status = ?
                """,
                (
                    TaskStatus.CANCELLED.value,
                    reason,
                    _utcnow().isoformat(),
                    task_id,
                    current.status.value,
                ),
            )
            if updated.rowcount != 1:
                raise TaskConflictError("Task changed before cancellation")
            self._record_event(
                conn,
                task_id,
                current.status,
                TaskStatus.CANCELLED,
                reason=reason,
            )
        return self._required_task(task_id)

    def delete_old_tasks(self, *, keep: int = 50) -> int:
        self._require_v2()
        terminal = (
            TaskStatus.SUCCEEDED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        )
        with safe_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                select id from tasks
                where status in (?, ?, ?)
                order by created_at desc
                """,
                terminal,
            ).fetchall()
            task_ids = [row[0] for row in rows[max(0, int(keep)) :]]
            if task_ids:
                conn.executemany(
                    "delete from task_status_events where task_id = ?",
                    [(task_id,) for task_id in task_ids],
                )
                conn.executemany(
                    "delete from task_logs where task_id = ?",
                    [(task_id,) for task_id in task_ids],
                )
                conn.executemany(
                    "delete from tasks where id = ?",
                    [(task_id,) for task_id in task_ids],
                )
        return len(task_ids)

    def recover_expired_leases(self, *, now: datetime | None = None) -> list[str]:
        self._require_v2()
        reference = now or _utcnow()
        recovered: list[str] = []
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("begin immediate")
            rows = conn.execute(
                """
                select id, status, lease_expires_at
                from tasks where status in (?, ?)
                """,
                (TaskStatus.CLAIMED.value, TaskStatus.RUNNING.value),
            ).fetchall()
            for row in rows:
                raw_expiry = row["lease_expires_at"]
                if not raw_expiry:
                    continue
                try:
                    expires_at = datetime.fromisoformat(raw_expiry)
                except ValueError:
                    expires_at = reference - timedelta(seconds=1)
                if expires_at > reference:
                    continue
                source = TaskStatus(row["status"])
                assert_task_transition(
                    source,
                    TaskStatus.PENDING,
                    attempt=0,
                    max_attempts=1,
                )
                conn.execute(
                    """
                    update tasks set
                      status = ?, claim_token = null, lease_expires_at = null,
                      status_reason = ?
                    where id = ? and status = ?
                    """,
                    (
                        TaskStatus.PENDING.value,
                        "lease_expired",
                        row["id"],
                        source.value,
                    ),
                )
                self._record_event(
                    conn,
                    row["id"],
                    source,
                    TaskStatus.PENDING,
                    reason="lease_expired",
                )
                recovered.append(row["id"])
        return recovered

    def _required_task(self, task_id: str) -> TaskRecord:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Task {task_id!r} not found")
        return task

    @staticmethod
    def _record_event(
        conn: sqlite3.Connection,
        task_id: str,
        source: TaskStatus,
        target: TaskStatus,
        *,
        reason: str | None,
    ) -> None:
        conn.execute(
            """
            insert into task_status_events
              (task_id, from_status, to_status, reason)
            values (?, ?, ?, ?)
            """,
            (task_id, source.value, target.value, reason),
        )
