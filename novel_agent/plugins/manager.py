import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

from novel_agent.logging_config import get_logger
from novel_agent.plugins.base import (
    ApprovalStrategyPlugin,
    AgentOverridePlugin,
    CommandPlugin,
    EmbeddingProviderPlugin,
    ExporterPlugin,
    EventListenerPlugin,
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
from novel_agent.plugins.discovery import PluginDiscovery, PluginEntry
from novel_agent.plugins.installer import install_plugin_zip, uninstall_plugin
from novel_agent.plugins.manifest import find_manifest_path, load_manifest, manifest_to_plugin_meta, ManifestError

logger = get_logger("plugins.manager")


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Any]] = {}

    def subscribe(self, event_name: str, callback: Any) -> None:
        self._subscribers.setdefault(event_name, []).append(callback)

    def unsubscribe(self, event_name: str, callback: Any) -> None:
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
            except ValueError:
                pass

    def publish(self, event_name: str, data: Dict[str, Any]) -> None:
        event = PluginEvent(name=event_name, data=data, timestamp=time.time())
        # Publish to specific topic
        for callback in self._subscribers.get(event_name, []):
            try:
                callback(event)
            except Exception as e:
                logger.error("Error in event subscriber for %s: %s", event_name, e)
        # Publish to wildcard "*" topic
        for callback in self._subscribers.get("*", []):
            try:
                callback(event)
            except Exception as e:
                logger.error("Error in event wildcard subscriber: %s", e)


class LoadedPlugin:
    def __init__(self, entry: PluginEntry, instance: PluginBase, enabled: bool = False):
        self.entry = entry
        self.instance = instance
        self.enabled = enabled
        self.meta: PluginMeta = instance.get_meta()


class PluginManager:
    def __init__(self, root_dir: Path, allow_web_extensions: bool = False):
        self.root_dir = Path(root_dir)
        self.allow_web_extensions = allow_web_extensions
        self.discovery = PluginDiscovery(self.root_dir)
        self.event_bus = EventBus()
        self.config_path = self.root_dir / "config" / "plugins.yaml"
        self.plugins: Dict[str, LoadedPlugin] = {}
        self._state_config: Dict[str, Any] = {}
        
        # Caches of active plugins grouped by type
        self._active_by_type: Dict[PluginType, List[PluginBase]] = {t: [] for t in PluginType}

    def initialize(self) -> None:
        """Scan, load, and activate enabled plugins."""
        if self.plugins:
            self.shutdown()
            self.plugins.clear()
            self._active_by_type = {t: [] for t in PluginType}
        self._load_state_config()
        discovered_entries = self.discovery.discover_all()

        for name, entry in discovered_entries.items():
            try:
                plugin_state = self._state_config.get("plugins", {}).get("registry", {}).get(name, {})
                enabled = plugin_state.get("enabled", entry.source == "entry_point")
                if entry.source == "local" and not enabled:
                    logger.info("Skipping untrusted local plugin '%s' until explicitly enabled.", name)
                    continue

                plugin_cls = entry.load_fn()
                instance = plugin_cls()
                if instance.get_meta().plugin_type == PluginType.WEB_EXTENSION and not self.allow_web_extensions:
                    logger.warning("Skipping project-scoped web extension plugin '%s'.", name)
                    continue
                
                loaded = LoadedPlugin(entry, instance, enabled=False) # Start as disabled internally
                self.plugins[name] = loaded
                
                if enabled:
                    self.enable_plugin(name)
            except Exception as e:
                logger.error("Failed to load plugin '%s': %s", name, e, exc_info=True)
                self._set_desired_enabled(name, False)

    def list_untrusted_local_plugins(self) -> List[str]:
        """List local plugin names without importing their Python modules."""
        registry = self._state_config.get("plugins", {}).get("registry", {})
        return sorted(
            name
            for name, entry in self.discovery.discover_all().items()
            if entry.source == "local" and not registry.get(name, {}).get("enabled", False)
        )

    def trust_local_plugin(self, name: str) -> bool:
        """Persist explicit trust for a local plugin without importing it yet."""
        entry = self.discovery.discover_all().get(name)
        if not entry or entry.source != "local":
            return False
        plugin_state = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
        plugin_state["enabled"] = True
        plugin_state.setdefault("config", {})
        self._save_state_config()
        return True

    def _load_state_config(self) -> None:
        if self.config_path.exists():
            try:
                self._state_config = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
            except Exception as e:
                logger.error("Failed to read plugins.yaml config: %s", e)
                self._state_config = {}
        else:
            self._state_config = {"plugins": {"registry": {}}}

    def _save_state_config(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(yaml.safe_dump(self._state_config, allow_unicode=True), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to write plugins.yaml config: %s", e)

    def _set_desired_enabled(self, name: str, enabled: bool) -> None:
        plugin_state = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
        plugin_state["enabled"] = enabled
        self._save_state_config()

    def _deactivate_loaded_plugin(self, name: str, loaded: LoadedPlugin) -> bool:
        if not loaded.enabled:
            return True
        try:
            if isinstance(loaded.instance, EventListenerPlugin):
                for event_name in loaded.instance.get_subscriptions():
                    self.event_bus.unsubscribe(event_name, loaded.instance.on_event)
            if isinstance(loaded.instance, LLMProviderPlugin):
                from novel_agent.agents.base import unregister_llm_provider
                unregister_llm_provider(loaded.instance.get_provider_name())
            loaded.instance.on_deactivate()
            loaded.enabled = False
            ptype = loaded.meta.plugin_type
            if loaded.instance in self._active_by_type[ptype]:
                self._active_by_type[ptype].remove(loaded.instance)
            return True
        except Exception as e:
            logger.error("Error deactivating plugin '%s': %s", name, e, exc_info=True)
            return False

    def shutdown(self) -> None:
        """Deactivate runtime instances without changing desired persisted state."""
        for name, loaded in reversed(list(self.plugins.items())):
            self._deactivate_loaded_plugin(name, loaded)

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin by name. Immediately activates it."""
        loaded = self.plugins.get(name)
        if not loaded:
            logger.warning("Plugin '%s' not found.", name)
            return False

        if loaded.enabled:
            return True

        # Check dependencies
        for req in loaded.meta.requires:
            req_loaded = self.plugins.get(req)
            if not req_loaded or not req_loaded.enabled:
                logger.error("Cannot enable plugin '%s': missing dependency '%s'", name, req)
                return False

        try:
            # Build context
            plugin_state = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
            plugin_state["enabled"] = True
            plugin_state.setdefault("config", {})
            self._save_state_config()

            plugin_home = None
            if loaded.entry.path:
                plugin_home = loaded.entry.path if loaded.entry.path.is_dir() else loaded.entry.path.parent
            context = PluginContext(
                root_dir=self.root_dir,
                config=plugin_state["config"],
                event_bus=self.event_bus,
                logger=get_logger(f"plugin.{name}"),
                plugin_home=plugin_home,
            )

            # Activate
            loaded.instance.on_activate(context)
            loaded.enabled = True

            # Register in active caches
            ptype = loaded.meta.plugin_type
            if loaded.instance not in self._active_by_type[ptype]:
                self._active_by_type[ptype].append(loaded.instance)

            # If it's an EventListener, auto-subscribe to event bus
            if isinstance(loaded.instance, EventListenerPlugin):
                for event_name in loaded.instance.get_subscriptions():
                    self.event_bus.subscribe(event_name, loaded.instance.on_event)

            # If it's an LLMProvider, register to agents.base
            if isinstance(loaded.instance, LLMProviderPlugin):
                from novel_agent.agents.base import register_llm_provider
                register_llm_provider(loaded.instance.get_provider_name(), loaded.instance)

            logger.info("Plugin '%s' (%s) successfully enabled.", name, loaded.meta.display_name)
            return True
        except Exception as e:
            logger.error("Error activating plugin '%s': %s", name, e, exc_info=True)
            loaded.enabled = False
            self._set_desired_enabled(name, False)
            return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin by name. Immediately deactivates it."""
        loaded = self.plugins.get(name)
        if not loaded:
            logger.warning("Plugin '%s' not found.", name)
            return False

        if not loaded.enabled:
            return True

        # Check if other active plugins depend on this one
        for other_name, other_loaded in self.plugins.items():
            if other_loaded.enabled and name in other_loaded.meta.requires:
                logger.error("Cannot disable plugin '%s': active plugin '%s' depends on it", name, other_name)
                return False

        try:
            if not self._deactivate_loaded_plugin(name, loaded):
                return False
            self._set_desired_enabled(name, False)
            logger.info("Plugin '%s' successfully disabled.", name)
            return True
        except Exception as e:
            logger.error("Error deactivating plugin '%s': %s", name, e, exc_info=True)
            return False

    def get_plugin_config(self, name: str) -> Dict[str, Any]:
        """Get custom configuration for a plugin."""
        return self._state_config.get("plugins", {}).get("registry", {}).get(name, {}).get("config", {})

    def update_plugin_config(self, name: str, new_config: Dict[str, Any]) -> bool:
        """Update the configuration for a plugin. Re-activates it to apply changes."""
        loaded = self.plugins.get(name)
        if not loaded:
            return False

        # Set config in yaml state
        plugin_state = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
        plugin_state["config"] = new_config
        self._save_state_config()

        # If it is currently active, deactivate and reactivate it to reload configuration
        if loaded.enabled:
            # Temporarily turn off internal enabled flag for deactivation/activation cycle
            loaded.enabled = False
            try:
                # If EventListener, unsubscribe
                if isinstance(loaded.instance, EventListenerPlugin):
                    for event_name in loaded.instance.get_subscriptions():
                        self.event_bus.unsubscribe(event_name, loaded.instance.on_event)

                # If LLMProvider, unregister
                if isinstance(loaded.instance, LLMProviderPlugin):
                    from novel_agent.agents.base import unregister_llm_provider
                    unregister_llm_provider(loaded.instance.get_provider_name())
                
                loaded.instance.on_deactivate()
            except Exception as e:
                logger.error("Error deactivating plugin '%s' during config update: %s", name, e)

            # Remove from active caches
            ptype = loaded.meta.plugin_type
            if loaded.instance in self._active_by_type[ptype]:
                self._active_by_type[ptype].remove(loaded.instance)

            # Reactivate
            try:
                context = PluginContext(
                    root_dir=self.root_dir,
                    config=new_config,
                    event_bus=self.event_bus,
                    logger=get_logger(f"plugin.{name}"),
                    plugin_home=self._plugin_home_for_entry(loaded.entry),
                )
                loaded.instance.on_activate(context)
                loaded.enabled = True
                
                if loaded.instance not in self._active_by_type[ptype]:
                    self._active_by_type[ptype].append(loaded.instance)

                if isinstance(loaded.instance, EventListenerPlugin):
                    for event_name in loaded.instance.get_subscriptions():
                        self.event_bus.subscribe(event_name, loaded.instance.on_event)

                if isinstance(loaded.instance, LLMProviderPlugin):
                    from novel_agent.agents.base import register_llm_provider
                    register_llm_provider(loaded.instance.get_provider_name(), loaded.instance)
            except Exception as e:
                logger.error("Failed to re-activate plugin '%s' after config update: %s", name, e)
                # Keep configuration but disable plugin to maintain consistency
                plugin_state = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
                plugin_state["enabled"] = False
                self._save_state_config()
                return False

        return True

    # High-level helper accessors for active plugins by type
    def get_hooks(self) -> List[PipelineHookPlugin]:
        return [p for p in self._active_by_type[PluginType.PIPELINE_HOOK] if isinstance(p, PipelineHookPlugin)]

    def get_quality_guards(self) -> List[QualityGuardPlugin]:
        return [p for p in self._active_by_type[PluginType.QUALITY_GUARD] if isinstance(p, QualityGuardPlugin)]

    def get_exporters(self) -> Dict[str, ExporterPlugin]:
        exporters = {}
        for p in self._active_by_type[PluginType.EXPORTER]:
            if isinstance(p, ExporterPlugin):
                exporters[p.get_format()] = p
        return exporters

    def get_llm_providers(self) -> Dict[str, LLMProviderPlugin]:
        providers = {}
        for p in self._active_by_type[PluginType.LLM_PROVIDER]:
            if isinstance(p, LLMProviderPlugin):
                providers[p.get_provider_name()] = p
        return providers

    def get_agent_overrides(self) -> Dict[str, AgentOverridePlugin]:
        overrides = {}
        # Order by priority
        active_overrides = sorted(
            [p for p in self._active_by_type[PluginType.AGENT_OVERRIDE] if isinstance(p, AgentOverridePlugin)],
            key=lambda x: x.get_priority()
        )
        for p in active_overrides:
            overrides[p.get_target_role()] = p
        return overrides

    def get_pipeline_phases(self) -> List[PipelinePhasePlugin]:
        return [p for p in self._active_by_type[PluginType.PIPELINE_PHASE] if isinstance(p, PipelinePhasePlugin)]

    def get_vector_stores(self) -> Dict[str, VectorStorePlugin]:
        stores = {}
        for p in self._active_by_type[PluginType.VECTOR_STORE]:
            if isinstance(p, VectorStorePlugin):
                stores[p.get_store_name()] = p
        return stores

    def get_embedding_providers(self) -> Dict[str, EmbeddingProviderPlugin]:
        providers = {}
        for p in self._active_by_type[PluginType.EMBEDDING_PROVIDER]:
            if isinstance(p, EmbeddingProviderPlugin):
                providers[p.get_provider_name()] = p
        return providers

    def get_approval_strategies(self) -> Dict[str, ApprovalStrategyPlugin]:
        strategies = {}
        for p in self._active_by_type[PluginType.APPROVAL_STRATEGY]:
            if isinstance(p, ApprovalStrategyPlugin):
                strategies[p.get_strategy_name()] = p
        return strategies

    def get_rules_extensions(self) -> List[RulesExtensionPlugin]:
        return [p for p in self._active_by_type[PluginType.RULES_EXTENSION] if isinstance(p, RulesExtensionPlugin)]

    def get_prompt_enhancers(self) -> List[PromptEnhancerPlugin]:
        return [p for p in self._active_by_type[PluginType.PROMPT_ENHANCER] if isinstance(p, PromptEnhancerPlugin)]

    def get_event_listeners(self) -> List[EventListenerPlugin]:
        return [p for p in self._active_by_type[PluginType.EVENT_LISTENER] if isinstance(p, EventListenerPlugin)]

    def get_web_extensions(self) -> List[WebExtensionPlugin]:
        return [p for p in self._active_by_type[PluginType.WEB_EXTENSION] if isinstance(p, WebExtensionPlugin)]

    def get_sensitive_scanners(self) -> List[SensitiveScannerPlugin]:
        return [p for p in self._active_by_type[PluginType.SENSITIVE_SCANNER] if isinstance(p, SensitiveScannerPlugin)]

    def get_commands(self) -> List[CommandPlugin]:
        return [p for p in self._active_by_type[PluginType.COMMAND] if isinstance(p, CommandPlugin)]

    def _plugin_home_for_entry(self, entry: PluginEntry) -> Optional[Path]:
        if not entry.path:
            return None
        return entry.path if entry.path.is_dir() else entry.path.parent

    def _meta_from_discovery_entry(self, name: str, entry: PluginEntry) -> Dict[str, Any]:
        if entry.path and entry.path.is_dir() and find_manifest_path(entry.path):
            try:
                manifest = load_manifest(entry.path)
                return manifest_to_plugin_meta(manifest)
            except ManifestError:
                pass
        return {
            "name": name,
            "display_name": name,
            "version": "0.1.0",
            "description": "",
            "author": "",
            "icon": "",
            "plugin_type": "",
            "requires": [],
            "min_core_version": "0.1.0",
            "config_schema": {},
            "capabilities": [],
        }

    def list_plugin_catalog(self) -> List[Dict[str, Any]]:
        """All discovered plugins with load/trust state (includes installed-but-not-imported)."""
        self._load_state_config()
        registry = self._state_config.get("plugins", {}).get("registry", {})
        discovered = self.discovery.discover_all()
        names = sorted(set(discovered.keys()) | set(self.plugins.keys()))
        catalog: List[Dict[str, Any]] = []
        for name in names:
            entry = discovered.get(name)
            loaded = self.plugins.get(name)
            reg = registry.get(name, {})
            trusted = bool(reg.get("enabled", False)) or (
                entry and entry.source == "entry_point"
            )
            if loaded:
                meta = loaded.meta
                catalog.append({
                    "name": loaded.entry.name,
                    "display_name": meta.display_name or loaded.entry.name,
                    "version": meta.version,
                    "description": meta.description,
                    "author": meta.author,
                    "icon": meta.icon,
                    "plugin_type": meta.plugin_type.value,
                    "requires": meta.requires,
                    "min_core_version": meta.min_core_version,
                    "config_schema": meta.config_schema,
                    "config": self.get_plugin_config(loaded.entry.name),
                    "source": loaded.entry.source,
                    "enabled": loaded.enabled,
                    "trusted": trusted,
                    "loaded": True,
                    "installed_version": reg.get("installed_version", meta.version),
                    "capabilities": getattr(meta, "capabilities", []) or [],
                })
            elif entry:
                meta = self._meta_from_discovery_entry(name, entry)
                catalog.append({
                    **meta,
                    "plugin_type": meta.get("plugin_type") or "",
                    "config": reg.get("config", {}),
                    "source": entry.source,
                    "enabled": False,
                    "trusted": trusted,
                    "loaded": False,
                    "installed_version": reg.get("installed_version", meta.get("version")),
                    "capabilities": meta.get("capabilities", []),
                })
        return catalog

    def install_from_zip(self, zip_bytes: bytes, *, replace: bool = True) -> Dict[str, Any]:
        result = install_plugin_zip(self.root_dir, zip_bytes, replace=replace)
        pid = result["id"]
        reg = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(pid, {})
        reg["enabled"] = False
        reg.setdefault("config", {})
        reg["installed_version"] = result.get("version", "0.1.0")
        self._save_state_config()
        return result

    def uninstall_plugin_by_id(self, name: str) -> bool:
        if name in self.plugins and self.plugins[name].enabled:
            if not self.disable_plugin(name):
                return False
        if not uninstall_plugin(self.root_dir, name):
            registry = self._state_config.get("plugins", {}).get("registry", {})
            if name not in registry:
                return False
        reg = self._state_config.setdefault("plugins", {}).setdefault("registry", {})
        if name in reg:
            del reg[name]
            self._save_state_config()
        if name in self.plugins:
            del self.plugins[name]
        return True
