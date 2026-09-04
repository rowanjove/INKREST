import json
import re
import time
import uuid
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
from novel_agent.plugins.permissions import (
    PluginCapability,
    capability_details,
    digest_plugin_path,
    effective_capabilities,
    risk_level,
    risk_summary,
)

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

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
        self._view_sessions: Dict[str, Dict[str, Any]] = {}
        
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
        state_changed = False

        for name, entry in discovered_entries.items():
            try:
                plugin_state = self._state_config.get("plugins", {}).get("registry", {}).get(name, {})
                enabled = bool(plugin_state.get("enabled", False))
                descriptor = self._security_descriptor(name, entry)
                if entry.source == "local":
                    if enabled and not plugin_state.get("trust_digest"):
                        self._migrate_legacy_trust(plugin_state, descriptor)
                        state_changed = True
                    if not self._is_security_grant_current(plugin_state, descriptor):
                        if enabled:
                            plugin_state["enabled"] = False
                            state_changed = True
                            logger.warning(
                                "Disabling local plugin '%s' because its code or permission grant changed.",
                                name,
                            )
                        continue
                    if not enabled:
                        continue
                else:
                    if enabled and not plugin_state.get("trust_digest"):
                        self._migrate_legacy_trust(plugin_state, descriptor)
                        state_changed = True
                    if enabled and not self._is_security_grant_current(plugin_state, descriptor):
                        plugin_state["enabled"] = False
                        state_changed = True
                        logger.warning(
                            "Disabling plugin '%s' because its permission grant is missing or stale.",
                            name,
                        )
                        continue
                    if not enabled:
                        continue

                plugin_cls = entry.load_fn()
                instance = plugin_cls()
                declared_type = descriptor.get("plugin_type")
                actual_type = instance.get_meta().plugin_type.value
                if declared_type and declared_type != "legacy" and actual_type != declared_type:
                    raise RuntimeError(
                        f"Plugin type mismatch: manifest={declared_type}, runtime={actual_type}"
                    )
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
        if state_changed:
            self._save_state_config()

    def list_untrusted_local_plugins(self) -> List[str]:
        """List local plugin names without importing their Python modules."""
        return sorted(
            row["name"]
            for row in self.list_plugin_catalog()
            if row.get("source") == "local" and not row.get("trusted")
        )

    def trust_local_plugin(
        self,
        name: str,
        *,
        digest: str,
        capabilities: List[str],
    ) -> bool:
        """Persist an explicit content-bound permission grant without importing code."""
        entry = self.discovery.discover_all().get(name)
        if not entry or entry.source != "local":
            return False
        descriptor = self._security_descriptor(name, entry)
        expected_capabilities = descriptor["effective_capabilities"]
        if digest != descriptor["digest"] or sorted(capabilities) != sorted(expected_capabilities):
            return False
        plugin_state = (
            self._state_config
            .setdefault("plugins", {})
            .setdefault("registry", {})
            .setdefault(name, {})
        )
        plugin_state["enabled"] = False
        plugin_state["trust_digest"] = descriptor["digest"]
        plugin_state["granted_capabilities"] = expected_capabilities
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

        if loaded.entry.source == "local":
            plugin_state = (
                self._state_config.get("plugins", {})
                .get("registry", {})
                .get(name, {})
            )
            descriptor = self._security_descriptor(name, loaded.entry)
            if not self._is_security_grant_current(plugin_state, descriptor):
                logger.error(
                    "Cannot enable local plugin '%s': trust digest or permission grant is stale.",
                    name,
                )
                self._set_desired_enabled(name, False)
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

    def _security_descriptor(self, name: str, entry: PluginEntry) -> Dict[str, Any]:
        """Describe a plugin without importing local Python code."""
        local = entry.source == "local"
        legacy = bool(local and (not entry.path or not entry.path.is_dir() or not find_manifest_path(entry.path)))
        meta = self._meta_from_discovery_entry(name, entry)
        plugin_type = str(meta.get("plugin_type") or ("legacy" if legacy else ""))
        declared = list(meta.get("declared_capabilities") or [])
        capabilities = (
            effective_capabilities(plugin_type, declared, local=local, legacy=legacy)
            if local
            else list(meta.get("capabilities") or [])
        )
        digest = digest_plugin_path(entry.path) if local and entry.path else "entry-point"
        return {
            "digest": digest,
            "plugin_type": plugin_type,
            "declared_capabilities": declared,
            "effective_capabilities": capabilities,
            "capability_details": capability_details(capabilities),
            "capability_mode": "legacy" if legacy else meta.get("capability_mode", "inferred"),
            "legacy": legacy,
            "risk_level": risk_level(capabilities),
            "risk_summary": risk_summary(capabilities, legacy=legacy),
        }

    @staticmethod
    def _is_security_grant_current(
        plugin_state: Dict[str, Any],
        descriptor: Dict[str, Any],
    ) -> bool:
        return (
            plugin_state.get("trust_digest") == descriptor.get("digest")
            and sorted(plugin_state.get("granted_capabilities") or [])
            == sorted(descriptor.get("effective_capabilities") or [])
        )

    @staticmethod
    def _migrate_legacy_trust(
        plugin_state: Dict[str, Any],
        descriptor: Dict[str, Any],
    ) -> None:
        """Bind pre-V2 enabled plugins to their current content on first upgrade."""
        plugin_state["trust_digest"] = descriptor["digest"]
        plugin_state["granted_capabilities"] = descriptor["effective_capabilities"]
        plugin_state["trust_migrated"] = True

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
            "declared_capabilities": [],
            "capability_mode": "legacy",
            "contributes": {"navigation": [], "commands": []},
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
            catalog_entry = entry or (loaded.entry if loaded else None)
            descriptor = (
                self._security_descriptor(name, catalog_entry)
                if catalog_entry
                else {
                    "digest": "",
                    "effective_capabilities": [],
                    "capability_details": [],
                    "capability_mode": "unknown",
                    "risk_level": "high",
                    "risk_summary": "无法确认插件来源与权限。",
                }
            )
            trusted = bool(
                catalog_entry
                and self._is_security_grant_current(reg, descriptor)
            )
            security_fields = {
                "digest": descriptor["digest"],
                "declared_capabilities": descriptor.get("declared_capabilities", []),
                "effective_capabilities": descriptor["effective_capabilities"],
                "capability_details": descriptor["capability_details"],
                "capability_mode": descriptor["capability_mode"],
                "risk_level": descriptor["risk_level"],
                "risk_summary": descriptor["risk_summary"],
                "requires_reauthorization": bool(
                    catalog_entry
                    and catalog_entry.source == "local"
                    and reg.get("trust_digest")
                    and not trusted
                ),
                "trust_migrated": bool(reg.get("trust_migrated", False)),
                "origin": (
                    f"plugins/{catalog_entry.path.name}"
                    if catalog_entry and catalog_entry.source == "local" and catalog_entry.path
                    else "Python entry point"
                ),
            }
            if loaded:
                meta = loaded.meta
                discovery_meta = self._meta_from_discovery_entry(loaded.entry.name, loaded.entry)
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
                    "capabilities": descriptor["effective_capabilities"],
                    "contributes": discovery_meta.get("contributes", {"navigation": [], "commands": []}),
                    **security_fields,
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
                    "capabilities": descriptor["effective_capabilities"],
                    "contributes": meta.get("contributes", {"navigation": [], "commands": []}),
                    **security_fields,
                })
        return catalog

    def install_from_zip(self, zip_bytes: bytes, *, replace: bool = True) -> Dict[str, Any]:
        result = install_plugin_zip(self.root_dir, zip_bytes, replace=replace)
        pid = result["id"]
        reg = self._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(pid, {})
        reg["enabled"] = False
        reg.pop("trust_digest", None)
        reg.pop("granted_capabilities", None)
        reg.pop("trust_migrated", None)
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

    def get_navigation_contributions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return safe, active dual-region navigation contributions partitioned by surface."""
        catalog = self.list_plugin_catalog()
        result: Dict[str, List[Dict[str, Any]]] = {
            "library_sidebar": [],
            "project_sidebar": [],
        }

        for item in catalog:
            if not item.get("enabled"):
                continue
            if item.get("source") == "local" and not item.get("trusted"):
                continue

            plugin_id = item.get("name") or ""
            plugin_display = item.get("display_name") or plugin_id
            granted_caps = set(item.get("capabilities") or [])

            contributes = item.get("contributes") or {}
            nav_items = contributes.get("navigation") or []

            for nav in nav_items:
                surface = nav.get("surface")
                if surface not in result:
                    continue

                requires = nav.get("requires") or []
                if requires and not set(requires).issubset(granted_caps):
                    logger.warning(
                        "Skipping navigation entry '%s' for plugin '%s': missing required capabilities %s",
                        nav.get("id"),
                        plugin_id,
                        set(requires) - granted_caps,
                    )
                    continue

                view_id = nav.get("view")
                path = (
                    f"/extensions/library/{plugin_id}/{view_id}"
                    if surface == "library_sidebar"
                    else f"/extensions/project/{plugin_id}/{view_id}"
                )

                result[surface].append({
                    "id": f"{plugin_id}:{nav['id']}",
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_display,
                    "contribution_id": nav["id"],
                    "title": nav["title"],
                    "surface": surface,
                    "icon": nav.get("icon", "extensions"),
                    "view": view_id,
                    "path": path,
                    "order": nav.get("order", 200),
                    "default_visibility": nav.get("default_visibility", "visible"),
                    "requires": requires,
                })

        for surf in result:
            result[surf].sort(key=lambda x: (x["order"], x["plugin_id"], x["id"]))

        return result

    def _prune_expired_sessions(self, max_age_seconds: float = 86400.0) -> None:
        """Prune view sessions older than max_age_seconds."""
        now = time.time()
        expired = [
            sid for sid, data in self._view_sessions.items()
            if now - data.get("created_at", 0) > max_age_seconds
        ]
        for sid in expired:
            del self._view_sessions[sid]

    def _assert_safe_project_id(self, project_id: str) -> None:
        if (
            not project_id
            or ".." in project_id
            or "/" in project_id
            or "\\" in project_id
            or not _PROJECT_ID_RE.fullmatch(project_id)
        ):
            raise ValueError("Invalid project_id")

    def _resolve_project_dir(self, project_id: Optional[str]) -> Optional[Path]:
        """Resolve a project directory regardless of whether root_dir is repository root or a project."""
        if not project_id:
            return None
        self._assert_safe_project_id(project_id)
        candidates: List[Path] = []
        if self.root_dir.name == project_id and (self.root_dir / "workspace").is_dir():
            candidates.append(self.root_dir)
        candidates.append(self.root_dir / "projects" / project_id)
        if self.root_dir.parent.name == "projects":
            candidates.append(self.root_dir.parent / project_id)
        try:
            from web.context import BASE_DIR
            candidates.append(BASE_DIR / "projects" / project_id)
        except Exception:
            pass
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.is_dir() and resolved.name == project_id:
                return resolved
        return None

    def _resolve_all_project_dirs(self) -> List[Path]:
        """Discover all project directories under any possible projects/ root."""
        candidates: List[Path] = []
        if (self.root_dir / "projects").is_dir():
            candidates.append(self.root_dir / "projects")
        if self.root_dir.parent.name == "projects":
            candidates.append(self.root_dir.parent)
        try:
            from web.context import BASE_DIR
            if (BASE_DIR / "projects").is_dir() and (BASE_DIR / "projects") not in candidates:
                candidates.append(BASE_DIR / "projects")
        except Exception:
            pass

        seen = set()
        pdirs: List[Path] = []
        for pdir in candidates:
            if pdir.is_dir():
                for sub in sorted(pdir.iterdir()):
                    if sub.is_dir() and sub.name not in seen and (sub / "workspace").is_dir():
                        seen.add(sub.name)
                        pdirs.append(sub)
        return pdirs

    def create_view_session(
        self,
        plugin_id: str,
        view_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Allocate an authenticated view session for a plugin view."""
        self._prune_expired_sessions()
        catalog = {p["name"]: p for p in self.list_plugin_catalog()}
        plugin = catalog.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_id}' not found")
        if not plugin.get("enabled"):
            raise ValueError(f"Plugin '{plugin_id}' is not enabled")
        if plugin.get("source") == "local" and not plugin.get("trusted"):
            raise ValueError(f"Plugin '{plugin_id}' is not trusted")

        contributes = plugin.get("contributes") or {}
        nav_items = contributes.get("navigation") or []
        target_nav = next(
            (n for n in nav_items if n.get("id") == view_id or n.get("view") == view_id),
            None,
        )
        if not target_nav:
            raise ValueError(f"View '{view_id}' is not registered for plugin '{plugin_id}'")

        surface = target_nav.get("surface")
        if surface == "project_sidebar" and not project_id:
            raise ValueError("project_id is required for project_sidebar views")
        if surface != "project_sidebar" and project_id:
            raise ValueError("library views cannot bind a project_id")

        granted_caps = set(plugin.get("capabilities") or [])
        if project_id:
            resolved = self._resolve_project_dir(project_id)
            if resolved is None:
                raise ValueError(f"Unknown project '{project_id}'")
            bound_to_project = self.root_dir.parent.name == "projects" and (
                self.root_dir / "workspace"
            ).is_dir()
            if bound_to_project and self.root_dir.name != project_id:
                if (
                    PluginCapability.ALL_PROJECTS_READ.value not in granted_caps
                    and PluginCapability.LEGACY_FULL_ACCESS.value not in granted_caps
                ):
                    raise ValueError("Cross-project access requires all_projects_read")
        requires = target_nav.get("requires") or []
        if requires and not set(requires).issubset(granted_caps):
            raise ValueError(
                f"Plugin is missing required capabilities: {set(requires) - granted_caps}"
            )

        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        session_data = {
            "session_id": session_id,
            "plugin_id": plugin_id,
            "view_id": target_nav["view"],
            "surface": surface,
            "project_id": project_id,
            "granted_capabilities": sorted(granted_caps),
            "created_at": time.time(),
        }
        self._view_sessions[session_id] = session_data
        return session_data

    def load_view_document(
        self, plugin_id: str, view_id: str, session_id: str
    ) -> Dict[str, Any]:
        """Return plugin-authored view HTML for an active session, or an empty document."""
        session = self._view_sessions.get(session_id)
        if (
            not session
            or session.get("plugin_id") != plugin_id
            or session.get("view_id") != view_id
        ):
            raise ValueError("Invalid view session")
        catalog = {item["name"]: item for item in self.list_plugin_catalog()}
        plugin = catalog.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_id}' not found")
        nav_items = (plugin.get("contributes") or {}).get("navigation") or []
        target_nav = next(
            (
                item
                for item in nav_items
                if item.get("id") == view_id or item.get("view") == view_id
            ),
            None,
        )
        if not target_nav:
            raise ValueError(f"View '{view_id}' is not registered for plugin '{plugin_id}'")
        title = str(target_nav.get("title") or view_id)
        html_rel = str(target_nav.get("html") or "").strip()
        if not html_rel:
            return {"title": title, "html": "", "has_document": False}
        entry = self.discovery.discover_all().get(plugin_id)
        if not entry or not entry.path:
            raise ValueError("Plugin path is unavailable")
        plugin_root = entry.path if entry.path.is_dir() else entry.path.parent
        from novel_agent.plugins.manifest import _validate_view_html

        safe_rel = _validate_view_html(plugin_root, html_rel)
        html_path = (plugin_root / safe_rel).resolve()
        text = html_path.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > 256_000:
            raise ValueError("View HTML exceeds 256KB")
        return {"title": title, "html": text, "has_document": True}

    def close_view_session(self, session_id: str) -> bool:
        """Terminate an active view session."""
        if session_id in self._view_sessions:
            del self._view_sessions[session_id]
            return True
        return False

    def execute_view_rpc(
        self,
        plugin_id: str,
        view_id: str,
        session_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        context_revision: int = 1,
    ) -> Dict[str, Any]:
        """Execute a controlled RPC request from an active plugin view sandbox."""
        self._prune_expired_sessions()
        params = params or {}
        session = self._view_sessions.get(session_id)
        if not session:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32001, "message": "Session not found or expired"},
            }
        if session["plugin_id"] != plugin_id or session["view_id"] != view_id:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32002, "message": "Session plugin or view mismatch"},
            }

        granted = set(session.get("granted_capabilities") or [])
        project_id = session.get("project_id")

        METHOD_CAPABILITIES = {
            "host.ping": None,
            "catalog.listProjects": "project_catalog_read",
            "project.getInfo": "project_read",
            "project.getChapters": "project_read",
            "project.getCharacters": "project_read",
            "project.getOutline": "project_read",
        }

        if method not in METHOD_CAPABILITIES:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found or unauthorized"},
            }

        required_cap = METHOD_CAPABILITIES[method]
        if required_cap and required_cap not in granted:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32003,
                    "message": f"Permission denied: method requires '{required_cap}' capability",
                },
            }

        try:
            if method == "host.ping":
                return {"jsonrpc": "2.0", "result": {"pong": True, "time": time.time()}}

            elif method == "catalog.listProjects":
                results = []
                for pdir in self._resolve_all_project_dirs():
                    meta_file = pdir / "config" / "project_meta.json"
                    name = pdir.name
                    if meta_file.is_file():
                        try:
                            m = json.loads(meta_file.read_text(encoding="utf-8"))
                            name = m.get("name") or name
                        except Exception:
                            pass
                    results.append({
                        "id": pdir.name,
                        "name": name,
                        "updated_at": pdir.stat().st_mtime,
                    })
                return {"jsonrpc": "2.0", "result": {"projects": results}}

            elif method == "project.getInfo":
                if not project_id:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32004, "message": "No active project in session"},
                    }
                pdir = self._resolve_project_dir(project_id)
                if not pdir:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32005, "message": f"Project '{project_id}' not found"},
                    }
                name = project_id
                meta_file = pdir / "config" / "project_meta.json"
                if meta_file.is_file():
                    try:
                        m = json.loads(meta_file.read_text(encoding="utf-8"))
                        name = m.get("name") or name
                    except Exception:
                        pass
                return {"jsonrpc": "2.0", "result": {"id": project_id, "name": name}}

            elif method == "project.getChapters":
                if not project_id:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32004, "message": "No active project in session"},
                    }
                pdir = self._resolve_project_dir(project_id)
                if not pdir:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32005, "message": f"Project '{project_id}' not found"},
                    }
                chap_dir = pdir / "workspace" / "chapters"
                chapters = []
                if chap_dir.is_dir():
                    for cdir in sorted(chap_dir.iterdir()):
                        if cdir.is_dir():
                            content_file = None
                            for fname in ("chapter_final.txt", "chapter_draft.txt", "content.txt"):
                                cand = cdir / fname
                                if cand.is_file():
                                    content_file = cand
                                    break
                            if content_file:
                                chapters.append({
                                    "chapter_id": cdir.name,
                                    "word_count": len(content_file.read_text(encoding="utf-8", errors="ignore")),
                                })
                return {"jsonrpc": "2.0", "result": {"chapters": chapters}}

            elif method == "project.getCharacters":
                if not project_id:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32004, "message": "No active project in session"},
                    }
                pdir = self._resolve_project_dir(project_id)
                if not pdir:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32005, "message": f"Project '{project_id}' not found"},
                    }
                characters = []
                card_yaml = pdir / "assets" / "character_cards.yaml"
                card_json = pdir / "assets" / "characters.json"
                if card_yaml.is_file():
                    try:
                        import yaml
                        loaded = yaml.safe_load(card_yaml.read_text(encoding="utf-8"))
                        if isinstance(loaded, list):
                            characters = loaded
                        elif isinstance(loaded, dict):
                            characters = [
                                {"name": k, **(v if isinstance(v, dict) else {"description": str(v)})}
                                for k, v in loaded.items()
                            ]
                    except Exception:
                        characters = []
                elif card_json.is_file():
                    try:
                        characters = json.loads(card_json.read_text(encoding="utf-8"))
                    except Exception:
                        characters = []
                return {"jsonrpc": "2.0", "result": {"characters": characters}}

            elif method == "project.getOutline":
                if not project_id:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32004, "message": "No active project in session"},
                    }
                pdir = self._resolve_project_dir(project_id)
                if not pdir:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32005, "message": f"Project '{project_id}' not found"},
                    }
                outline_file = pdir / "workspace" / "outline.json"
                outline = {}
                if outline_file.is_file():
                    try:
                        outline = json.loads(outline_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                return {"jsonrpc": "2.0", "result": {"outline": outline}}

        except Exception as exc:
            logger.error("Error executing RPC method '%s': %s", method, exc, exc_info=True)
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal RPC error"},
            }
