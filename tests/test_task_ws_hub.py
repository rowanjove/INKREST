"""Task WebSocket hub coalesced notifications."""

import subprocess
import sys
from pathlib import Path

from web.task_ws_hub import notify_tasks_changed


def test_notify_tasks_changed_is_safe_without_clients() -> None:
    notify_tasks_changed()


def test_task_ws_hub_imports_after_asyncio_run_closed_default_loop() -> None:
    code = (
        "import asyncio; "
        "asyncio.run(asyncio.sleep(0)); "
        "import web.task_ws_hub; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
