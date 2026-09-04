from novel_agent.plugins.base import PluginMeta, PluginType, WebExtensionPlugin


class DualRegionPlugin(WebExtensionPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="dual-region-starter",
            display_name="双区域套件模版",
            version="1.0.0",
            plugin_type=PluginType.WEB_EXTENSION,
        )


PLUGIN_CLASS = DualRegionPlugin
