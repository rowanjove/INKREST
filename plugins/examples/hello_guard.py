"""Example quality guard plugin — copy to plugins/ for local experiments."""

from __future__ import annotations

from novel_agent.plugins.base import PluginBase, PluginContext, PluginMeta, PluginType


class HelloGuardPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="hello-guard",
            display_name="Hello Guard（示例）",
            description="演示质量门禁插件：正文过短时报 WARN。",
            plugin_type=PluginType.QUALITY_GUARD,
            tags=["example"],
        )

    def on_activate(self, context: PluginContext) -> None:
        self._ctx = context

    def check_chapter(self, chapter_id: str, text: str, **kwargs):
        if len((text or "").strip()) < 200:
            return {"pass": False, "level": "warn", "message": "示例门禁：正文少于 200 字"}
        return {"pass": True, "level": "info", "message": "Hello Guard OK"}


PLUGIN_CLASS = HelloGuardPlugin