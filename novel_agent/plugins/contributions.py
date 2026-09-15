"""Contribution points registry for INKREST Plugin Platform 2.0.

Decouples plugin capabilities from a single rigid PluginType.
Allows a single plugin to declare multiple contributions:
- commands: Actionable commands for command palette and shortcuts
- views: UI views (library_sidebar, project_sidebar, general webview)
- validators: Chapter/setting/world consistency checkers
- pipeline_hooks: Lifecycle points in novel generation pipeline
- exporters: Document/file export format handlers
- prompt_enhancers: Pre/post prompt refinement hooks
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CommandContribution:
    id: str
    title: str
    category: str = ""
    icon: str = ""
    keybinding: str = ""
    handler: Optional[Callable[..., Any]] = None


@dataclass
class ViewContribution:
    id: str
    title: str
    surface: str = "project_sidebar"  # library_sidebar, project_sidebar, webview
    view_id: str = ""
    icon: str = ""
    html: str = ""
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidatorContribution:
    id: str
    label: str = ""
    scope: str = "chapter"  # chapter, outline, world, character
    handler: Optional[Callable[..., Any]] = None


@dataclass
class PipelineHookContribution:
    id: str
    phase: str  # before_outline, after_outline, before_scene_write, etc.
    priority: int = 0
    handler: Optional[Callable[..., Any]] = None


@dataclass
class ExporterContribution:
    id: str
    format: str  # epub, pdf, docx, markdown
    label: str = ""
    handler: Optional[Callable[..., Any]] = None


@dataclass
class PromptEnhancerContribution:
    id: str
    target: str = "scene"
    priority: int = 0
    handler: Optional[Callable[..., Any]] = None


class ContributionRegistry:
    """Registry holding all contributed capabilities declared by plugins."""

    def __init__(self) -> None:
        self.commands: Dict[str, CommandContribution] = {}
        self.views: Dict[str, ViewContribution] = {}
        self.validators: Dict[str, ValidatorContribution] = {}
        self.pipeline_hooks: Dict[str, List[PipelineHookContribution]] = {}
        self.exporters: Dict[str, ExporterContribution] = {}
        self.prompt_enhancers: Dict[str, List[PromptEnhancerContribution]] = {}

    def register_command(self, cmd: CommandContribution) -> None:
        self.commands[cmd.id] = cmd

    def register_view(self, view: ViewContribution) -> None:
        self.views[view.id] = view

    def register_validator(self, val: ValidatorContribution) -> None:
        self.validators[val.id] = val

    def register_pipeline_hook(self, hook: PipelineHookContribution) -> None:
        self.pipeline_hooks.setdefault(hook.phase, []).append(hook)
        self.pipeline_hooks[hook.phase].sort(key=lambda h: h.priority, reverse=True)

    def register_exporter(self, exp: ExporterContribution) -> None:
        self.exporters[exp.id] = exp

    def register_prompt_enhancer(self, enh: PromptEnhancerContribution) -> None:
        self.prompt_enhancers.setdefault(enh.target, []).append(enh)
        self.prompt_enhancers[enh.target].sort(key=lambda e: e.priority, reverse=True)

    def load_from_manifest(self, plugin_id: str, contributes_data: Dict[str, Any]) -> None:
        """Parse contributes dictionary statically from manifest."""
        if not isinstance(contributes_data, dict):
            return

        # Commands
        for cmd in contributes_data.get("commands", []):
            if isinstance(cmd, dict) and "id" in cmd and "title" in cmd:
                cid = f"{plugin_id}.{cmd['id']}" if not cmd["id"].startswith(plugin_id) else cmd["id"]
                self.register_command(
                    CommandContribution(
                        id=cid,
                        title=str(cmd["title"]),
                        category=str(cmd.get("category", "")),
                        icon=str(cmd.get("icon", "")),
                        keybinding=str(cmd.get("keybinding", "")),
                    )
                )

        # Navigation / Views
        for nav in contributes_data.get("navigation", []):
            if isinstance(nav, dict) and "id" in nav and "title" in nav:
                vid = f"{plugin_id}.{nav['id']}" if not nav["id"].startswith(plugin_id) else nav["id"]
                self.register_view(
                    ViewContribution(
                        id=vid,
                        title=str(nav["title"]),
                        surface=str(nav.get("surface", "project_sidebar")),
                        view_id=str(nav.get("view_id", "")),
                        icon=str(nav.get("icon", "")),
                        html=str(nav.get("html", "")),
                    )
                )

        # Views generic
        for view in contributes_data.get("views", []):
            if isinstance(view, dict) and "id" in view:
                vid = f"{plugin_id}.{view['id']}" if not view["id"].startswith(plugin_id) else view["id"]
                self.register_view(
                    ViewContribution(
                        id=vid,
                        title=str(view.get("title", vid)),
                        surface=str(view.get("surface", "project_sidebar")),
                        view_id=str(view.get("view_id", "")),
                        html=str(view.get("html", "")),
                        options=view.get("options", {}),
                    )
                )

        # Validators
        for val in contributes_data.get("validators", []):
            if isinstance(val, dict) and "id" in val:
                vid = f"{plugin_id}.{val['id']}" if not val["id"].startswith(plugin_id) else val["id"]
                self.register_validator(
                    ValidatorContribution(
                        id=vid,
                        label=str(val.get("label", vid)),
                        scope=str(val.get("scope", "chapter")),
                    )
                )

        # Exporters
        for exp in contributes_data.get("exporters", []):
            if isinstance(exp, dict) and "id" in exp and "format" in exp:
                eid = f"{plugin_id}.{exp['id']}" if not exp["id"].startswith(plugin_id) else exp["id"]
                self.register_exporter(
                    ExporterContribution(
                        id=eid,
                        format=str(exp["format"]),
                        label=str(exp.get("label", eid)),
                    )
                )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all registered contributions."""
        return {
            "commands": [
                {"id": c.id, "title": c.title, "category": c.category, "icon": c.icon}
                for c in self.commands.values()
            ],
            "views": [
                {"id": v.id, "title": v.title, "surface": v.surface, "view_id": v.view_id}
                for v in self.views.values()
            ],
            "validators": [
                {"id": val.id, "label": val.label, "scope": val.scope}
                for val in self.validators.values()
            ],
            "exporters": [
                {"id": e.id, "format": e.format, "label": e.label}
                for e in self.exporters.values()
            ],
            "pipeline_hooks": {
                phase: [{"id": h.id, "priority": h.priority} for h in hooks]
                for phase, hooks in self.pipeline_hooks.items()
            },
        }
