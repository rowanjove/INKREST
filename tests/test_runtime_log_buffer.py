"""Tests for web.runtime_log_buffer."""

from web.runtime_log_buffer import (
    append_runtime_log,
    clear_runtime_logs,
    list_runtime_logs,
    tail_runtime_logs,
)


def test_append_and_list():
    clear_runtime_logs()
    id1 = append_runtime_log({"type": "log", "level": "info", "message": "hello", "step": "writer"})
    id2 = append_runtime_log({"type": "progress", "step": "planner", "status": "running"})
    assert id2 > id1
    rows = list_runtime_logs(since_id=0)
    assert len(rows) >= 2
    assert rows[-1]["message"]


def test_tail_limit():
    clear_runtime_logs()
    for i in range(5):
        append_runtime_log({"type": "log", "message": f"m{i}"})
    tail = tail_runtime_logs(2)
    assert len(tail) == 2


def test_runtime_logs_can_be_scoped_to_one_project():
    clear_runtime_logs()
    append_runtime_log({"type": "log", "message": "book one", "project_id": "book-1"})
    append_runtime_log({"type": "log", "message": "book two", "project_id": "book-2"})

    assert [row["message"] for row in list_runtime_logs(project_id="book-1")] == [
        "book one"
    ]
    assert [row["message"] for row in tail_runtime_logs(20, project_id="book-2")] == [
        "book two"
    ]


def test_runtime_logs_can_clear_only_one_project():
    clear_runtime_logs()
    first_id = append_runtime_log(
        {"type": "log", "message": "book one", "project_id": "book-1"}
    )
    second_id = append_runtime_log(
        {"type": "log", "message": "book two", "project_id": "book-2"}
    )

    clear_runtime_logs(project_id="book-1")

    assert list_runtime_logs(project_id="book-1") == []
    assert [row["message"] for row in list_runtime_logs(project_id="book-2")] == [
        "book two"
    ]
    assert append_runtime_log(
        {"type": "log", "message": "book one again", "project_id": "book-1"}
    ) > max(first_id, second_id)
