"""Push task list updates to connected /ws/tasks clients."""

from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket

_clients: Set[WebSocket] = set()
_dirty: asyncio.Event | None = None
_dirty_pending = False
_loop_task: asyncio.Task | None = None
_main_loop: asyncio.AbstractEventLoop | None = None
_COALESCE_SEC = 0.35


def _get_dirty_event() -> asyncio.Event:
    global _dirty, _dirty_pending
    if _dirty is None:
        _dirty = asyncio.Event()
        if _dirty_pending:
            _dirty.set()
            _dirty_pending = False
    return _dirty


def _mark_dirty_on_loop() -> None:
    _get_dirty_event().set()


def bind_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def notify_tasks_changed() -> None:
    """Mark task snapshot dirty; safe from sync worker threads."""
    global _dirty_pending
    loop = _main_loop
    if loop is not None and loop.is_running():
        loop.call_soon_threadsafe(_mark_dirty_on_loop)
    else:
        _dirty_pending = True


def broadcast_progress(msg: dict) -> None:
    """Immediately broadcast a progress message to all connected clients."""
    loop = _main_loop
    if loop is not None and loop.is_running():
        loop.call_soon_threadsafe(lambda: asyncio.create_task(_send_to_all(msg)))

async def _send_to_all(msg: dict) -> None:
    if not _clients:
        return
    dead: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


async def _broadcast_loop() -> None:
    dirty = _get_dirty_event()
    while True:
        await dirty.wait()
        dirty.clear()
        await asyncio.sleep(_COALESCE_SEC)
        while dirty.is_set():
            dirty.clear()
            await asyncio.sleep(_COALESCE_SEC)
        if not _clients:
            continue
        try:
            from web.context import get_root_dir
            from web.project_task_registry import ProjectTaskRegistry

            # Always broadcast the currently active project's task list.
            # Never spawn a manager just to answer a WS poll for an idle root.
            manager = ProjectTaskRegistry.shared().peek(get_root_dir())
            if manager is None:
                from web.context import _get_task_manager

                manager = _get_task_manager()
            tasks = manager.list_tasks()
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
    _get_dirty_event()
    _loop_task = loop.create_task(_broadcast_loop())
    return _loop_task
