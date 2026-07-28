"""WebSocket connection handler for task progress broadcasts."""

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from web.context import _get_task_manager, get_root_dir
from web.project_task_registry import ProjectTaskRegistry
from web.task_ws_hub import register_client, unregister_client


async def handle_websocket_tasks(ws: WebSocket, *, accepted: bool = False):
    """Register client; server pushes task snapshots on change via task_ws_hub."""
    if not accepted:
        await ws.accept()
    await register_client(ws)
    try:
        manager = ProjectTaskRegistry.shared().peek(get_root_dir())
        if manager is None:
            manager = _get_task_manager()
        tasks = manager.list_tasks()
        await ws.send_json(tasks)
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=90.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        await unregister_client(ws)