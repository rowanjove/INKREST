"""Foreshadow Inspector - Showcase Plugin for INKREST Plugin Platform 2.0.

Demonstrates:
- Multiple contributions: command, validator, sidebar navigation
- Service dependency on inkrest.project.reader & publishing foreshadow.service
- CapabilityBroker project_read & model_access usage
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from novel_agent.plugins.base import PluginBase, PluginContext, PluginMeta, PluginType


class ForeshadowService:
    """Service exposed to other plugins and host via ServiceRegistry."""

    def __init__(self, inspector: ForeshadowInspector) -> None:
        self.inspector = inspector

    def get_tracked_foreshadows(self) -> List[Dict[str, Any]]:
        return self.inspector.foreshadow_db


class ForeshadowInspector(PluginBase):
    """Inspects narrative foreshadowing continuity across chapters."""

    def __init__(self) -> None:
        self.context: Optional[PluginContext] = None
        self.foreshadow_db: List[Dict[str, Any]] = []

    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="inkrest.foreshadow-inspector",
            display_name="伏笔完整性检测器",
            version="1.0.0",
            description="智能扫描长篇小说前后伏笔、呼应状态与一致性风险",
            author="INKREST Team",
            icon="inspection",
            plugin_type=PluginType.QUALITY_GUARD,
        )

    def on_activate(self, context: PluginContext) -> None:
        self.context = context
        # Provide service if service registry available
        service_registry = getattr(context, "services", None)
        if service_registry:
            service_registry.register("foreshadow.service", ForeshadowService(self), owner=self.get_meta().name)

        if context.logger:
            context.logger.info("Foreshadow Inspector activated successfully.")

    def on_deactivate(self) -> None:
        if self.context and getattr(self.context, "services", None):
            self.context.services.unregister("foreshadow.service")

    # Command Handler
    def scan_foreshadows(self, project_id: str = "demo") -> Dict[str, Any]:
        """Scan project chapters for active and resolved foreshadowing."""
        # Uses broker to read chapters safely
        broker = getattr(self.context, "broker", None)
        if broker:
            chapter = broker.project.read_chapter(project_id, "001")
            content = chapter.get("content", "") if chapter else ""
        else:
            content = ""

        found = [
            {"id": "fs_01", "name": "神秘玉佩的裂纹", "status": "planted", "chapter": "001"},
            {"id": "fs_02", "name": "黑衣人的半截短剑", "status": "resolved", "chapter": "005"},
        ]
        self.foreshadow_db = found
        return {"project_id": project_id, "total_found": len(found), "items": found}

    # Validator Handler
    def check_consistency(self, chapter_text: str, context: Any = None) -> List[Dict[str, Any]]:
        """Run consistency checks on chapter text."""
        issues = []
        if "玉佩" in chapter_text and "碎裂" in chapter_text:
            issues.append({
                "rule": "foreshadow_consistency",
                "severity": "info",
                "message": "检测到玉佩伏笔触发情节，请核对前文对应章节的一致性描述",
            })
        return issues


PLUGIN_CLASS = ForeshadowInspector
