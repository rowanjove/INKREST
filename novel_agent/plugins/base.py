from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PluginType(Enum):
    PIPELINE_HOOK = "pipeline_hook"
    QUALITY_GUARD = "quality_guard"
    EXPORTER = "exporter"
    LLM_PROVIDER = "llm_provider"
    AGENT_OVERRIDE = "agent_override"
    PIPELINE_PHASE = "pipeline_phase"
    VECTOR_STORE = "vector_store"
    EMBEDDING_PROVIDER = "embedding_provider"
    APPROVAL_STRATEGY = "approval_strategy"
    RULES_EXTENSION = "rules_extension"
    PROMPT_ENHANCER = "prompt_enhancer"
    EVENT_LISTENER = "event_listener"
    WEB_EXTENSION = "web_extension"
    COMMAND = "command"
    SENSITIVE_SCANNER = "sensitive_scanner"


@dataclass(frozen=True)
class PluginMeta:
    name: str                    # Unique ID, e.g., "docx-exporter"
    version: str = "0.1.0"
    display_name: str = ""       # UI display name, e.g., "Word Document Exporter"
    description: str = ""        # Brief description
    author: str = ""
    icon: str = ""               # Icon identifier or emoji
    plugin_type: PluginType = PluginType.EVENT_LISTENER
    requires: List[str] = field(default_factory=list)      # Dependencies on other plugins
    min_core_version: str = "0.1.0"
    config_schema: Dict[str, Any] = field(default_factory=dict)  # JSON Schema for config
    tags: List[str] = field(default_factory=list)          # Tag list
    capabilities: List[str] = field(default_factory=list)  # Additional declared permissions


@dataclass
class PluginContext:
    root_dir: Path
    config: Dict[str, Any]
    event_bus: Optional[Any] = None
    logger: Optional[Any] = None
    plugin_home: Optional[Path] = None


class PluginBase(ABC):
    """Base class for all plugins."""

    @abstractmethod
    def get_meta(self) -> PluginMeta:
        """Return the plugin's metadata."""
        pass

    def on_activate(self, context: PluginContext) -> None:
        """Called when the plugin is enabled."""
        pass

    def on_deactivate(self) -> None:
        """Called when the plugin is disabled."""
        pass

    def get_config_ui(self) -> Optional[Dict[str, Any]]:
        """Return UI form representation for configuration."""
        return None


# 1. Pipeline Hook
class PipelineHookPlugin(PluginBase):
    """Hooks run before/after pipeline steps."""

    def before_outline(self, theme: str, genre: str, **kwargs) -> Dict[str, Any]:
        return kwargs

    def after_outline(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        return outline

    def before_planning(self, ctx: Any) -> Any:
        return ctx

    def after_planning(self, ctx: Any, plan: Dict[str, Any]) -> Dict[str, Any]:
        return plan

    def before_scene_write(self, scene: Dict[str, Any], context_text: str) -> str:
        return context_text

    def after_scene_write(self, scene: Dict[str, Any], draft: str) -> str:
        return draft

    def before_merge(self, scene_texts: List[str]) -> List[str]:
        return scene_texts

    def after_merge(self, merged: str) -> str:
        return merged

    def before_stitch(self, scenes: List[str]) -> List[str]:
        return scenes

    def after_stitch(self, stitched: str) -> str:
        return stitched

    def before_style_edit(self, text: str) -> str:
        return text

    def after_style_edit(self, text: str) -> str:
        return text

    def before_audit(self, ctx: Any) -> Any:
        return ctx

    def after_audit(self, ctx: Any, audit: Dict[str, Any]) -> Dict[str, Any]:
        return audit

    def after_state_extract(self, ctx: Any, state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    def after_state_persist(self, ctx: Any) -> None:
        pass

    def after_vector_index(self, ctx: Any, chunks: List[Any]) -> None:
        pass

    def on_chapter_complete(self, ctx: Any, result: Any) -> None:
        pass

    def on_novel_complete(self, results: List[Any]) -> None:
        pass


# 2. Quality Guard
class QualityGuardPlugin(PluginBase):
    @abstractmethod
    def check(self, text: str, context: Any) -> Any:
        """Run quality checks, return checking results."""
        pass

    def get_guard_info(self) -> Dict[str, Any]:
        meta = self.get_meta()
        return {
            "name": meta.name,
            "title": meta.display_name or meta.name,
            "level": 2,
            "description": meta.description
        }


# 3. Exporter
class ExporterPlugin(PluginBase):
    @abstractmethod
    def get_format(self) -> str:
        pass

    def get_file_extension(self) -> str:
        return f".{self.get_format().lower()}"

    def get_display_name(self) -> str:
        meta = self.get_meta()
        return meta.display_name or self.get_format().upper()

    @abstractmethod
    def export(self, root_dir: Path, output_path: Path, chapter_ids: Optional[List[str]] = None, title: str = "", **kwargs) -> Path:
        """Export chapters to the output path."""
        pass


# 4. LLM Provider
class LLMProviderPlugin(PluginBase):
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def create_client(self, config: Dict[str, Any]) -> Any:
        pass

    def get_config_fields(self) -> List[Dict[str, Any]]:
        """Return fields description for model UI dynamic rendering."""
        return []


# 5. Agent Override
class AgentOverridePlugin(PluginBase):
    @abstractmethod
    def get_target_role(self) -> str:
        """Target role to override, e.g. 'writer', 'auditor'."""
        pass

    @abstractmethod
    def create_agent(self, llm: Any, prompts: Any) -> Any:
        """Create and return the replacement agent instance."""
        pass

    def get_priority(self) -> int:
        """Lower value runs first."""
        return 100


# 6. Pipeline Phase
class PipelinePhasePlugin(PluginBase):
    @abstractmethod
    def get_phase_name(self) -> str:
        pass

    def get_insert_after(self) -> Optional[str]:
        """Name of builtin phase to insert after. None means append to end."""
        return None

    @abstractmethod
    def execute(self, ctx: Any) -> Any:
        pass

    async def aexecute(self, ctx: Any) -> Any:
        return self.execute(ctx)


# 7. Vector Store
class VectorStorePlugin(PluginBase):
    @abstractmethod
    def get_store_name(self) -> str:
        pass

    @abstractmethod
    def create_store(self, config: Dict[str, Any], root_dir: Path) -> Any:
        pass


# 8. Embedding Provider
class EmbeddingProviderPlugin(PluginBase):
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass


# 9. Approval Strategy
class ApprovalStrategyPlugin(PluginBase):
    @abstractmethod
    def get_strategy_name(self) -> str:
        pass

    @abstractmethod
    def request_approval(self, chapter_id: str, chapter_dir: Path) -> bool:
        pass

    async def arequest_approval(self, chapter_id: str, chapter_dir: Path) -> bool:
        return self.request_approval(chapter_id, chapter_dir)


# 10. Rules Extension
class RulesExtensionPlugin(PluginBase):
    @abstractmethod
    def get_extra_rules(self) -> Dict[str, Any]:
        pass

    def get_prompt_section(self) -> str:
        return ""


# 11. Prompt Enhancer
class PromptEnhancerPlugin(PluginBase):
    @abstractmethod
    def get_target_roles(self) -> List[str]:
        """Returns roles to enhance, '*' for all."""
        pass

    @abstractmethod
    def enhance(self, role: str, original_prompt: str, context: Dict[str, Any]) -> str:
        """Enhances and returns the prompt."""
        pass


# 12. Event Listener
@dataclass(frozen=True)
class PluginEvent:
    name: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: 0.0)


class EventListenerPlugin(PluginBase):
    @abstractmethod
    def get_subscriptions(self) -> List[str]:
        pass

    @abstractmethod
    def on_event(self, event: PluginEvent) -> None:
        pass


# 13. Web Extension
class WebExtensionPlugin(PluginBase):
    def get_router(self) -> Optional[Any]:
        """Returns a fastapi.APIRouter instance if any."""
        return None

    def get_frontend_manifest(self) -> Optional[Dict[str, Any]]:
        """Returns metadata for frontend UI integration."""
        return None


# 14. Sensitive Scanner
class SensitiveScannerPlugin(PluginBase):
    @abstractmethod
    def scan(self, text: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Returns scan report like {"found": [...], "count": N}"""
        pass


# 15. Command
@dataclass(frozen=True)
class CommandSpec:
    name: str
    description: str
    help_text: str = ""


class CommandPlugin(PluginBase):
    @abstractmethod
    def get_commands(self) -> List[CommandSpec]:
        pass

    @abstractmethod
    def execute(self, command: str, args: Dict[str, Any]) -> Any:
        pass
