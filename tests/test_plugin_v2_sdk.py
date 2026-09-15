import sys
from pathlib import Path

# Add the packages/inkrest-plugin-sdk directory to sys.path
sdk_path = Path(__file__).resolve().parent.parent / "packages" / "inkrest-plugin-sdk"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))

import inkrest_sdk
from inkrest_sdk import (
    PluginBase,
    PluginMeta,
    PluginType,
    hookimpl,
    PluginTestHost,
)


class SampleSdkPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="sdk_sample",
            display_name="SDK示例插件",
            version="2.0.0",
            plugin_type=PluginType.PIPELINE_HOOK,
        )

    @hookimpl
    def custom_filter(self, text: str) -> str:
        return f"[filtered]{text}"


def test_sdk_classes_and_hookimpl():
    plugin = SampleSdkPlugin()
    meta = plugin.get_meta()
    assert meta.name == "sdk_sample"
    assert meta.version == "2.0.0"
    assert meta.plugin_type == PluginType.PIPELINE_HOOK

    # Check hookimpl attribute
    assert hasattr(plugin.custom_filter, "__hookimpl__")
    assert plugin.custom_filter("hello") == "[filtered]hello"


def test_sdk_testing_harness():
    host = PluginTestHost()
    host.llm.set_response("Hello", "Test prompt response")
    
    res = host.llm.complete("Hello world")
    assert res == "Test prompt response"
    assert len(host.llm.history) == 1
