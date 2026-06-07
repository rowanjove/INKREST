"""Task WebSocket hub coalesced notifications."""

from web.task_ws_hub import notify_tasks_changed


def test_notify_tasks_changed_is_safe_without_clients() -> None:
    notify_tasks_changed()