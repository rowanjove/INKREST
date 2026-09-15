# Inkrest Plugin SDK (2.0)

Official Python SDK for authoring plugins and extensions for the Inkrest novel generation platform.

## Features

- **Standard Base Classes**: `PluginBase`, `WebExtensionPlugin`, `PipelineHookPlugin`, etc.
- **Hook Specifications & Implementation**: Clean `@hookspec` and `@hookimpl` decorators.
- **Contract-Based Testing**: `PluginTestHost` with built-in mock services (`MockProjectService`, `MockLLMService`, `MockEventBus`).
- **Strict Capabilities & RPC Compatibility**: View RPC is allowlisted. Host-side Worker isolation exists but is not the default production loader; trusted plugins still activate in-process.

## Installation

```bash
pip install inkrest-plugin-sdk
```

## Quick Start

```python
from inkrest_sdk import PluginBase, PluginMeta, PluginType, hookimpl

class MyInspectorPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="my-inspector",
            display_name="线索审查器",
            version="1.0.0",
            plugin_type=PluginType.PIPELINE_HOOK,
        )

    @hookimpl
    def before_chapter_generation(self, chapter_outline: dict) -> dict:
        # Inspect or augment chapter outlines
        return chapter_outline
```
