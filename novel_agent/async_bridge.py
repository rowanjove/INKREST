"""Run async coroutines from sync callers without nesting asyncio.run in a live loop."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Coroutine, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[object, object, T]) -> T:
    """Execute *coro* from sync code; safe when an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="novel-async-bridge") as pool:
        return pool.submit(asyncio.run, coro).result()