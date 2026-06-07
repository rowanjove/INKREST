"""Push task list updates to connected /ws/tasks clients."""

from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket

_clients: Set[WebSocket] = set()
_dirty = asyncio.Event()
_loop_task: asyncio.Task | None = None
_main_loop: asyncio.AbstractEventLoop | None = None
_COALESCE_SEC = 0.35


def bind_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def notify_tasks_changed() -> None:
    """Mark task snapshot dirty; safe from sync worker threads."""
    loop = _main_loop
    if loop is not None and loop.is_running():
        loop.call_soon_threadsafe(_dirty.set)
    else:
        _dirty.set()


async def _broadcast_loop() -> None:
    while True:
        await _dirty.wait()
        _dirty.clear()
        await asyncio.sleep(_COALESCE_SEC)
        while _dirty.is_set():
            _dirty.clear()
            await asyncio.sleep(_COALESCE_SEC)
        if not _clients:
            continue
        try:
            from web.context import _get_task_manager

            tasks = _get_task_manager().list_tasks()
        except Exception:
            continue
        dead: list[WebSocket] = []
        for ws in list(_clients):
            try:
                await ws.send_json(tasks)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.discard(ws)


async def register_client(ws: WebSocket) -> None:
    _clients.add(ws)


async def unregister_client(ws: WebSocket) -> None:
    _clients.discard(ws)


def start_task_broadcast_loop() -> asyncio.Task:
    """Lifespan hook: keep coalesced broadcaster alive."""
    loop = asyncio.get_running_loop()
    bind_main_loop(loop)
    global _loop_task
    _loop_task = loop.create_task(_broadcast_loop())
    return _loop_task