"""One TaskManager (chapter queue) per project root."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

from web.tasks import TaskManager

_registry_singleton: Optional["ProjectTaskRegistry"] = None
_registry_lock = threading.Lock()


class ProjectTaskRegistry:
    def __init__(self) -> None:
        self._managers: Dict[str, TaskManager] = {}
        self._lock = threading.RLock()

    @classmethod
    def shared(cls) -> "ProjectTaskRegistry":
        global _registry_singleton
        with _registry_lock:
            if _registry_singleton is None:
                _registry_singleton = cls()
            return _registry_singleton

    @staticmethod
    def _key(root_dir: Path) -> str:
        return str(Path(root_dir).resolve())

    def get(self, root_dir: Path) -> TaskManager:
        key = self._key(root_dir)
        with self._lock:
            manager = self._managers.get(key)
            if manager is None:
                manager = TaskManager(root_dir)
                self._managers[key] = manager
            else:
                manager.sync_concurrency_limit()
            return manager

    def has_active_tasks(self, root_dir: Path) -> bool:
        key = self._key(root_dir)
        with self._lock:
            manager = self._managers.get(key)
            return bool(manager and manager.has_active_tasks())

    def drop(self, root_dir: Path) -> None:
        key = self._key(root_dir)
        with self._lock:
            manager = self._managers.pop(key, None)
        if manager is not None:
            manager.shutdown()
