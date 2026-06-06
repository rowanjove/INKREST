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