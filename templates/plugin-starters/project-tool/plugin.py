from novel_agent.plugins.base import PluginMeta, PluginType, WebExtensionPlugin


class ProjectToolPlugin(WebExtensionPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="project-tool-starter",
            display_name="作品工具模版",
            version="1.0.0",
            plugin_type=PluginType.WEB_EXTENSION,
        )


PLUGIN_CLASS = ProjectToolPlugin
