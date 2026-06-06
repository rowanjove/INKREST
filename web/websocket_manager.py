"""WebSocket connection handler for task progress broadcasts."""

from fastapi import WebSocket, WebSocketDisconnect
from web.context import _get_task_manager


async def handle_websocket_tasks(ws: WebSocket, *, accepted: bool = False):
    """Handle client connection and broadcast tasks status."""
    if not accepted:
        await ws.accept()
    try:
        while True:
            # Query all active tasks and status
            tasks = _get_task_manager().list_tasks()
            await ws.send_json(tasks)
            # Wait for any message (ping/heartbeat) from client to avoid spin lock
            await ws.receive_text()
    except WebSocketDisconnect:
        # Connection closed gracefully by the client, stop broadcasting
        pass
