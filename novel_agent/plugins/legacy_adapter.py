"""Legacy Plugin Adapter for INKREST Plugin Platform 2.0.

Provides 100% backward compatibility for existing V1 plugins inheriting
from PluginBase and declaring a single PluginType.
Translates V1 lifecycle methods, hooks, and types into V2 Contributions and Hook implementations.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from novel_agent.plugins.base import (
    CommandPlugin,
    ExporterPlugin,
    PipelineHookPlugin,
    PluginBase,
    PluginType,
    PromptEnhancerPlugin,
    QualityGuardPlugin,
    WebExtensionPlugin,
)
from novel_agent.plugins.contributions import (
    CommandContribution,
    ContributionRegistry,
    ExporterContribution,
    PipelineHookContribution,
    PromptEnhancerContribution,
    ValidatorContribution,
    ViewContribution,
)
from novel_agent.plugins.hooks import HookRegistry


class LegacyPluginAdapter:
    """Adapts a legacy V1 plugin into V2 Contribution and Hook registries."""

    def __init__(self, plugin: PluginBase) -> None:
        self.plugin = plugin
        self.meta = plugin.get_meta()
        self.plugin_id = self.meta.name

    def adapt_into_registries(
        self,
        contributions: ContributionRegistry,
        hooks: HookRegistry,
    ) -> None:
        """Register all legacy capabilities into the V2 registries."""
        ptype = self.meta.plugin_type

        # 1. PipelineHookPlugin
        if isinstance(self.plugin, PipelineHookPlugin) or ptype == PluginType.PIPELINE_HOOK:
            self._adapt_pipeline_hooks(contributions, hooks)

        # 2. Quality Guard
        if isinstance(self.plugin, QualityGuardPlugin) or ptype == PluginType.QUALITY_GUARD:
            handler = getattr(self.plugin, "check", None) or getattr(self.plugin, "check_chapter", None)
            contributions.register_validator(
                ValidatorContribution(
                    id=f"{self.plugin_id}.guard",
                    label=self.meta.display_name or self.plugin_id,
                    scope="chapter",
                    handler=handler,
                )
            )

        # 3. ExporterPlugin
        if isinstance(self.plugin, ExporterPlugin) or ptype == PluginType.EXPORTER:
            fmt = getattr(self.plugin, "get_format", lambda: "custom")()
            contributions.register_exporter(
                ExporterContribution(
                    id=f"{self.plugin_id}.exporter",
                    format=fmt,
                    label=self.meta.display_name or f"{fmt.upper()} Exporter",
                    handler=getattr(self.plugin, "export", None),
                )
            )

        # 4. CommandPlugin
        if isinstance(self.plugin, CommandPlugin) or ptype == PluginType.COMMAND:
            specs = getattr(self.plugin, "get_commands", lambda: [])()
            for spec in specs:
                contributions.register_command(
                    CommandContribution(
                        id=f"{self.plugin_id}.{spec.name}",
                        title=spec.title or spec.name,
                        category=spec.category or "General",
                        keybinding=spec.keybinding or "",
                        handler=spec.handler,
                    )
                )

        # 5. PromptEnhancerPlugin
        if isinstance(self.plugin, PromptEnhancerPlugin) or ptype == PluginType.PROMPT_ENHANCER:
            contributions.register_prompt_enhancer(
                PromptEnhancerContribution(
                    id=f"{self.plugin_id}.enhancer",
                    target="scene",
                    handler=getattr(self.plugin, "enhance_prompt", None),
                )
            )

    def _adapt_pipeline_hooks(
        self,
        contributions: ContributionRegistry,
        hooks: HookRegistry,
    ) -> None:
        phases = [
            "before_outline",
            "after_outline",
            "before_planning",
            "after_planning",
            "before_scene_write",
            "after_scene_write",
            "before_merge",
            "after_merge",
            "before_stitch",
            "after_stitch",
            "before_refine",
            "after_refine",
        ]
        for phase in phases:
            fn = getattr(self.plugin, phase, None)
            if fn and callable(fn):
                # Register in ContributionRegistry
                contributions.register_pipeline_hook(
                    PipelineHookContribution(
                        id=f"{self.plugin_id}.{phase}",
                        phase=phase,
                        handler=fn,
                    )
                )
                # Register in HookRegistry
                hooks.register_impl(
                    hook_name=phase,
                    plugin_id=self.plugin_id,
                    impl_fn=fn,
                )
