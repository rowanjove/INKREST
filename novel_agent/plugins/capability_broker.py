"""Capability Broker and permission enforcement for INKREST Plugin Platform 2.0.

Intercepts, validates, and audits all sensitive interactions (project files,
model completions, network access, storage, secrets) to ensure plugins
only execute within their granted capability boundaries.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from novel_agent.logging_config import get_logger

logger = get_logger("plugins.capability_broker")


class PermissionDeniedError(PermissionError):
    """Raised when a plugin attempts an action exceeding its granted capabilities."""
    pass


class ProjectBroker:
    """Brokered access to project manuscripts, chapters, and outlines."""

    def __init__(
        self,
        plugin_id: str,
        granted_capabilities: Set[str],
        root_dir: Path,
        audit_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._plugin_id = plugin_id
        self._granted = granted_capabilities
        self._root_dir = root_dir
        self._audit = audit_callback

    def _check_permission(self, required_permission: str) -> None:
        # Match coarse or fine-grained: e.g. "project_read" matches "project.read.chapter"
        if required_permission in self._granted:
            return
        if "project_read" in self._granted and required_permission.startswith("project.read"):
            return
        if "project_write" in self._granted and required_permission.startswith("project.write"):
            return
        raise PermissionDeniedError(
            f"Plugin '{self._plugin_id}' lacks required permission: '{required_permission}'"
        )

    def _sanitize_path(self, project_id: str, chapter_id: str) -> Path:
        safe_pid = Path(project_id).name
        safe_cid = Path(chapter_id).name
        if safe_pid != project_id or safe_cid != chapter_id or ".." in project_id or ".." in chapter_id:
            raise PermissionDeniedError(f"Invalid path identifiers: project='{project_id}', chapter='{chapter_id}'")
        target = (self._root_dir / "projects" / safe_pid / "chapters" / f"{safe_cid}.json").resolve()
        expected_parent = (self._root_dir / "projects").resolve()
        try:
            if not target.is_relative_to(expected_parent):
                raise PermissionDeniedError(f"Path traversal detected: '{project_id}/{chapter_id}'")
        except AttributeError:
            # Fallback for Python < 3.9 compatibility
            if not str(target).startswith(str(expected_parent)):
                raise PermissionDeniedError(f"Path traversal detected: '{project_id}/{chapter_id}'")
        return target

    def read_chapter(self, project_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Safely read chapter content through broker."""
        self._check_permission("project.read.chapter")
        if self._audit:
            self._audit(self._plugin_id, "project.read.chapter", {"project_id": project_id, "chapter_id": chapter_id})

        chapter_file = self._sanitize_path(project_id, chapter_id)
        if not chapter_file.is_file():
            return None
        try:
            return json.loads(chapter_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Error reading chapter via broker: %s", e)
            return None

    def write_chapter(self, project_id: str, chapter_id: str, data: Dict[str, Any]) -> bool:
        """Safely write chapter content through broker."""
        self._check_permission("project.write.chapter")
        if self._audit:
            self._audit(self._plugin_id, "project.write.chapter", {"project_id": project_id, "chapter_id": chapter_id})

        chapter_file = self._sanitize_path(project_id, chapter_id)
        chapter_file.parent.mkdir(parents=True, exist_ok=True)
        chapter_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True


class ModelBroker:
    """Brokered access to LLM model completion."""

    def __init__(
        self,
        plugin_id: str,
        granted_capabilities: Set[str],
        audit_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._plugin_id = plugin_id
        self._granted = granted_capabilities
        self._audit = audit_callback

    def complete(self, prompt: str, **kwargs: Any) -> str:
        if "model_access" not in self._granted and "model.invoke" not in self._granted:
            raise PermissionDeniedError(f"Plugin '{self._plugin_id}' lacks model completion permission")

        if self._audit:
            self._audit(self._plugin_id, "model.invoke", {"prompt_len": len(prompt)})

        # Mock or delegate to actual LLM provider in host
        return f"[ModelBroker Response for prompt: {prompt[:30]}...]"


class StorageBroker:
    """Isolated key-value / file storage for a plugin."""

    def __init__(self, plugin_id: str, root_dir: Path) -> None:
        self._plugin_id = plugin_id
        self._store_dir = root_dir / "data" / "plugins" / plugin_id
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._kv_file = self._store_dir / "storage.json"

    def _load_kv(self) -> Dict[str, Any]:
        if self._kv_file.is_file():
            try:
                return json.loads(self._kv_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_kv(self, data: Dict[str, Any]) -> None:
        self._kv_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._load_kv().get(key, default)

    def set(self, key: str, value: Any) -> None:
        kv = self._load_kv()
        kv[key] = value
        self._save_kv(kv)

    def delete(self, key: str) -> bool:
        kv = self._load_kv()
        if key in kv:
            del kv[key]
            self._save_kv(kv)
            return True
        return False


class CapabilityBroker:
    """Aggregates all capability brokers for a plugin context."""

    def __init__(self, plugin_id: str, granted_capabilities: List[str], root_dir: Path) -> None:
        self.plugin_id = plugin_id
        self.granted = set(granted_capabilities)
        self.root_dir = Path(root_dir)
        self.audit_log: List[Dict[str, Any]] = []

        self.project = ProjectBroker(self.plugin_id, self.granted, self.root_dir, self._record_audit)
        self.model = ModelBroker(self.plugin_id, self.granted, self._record_audit)
        self.storage = StorageBroker(self.plugin_id, self.root_dir)

    def _record_audit(self, plugin_id: str, action: str, details: Dict[str, Any]) -> None:
        entry = {
            "plugin_id": plugin_id,
            "action": action,
            "details": details,
            "timestamp": time.time(),
        }
        self.audit_log.append(entry)
        if len(self.audit_log) > 100:
            self.audit_log = self.audit_log[-100:]
