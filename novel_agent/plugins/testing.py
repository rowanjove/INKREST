"""PluginTestHost and Mock services for testing INKREST plugins without full runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from novel_agent.logging_config import get_logger
from novel_agent.plugins.base import PluginBase, PluginContext, PluginEvent
from novel_agent.plugins.capability_broker import CapabilityBroker
from novel_agent.plugins.manifest import load_manifest
from novel_agent.plugins.services import (
    SERVICE_EVENT_BUS,
    SERVICE_LLM,
    SERVICE_PROJECT_READER,
    SERVICE_PROJECT_WRITER,
    SERVICE_STORAGE,
    ServiceRegistry,
)

logger = get_logger("plugins.testing")


class MockProjectService:
    """In-memory mock for project files and chapters."""

    def __init__(self) -> None:
        self.chapters: Dict[str, Dict[str, Any]] = {}
        self.outlines: Dict[str, Any] = {}

    def add_chapter(self, chapter_id: str, title: str = "", content: str = "") -> None:
        self.chapters[chapter_id] = {
            "id": chapter_id,
            "title": title or f"Chapter {chapter_id}",
            "content": content,
        }

    def read_chapter(self, project_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        return self.chapters.get(chapter_id)

    def write_chapter(self, project_id: str, chapter_id: str, data: Dict[str, Any]) -> bool:
        self.chapters[chapter_id] = data
        return True


class MockLLMService:
    """In-memory mock for LLM completion responses."""

    def __init__(self) -> None:
        self.responses: Dict[str, str] = {}
        self.history: List[str] = []

    def set_response(self, prompt_keyword: str, response: str) -> None:
        self.responses[prompt_keyword] = response

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.history.append(prompt)
        for kw, resp in self.responses.items():
            if kw in prompt:
                return resp
        return f"[MockLLM Response to: {prompt[:30]}]"


class MockEventBus:
    """Mock event bus recording published events."""

    def __init__(self) -> None:
        self.published: List[PluginEvent] = []
        self.subscribers: Dict[str, List[Callable[..., Any]]] = {}

    def subscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        self.subscribers.setdefault(event_name, []).append(callback)

    def publish(self, event_name: str, data: Dict[str, Any]) -> None:
        event = PluginEvent(name=event_name, data=data)
        self.published.append(event)
        for cb in self.subscribers.get(event_name, []):
            cb(event)


class PluginTestHost:
    """Test harness for isolated plugin unit and contract tests."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path("./test_workspace")
        self.project = MockProjectService()
        self.llm = MockLLMService()
        self.event_bus = MockEventBus()
        self.services = ServiceRegistry()

        # Register standard services
        self.services.register(SERVICE_PROJECT_READER, self.project)
        self.services.register(SERVICE_PROJECT_WRITER, self.project)
        self.services.register(SERVICE_LLM, self.llm)
        self.services.register(SERVICE_EVENT_BUS, self.event_bus)

    def create_context(
        self,
        plugin_id: str,
        granted_capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> PluginContext:
        """Create a mock PluginContext equipped with mock capability brokers."""
        caps = granted_capabilities or ["project_read", "project_write", "model_access"]
        broker = CapabilityBroker(plugin_id, caps, self.root_dir)
        ctx = PluginContext(
            root_dir=self.root_dir,
            config=config or {},
            event_bus=self.event_bus,
            logger=get_logger(f"test.{plugin_id}"),
        )
        ctx.broker = broker  # type: ignore[attr-defined]
        return ctx

    def activate_plugin(
        self,
        plugin: PluginBase,
        granted_capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> PluginContext:
        """Activate a plugin instance within the test host."""
        meta = plugin.get_meta()
        ctx = self.create_context(meta.name, granted_capabilities, config)
        plugin.on_activate(ctx)
        return ctx
