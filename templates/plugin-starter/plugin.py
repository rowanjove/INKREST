"""Plugin starter — copy folder, edit inkrest.plugin.json, zip and install via 插件页."""

from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType


class MyPlugin(PipelineHookPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="my-plugin",
            display_name="我的插件",
            version="1.0.0",
            description="简要说明插件用途",
            plugin_type=PluginType.PIPELINE_HOOK,
            config_schema={
                "type": "object",
                "properties": {
                    "enabled_feature": {
                        "type": "boolean",
                        "title": "启用扩展功能",
                        "default": True,
                    }
                },
            },
        )

    def after_outline(self, outline):
        if self.context and self.context.config.get("enabled_feature", True):
            outline.setdefault("plugin_notes", []).append("my-plugin")
        return outline


PLUGIN_CLASS = MyPlugin