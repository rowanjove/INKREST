from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from novel_agent.domain.project_snapshot import ProjectSnapshot
from novel_agent.domain.tasks import (
    TaskRecord,
    TaskStatus,
    TaskTransitionError,
    TaskType,
    assert_task_transition,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TaskStatus.PENDING, TaskStatus.CLAIMED),
        (TaskStatus.CLAIMED, TaskStatus.RUNNING),
        (TaskStatus.RUNNING, TaskStatus.SUCCEEDED),
        (TaskStatus.RUNNING, TaskStatus.PAUSED),
        (TaskStatus.PAUSED, TaskStatus.CLAIMED),
        (TaskStatus.PENDING, TaskStatus.CANCELLED),
        (TaskStatus.CLAIMED, TaskStatus.CANCELLED),
        (TaskStatus.RUNNING, TaskStatus.CANCELLED),
        (TaskStatus.PAUSED, TaskStatus.CANCELLED),
    ],
)
def test_task_state_machine_accepts_declared_transitions(current, target):
    assert_task_transition(current, target, attempt=0, max_attempts=2)


@pytest.mark.parametrize("terminal", [TaskStatus.SUCCEEDED, TaskStatus.CANCELLED])
def test_task_state_machine_rejects_transitions_from_terminal_states(terminal):
    with pytest.raises(TaskTransitionError, match="terminal"):
        assert_task_transition(terminal, TaskStatus.RUNNING, attempt=1, max_attempts=2)


def test_failed_task_can_only_be_reclaimed_with_attempts_remaining():
    assert_task_transition(
        TaskStatus.FAILED,
        TaskStatus.CLAIMED,
        attempt=1,
        max_attempts=2,
    )

    with pytest.raises(TaskTransitionError, match="attempt"):
        assert_task_transition(
            TaskStatus.FAILED,
            TaskStatus.CLAIMED,
            attempt=2,
            max_attempts=2,
        )


def test_task_state_machine_rejects_unknown_or_illegal_transitions():
    with pytest.raises(TaskTransitionError, match="Unknown"):
        assert_task_transition("waiting", TaskStatus.RUNNING, attempt=0, max_attempts=1)
    with pytest.raises(TaskTransitionError, match="Illegal"):
        assert_task_transition(
            TaskStatus.PENDING,
            TaskStatus.SUCCEEDED,
            attempt=0,
            max_attempts=1,
        )


def test_task_record_contains_the_complete_v2_contract():
    now = datetime.now(UTC)
    task = TaskRecord(
        id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        status=TaskStatus.RUNNING,
        payload_json={"chapter_id": "001", "goal": "开场"},
        result_json=None,
        attempt=1,
        max_attempts=2,
        claim_token="claim-1",
        lease_expires_at=now,
        heartbeat_at=now,
        checkpoint={"step": "writer"},
        status_reason=None,
        created_at=now,
        started_at=now,
        finished_at=None,
    )

    assert set(task.model_dump()) == {
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
    }


def test_task_record_rejects_attempts_beyond_the_retry_budget():
    with pytest.raises(ValidationError):
        TaskRecord(
            id="task-1",
            project_id="book-1",
            task_type=TaskType.CHAPTER,
            status=TaskStatus.FAILED,
            payload_json={},
            attempt=3,
            max_attempts=2,
            created_at=datetime.now(UTC),
        )


def test_project_snapshot_exposes_one_stable_top_level_contract():
    snapshot = ProjectSnapshot(
        project={"id": "book-1", "name": "测试书"},
        workflow_mode="assisted",
        readiness={"ready": True},
        outline_progress={"status": "ready"},
        chapter_progress={"completed": 1, "target": 10},
        active_tasks=[],
        blocking_issues=[],
        quality_summary={"status": "stable"},
        cost_summary={"total_cost_cny": 0.0},
        next_actions=[{"id": "write-next", "label": "继续写作"}],
        updated_at=datetime.now(UTC),
    )

    assert set(snapshot.model_dump()) == {
        "project",
        "workflow_mode",
        "readiness",
        "outline_progress",
        "chapter_progress",
        "active_tasks",
        "blocking_issues",
        "quality_summary",
        "cost_summary",
        "next_actions",
        "updated_at",
    }
