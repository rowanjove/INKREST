from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.state.schema_version import (
    SCHEMA_VERSION,
    LegacySchemaError,
    SchemaState,
)
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection
from novel_agent.state.task_repository import (
    TaskConflictError,
    TaskOwnershipError,
)


def _new_store(tmp_path) -> SQLiteStateStore:
    return SQLiteStateStore(tmp_path)


def test_new_database_is_marked_as_v2_and_has_the_complete_task_schema(tmp_path):
    store = _new_store(tmp_path)

    assert store.schema_state is SchemaState.V2
    assert store.schema_version == SCHEMA_VERSION
    with safe_connection(store.db_path) as conn:
        version = conn.execute(
            "select value from app_metadata where key = 'schema_version'"
        ).fetchone()
        columns = {
            row[1] for row in conn.execute("pragma table_info(tasks)").fetchall()
        }
    assert version == (str(SCHEMA_VERSION),)
    assert {
        "id",
        "project_id",
        "task_type",
        "status",
        "payload_json",
        "result_json",
        "attempt",
        "max_attempts",
        "claim_token",
        "lease_expires_at",
        "heartbeat_at",
        "checkpoint",
        "status_reason",
        "created_at",
        "started_at",
        "finished_at",
    } <= columns


def test_existing_unversioned_database_is_reported_as_legacy(tmp_path):
    db_path = tmp_path / "data" / "novel.sqlite"
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("create table tasks (id text primary key, status text)")

    store = SQLiteStateStore(tmp_path)

    assert store.schema_state is SchemaState.LEGACY
    with pytest.raises(LegacySchemaError, match="reset"):
        store.task_repository.create_task(
            task_id="task-1",
            project_id="book-1",
            task_type=TaskType.CHAPTER,
            payload={"chapter_id": "001"},
        )


def test_create_task_is_idempotent_only_for_the_same_payload(tmp_path):
    repository = _new_store(tmp_path).task_repository
    first = repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "001", "goal": "开场"},
        max_attempts=2,
    )
    replay = repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"goal": "开场", "chapter_id": "001"},
        max_attempts=2,
    )

    assert replay == first
    with pytest.raises(TaskConflictError, match="different payload"):
        repository.create_task(
            task_id="task-1",
            project_id="book-1",
            task_type=TaskType.CHAPTER,
            payload={"chapter_id": "002", "goal": "冲突"},
            max_attempts=2,
        )


def test_claim_start_heartbeat_and_success_require_the_claim_token(tmp_path):
    repository = _new_store(tmp_path).task_repository
    repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "001"},
        max_attempts=2,
    )

    claimed = repository.claim_task("task-1", lease_seconds=30)
    assert claimed.status is TaskStatus.CLAIMED
    assert claimed.attempt == 1
    assert claimed.claim_token

    with pytest.raises(TaskOwnershipError):
        repository.start_task("task-1", "wrong-token")
    running = repository.start_task("task-1", claimed.claim_token)
    assert running.status is TaskStatus.RUNNING

    old_expiry = running.lease_expires_at
    heartbeat = repository.heartbeat(
        "task-1",
        claimed.claim_token,
        checkpoint={"step": "writer"},
        lease_seconds=60,
    )
    assert heartbeat.heartbeat_at is not None
    assert heartbeat.lease_expires_at > old_expiry
    assert heartbeat.checkpoint == {"step": "writer"}

    completed = repository.finish_task(
        "task-1",
        claimed.claim_token,
        status=TaskStatus.SUCCEEDED,
        result={"chapter_id": "001"},
    )
    assert completed.status is TaskStatus.SUCCEEDED
    assert completed.result_json == {"chapter_id": "001"}
    assert completed.finished_at is not None
    assert completed.claim_token is None


def test_failed_task_respects_retry_budget(tmp_path):
    repository = _new_store(tmp_path).task_repository
    repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={},
        max_attempts=1,
    )
    claimed = repository.claim_task("task-1")
    repository.start_task("task-1", claimed.claim_token)
    repository.finish_task(
        "task-1",
        claimed.claim_token,
        status=TaskStatus.FAILED,
        reason="provider_error",
    )

    assert repository.claim_task("task-1") is None


def test_expired_claims_are_requeued_but_live_leases_are_untouched(tmp_path):
    store = _new_store(tmp_path)
    repository = store.task_repository
    for task_id in ("expired", "live"):
        repository.create_task(
            task_id=task_id,
            project_id="book-1",
            task_type=TaskType.CHAPTER,
            payload={"chapter_id": task_id},
        )
        repository.claim_task(task_id, lease_seconds=120)

    past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    future = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    with safe_connection(store.db_path) as conn:
        conn.execute(
            "update tasks set lease_expires_at = ? where id = 'expired'",
            (past,),
        )
        conn.execute(
            "update tasks set lease_expires_at = ? where id = 'live'",
            (future,),
        )

    assert repository.recover_expired_leases() == ["expired"]
    assert repository.get_task("expired").status is TaskStatus.PENDING
    assert repository.get_task("expired").status_reason == "lease_expired"
    assert repository.get_task("live").status is TaskStatus.CLAIMED


def test_task_json_fields_round_trip_as_objects(tmp_path):
    store = _new_store(tmp_path)
    repository = store.task_repository
    repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.NOVEL_RUN,
        payload={"chapters": ["001", "002"]},
    )
    task = repository.get_task("task-1")

    assert task.payload_json == {"chapters": ["001", "002"]}
    with safe_connection(store.db_path) as conn:
        raw = conn.execute(
            "select payload_json from tasks where id = 'task-1'"
        ).fetchone()[0]
    assert json.loads(raw) == task.payload_json


def test_task_events_and_logs_are_project_scoped_and_ordered(tmp_path):
    repository = _new_store(tmp_path).task_repository
    repository.create_task(
        task_id="book-1-task",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "001"},
        max_attempts=2,
    )
    repository.create_task(
        task_id="book-2-task",
        project_id="book-2",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "099"},
    )

    claimed = repository.claim_task("book-1-task")
    assert claimed and claimed.claim_token
    repository.start_task("book-1-task", claimed.claim_token)
    repository.append_task_log(
        "book-1-task",
        level="info",
        step="writer",
        message="开始写作",
        timestamp=10.0,
    )
    repository.append_task_log(
        "book-1-task",
        level="warning",
        step="quality_guard",
        message="需要人工复核",
        timestamp=20.0,
    )
    repository.append_task_log(
        "book-2-task",
        level="error",
        step="writer",
        message="不应串到另一本书",
        timestamp=30.0,
    )

    events = repository.list_task_status_events(project_id="book-1")
    logs = repository.list_task_logs(project_id="book-1")

    assert [event["to_status"] for event in events] == ["running", "claimed"]
    assert [row["message"] for row in logs] == ["需要人工复核", "开始写作"]
    assert {row["task_id"] for row in logs} == {"book-1-task"}
    assert all("claim_token" not in event for event in events)


def test_task_log_rejects_unknown_task_and_bounds_user_text(tmp_path):
    repository = _new_store(tmp_path).task_repository
    repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={},
    )

    with pytest.raises(KeyError):
        repository.append_task_log(
            "missing",
            level="error",
            step="writer",
            message="unknown",
        )

    repository.append_task_log(
        "task-1",
        level="not-a-level",
        step="x" * 400,
        message="m" * 6000,
    )
    row = repository.list_task_logs(project_id="book-1")[0]
    assert row["level"] == "info"
    assert len(row["step"]) == 128
    assert len(row["message"]) == 4000
