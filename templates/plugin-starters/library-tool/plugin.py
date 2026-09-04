from novel_agent.plugins.base import PluginMeta, PluginType, WebExtensionPlugin


class LibraryToolPlugin(WebExtensionPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="library-tool-starter",
            display_name="书库工具模版",
            version="1.0.0",
            plugin_type=PluginType.WEB_EXTENSION,
        )


PLUGIN_CLASS = LibraryToolPlugin
