"""Run async coroutines from sync callers without nesting asyncio.run in a live loop."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Coroutine, TypeVar

T = TypeVar("T")


def _bridge_worker_count() -> int:
    raw = os.environ.get("NOVEL_AGENT_ASYNC_BRIDGE_WORKERS", "8").strip()
    try:
        count = int(raw)
    except ValueError:
        count = 8
    return max(2, min(count, 32))


# 声明一个全局线程池以重用线程，防止在同步/异步桥接时频繁创建与注销原生 OS 线程导致的性能抖动
_BRIDGE_EXECUTOR = ThreadPoolExecutor(
    max_workers=_bridge_worker_count(),
    thread_name_prefix="novel-async-bridge",
)


def run_sync(coro: Coroutine[object, object, T]) -> T:
    """Execute *coro* from sync code; safe when an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    # 提交给全局重用的线程池执行，避免频繁创建/关闭线程
    future = _BRIDGE_EXECUTOR.submit(asyncio.run, coro)
    return future.result()