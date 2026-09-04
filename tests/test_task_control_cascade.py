from __future__ import annotations

import sqlite3
import pytest

from novel_agent.domain.tasks import BatchOutcome, ControlAction, TaskRecord, TaskStatus, TaskType
from novel_agent.state.schema_version import SCHEMA_VERSION, SchemaState
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection
from novel_agent.state.task_repository import TaskConflictError


def _new_store(tmp_path) -> SQLiteStateStore:
    return SQLiteStateStore(tmp_path)


def test_task_parent_child_and_checkpoint_kind(tmp_path):
    repo = _new_store(tmp_path).task_repository

    parent = repo.create_task(
        task_id="parent-1",
        project_id="book-1",
        task_type=TaskType.NOVEL_CONTINUE,
        payload={"max_chapters": 5},
        checkpoint_kind="novel_batch",
    )
    assert parent.checkpoint_kind == "novel_batch"
    assert parent.parent_task_id is None
    assert parent.active_child_task_id is None

    child = repo.create_task(
        task_id="child-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "c001"},
        parent_task_id="parent-1",
        checkpoint_kind="chapter_draft",
    )
    assert child.parent_task_id == "parent-1"
    assert child.checkpoint_kind == "chapter_draft"

    repo.set_active_child_task("parent-1", "child-1")
    reloaded_parent = repo.get_task("parent-1")
    assert reloaded_parent.active_child_task_id == "child-1"

    children = repo.list_child_tasks("parent-1")
    assert len(children) == 1
    assert children[0].id == "child-1"


def test_cancel_requested_priority_over_pause(tmp_path):
    repo = _new_store(tmp_path).task_repository

    task = repo.create_task(
        task_id="task-prio",
        project_id="book-1",
        task_type=TaskType.NOVEL_CONTINUE,
        payload={},
    )

    # Request cancel
    updated = repo.request_control("task-prio", "cancel_requested")
    assert (updated.checkpoint or {}).get("control_action") == "cancel_requested"

    # Attempt to request pause while cancel is requested
    updated_after_pause = repo.request_control("task-prio", "pause_requested")
    # Must remain cancel_requested
    assert (updated_after_pause.checkpoint or {}).get("control_action") == "cancel_requested"


def test_llm_cost_unique_index_prevents_duplicate_call_id(tmp_path):
    store = _new_store(tmp_path)

    with safe_connection(store.db_path) as conn:
        conn.execute(
            """
            insert into llm_cost_log (call_id, model, input_tokens, output_tokens, project_id)
            values ('call-123', 'test-model', 100, 50, 'p1')
            """
        )

    # Attempting to insert duplicate call_id raises IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        with safe_connection(store.db_path) as conn:
            conn.execute(
                """
                insert into llm_cost_log (call_id, model, input_tokens, output_tokens, project_id)
                values ('call-123', 'test-model', 100, 50, 'p1')
                """
            )

    # history_repository.record_llm_cost uses insert or ignore / check exists
    # Even if called directly, it should handle idempotently
    res = store.log_llm_cost(
        model="test-model",
        input_tokens=10,
        output_tokens=5,
        input_cost=0.001,
        output_cost=0.002,
        project_id="p1",
        call_id="call-123",
    )
    assert res is False


def test_batch_outcome_model():
    success_outcome = BatchOutcome(
        status=TaskStatus.SUCCEEDED,
        completed_chapters=["c001", "c002"],
        reason="completed",
    )
    assert success_outcome.is_success is True
    assert success_outcome.is_paused is False
    assert success_outcome.is_cancelled is False

    paused_outcome = BatchOutcome(
        status=TaskStatus.PAUSED,
        completed_chapters=["c001"],
        reason="user_paused",
        resumable_from="novel_batch",
    )
    assert paused_outcome.is_success is False
    assert paused_outcome.is_paused is True
    assert paused_outcome.is_cancelled is False

    cancelled_outcome = BatchOutcome(
        status=TaskStatus.CANCELLED,
        completed_chapters=[],
        reason="user_cancelled",
    )
    assert cancelled_outcome.is_success is False
    assert cancelled_outcome.is_paused is False
    assert cancelled_outcome.is_cancelled is True
