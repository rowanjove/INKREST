"""Inkrest Plugin SDK 2.0.

Provides standard abstractions, hook decorators, contribution models, and
testing utilities for building Inkrest plugins.
"""

from __future__ import annotations

# Re-export core classes with fallback
try:
    from novel_agent.plugins.base import (
        CommandPlugin,
        CommandSpec,
        EventListenerPlugin,
        ExporterPlugin,
        LLMProviderPlugin,
        PipelineHookPlugin,
        PipelinePhasePlugin,
        PluginBase,
        PluginContext,
        PluginEvent,
        PluginMeta,
        PluginType,
        PromptEnhancerPlugin,
        QualityGuardPlugin,
        RulesExtensionPlugin,
        SensitiveScannerPlugin,
        VectorStorePlugin,
        WebExtensionPlugin,
    )
    from novel_agent.plugins.hooks import (
        HookContract,
        HookError,
        HookExecutionError,
        HookTimeoutError,
        hookimpl,
        hookspec,
    )
    from novel_agent.plugins.contributions import (
        CommandContribution,
        ViewContribution,
        ValidatorContribution,
        PipelineHookContribution,
        ExporterContribution,
        PromptEnhancerContribution,
    )
    from novel_agent.plugins.testing import (
        MockEventBus,
        MockLLMService,
        MockProjectService,
        PluginTestHost,
    )
except ImportError:
    # Standalone mode fallback implementations if novel_agent is not directly on sys.path
    from enum import Enum
    from dataclasses import dataclass, field
    from typing import Any, Callable, Dict, List, Optional

    class PluginType(str, Enum):
        PIPELINE_HOOK = "pipeline_hook"
        QUALITY_GUARD = "quality_guard"
        EXPORTER = "exporter"
        LLM_PROVIDER = "llm_provider"
        COMMAND = "command"
        WEB_EXTENSION = "web_extension"

    @dataclass
    class PluginMeta:
        name: str
        display_name: str
        version: str
        plugin_type: PluginType
        description: str = ""
        author: str = ""
        entry: str = ""

    class PluginBase:
        def get_meta(self) -> PluginMeta:
            raise NotImplementedError

    class PluginContext:
        def __init__(self, services: Optional[Dict[str, Any]] = None):
            self.services = services or {}

    def hookspec(func: Any = None, **kwargs: Any) -> Any:
        def decorator(f: Any) -> Any:
            setattr(f, "_is_hookspec", True)
            return f
        return decorator(func) if func else decorator

    def hookimpl(func: Any = None, **kwargs: Any) -> Any:
        def decorator(f: Any) -> Any:
            setattr(f, "_is_hookimpl", True)
            return f
        return decorator(func) if func else decorator


__version__ = "2.0.0"

__all__ = [
    "PluginBase",
    "PluginMeta",
    "PluginType",
    "PluginContext",
    "PluginEvent",
    "PipelineHookPlugin",
    "QualityGuardPlugin",
    "ExporterPlugin",
    "LLMProviderPlugin",
    "WebExtensionPlugin",
    "CommandPlugin",
    "CommandSpec",
    "hookspec",
    "hookimpl",
    "HookContract",
    "CommandContribution",
    "ViewContribution",
    "PluginTestHost",
    "MockProjectService",
    "MockLLMService",
    "MockEventBus",
]
