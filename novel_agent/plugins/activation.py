"""Activation Manager for Inkrest Plugin System 2.0.

Provides lazy / on-demand activation support for plugins based on activation events:
- '*' or 'onStartup': Eager activation during host initialization.
- 'onCommand:<command_id>': Activated when a specific contributed command is executed.
- 'onHook:<hook_name>': Activated when a pipeline hook or life-cycle hook is invoked.
- 'onView:<view_id>': Activated when a custom view is opened.
- 'onLanguage:<lang>': Activated on matching language / document context.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from novel_agent.plugins.lifecycle import PluginDiagnostics, PluginState

logger = logging.getLogger(__name__)


class ActivationManager:
    """Manages lazy plugin activation lifecycle."""

    def __init__(
        self,
        activator: Optional[Callable[[str], Any]] = None,
        diagnostics_provider: Optional[Callable[[str], Optional[PluginDiagnostics]]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._activator = activator
        self._diagnostics_provider = diagnostics_provider
        self._events_by_plugin: Dict[str, Set[str]] = {}
        self._plugins_by_event: Dict[str, Set[str]] = {}
        self._activated_plugins: Set[str] = set()
        self._activating_plugins: Set[str] = set()
        self._activation_times: Dict[str, float] = {}

    def set_activator(self, activator: Callable[[str], Any]) -> None:
        """Set the callable used to activate a plugin by id."""
        self._activator = activator

    def set_diagnostics_provider(
        self, provider: Callable[[str], Optional[PluginDiagnostics]]
    ) -> None:
        self._diagnostics_provider = provider

    def register_plugin(
        self,
        plugin_id: str,
        events: Optional[List[str]] = None,
    ) -> bool:
        """Register activation events for a plugin.
        
        Returns True if the plugin is eager (requires immediate activation).
        """
        raw_events = set(events or [])
        if not raw_events or "*" in raw_events or "onStartup" in raw_events:
            # Eager plugin
            raw_events.add("*")
            self._events_by_plugin[plugin_id] = raw_events
            self._plugins_by_event.setdefault("*", set()).add(plugin_id)
            return True

        self._events_by_plugin[plugin_id] = raw_events
        for ev in raw_events:
            self._plugins_by_event.setdefault(ev, set()).add(plugin_id)
        return False

    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove a plugin from the activation registry."""
        events = self._events_by_plugin.pop(plugin_id, set())
        for ev in events:
            if ev in self._plugins_by_event:
                self._plugins_by_event[ev].discard(plugin_id)
                if not self._plugins_by_event[ev]:
                    del self._plugins_by_event[ev]
        self._activated_plugins.discard(plugin_id)
        self._activating_plugins.discard(plugin_id)
        self._activation_times.pop(plugin_id, None)

    def is_activated(self, plugin_id: str) -> bool:
        return plugin_id in self._activated_plugins

    def get_activation_events(self, plugin_id: str) -> List[str]:
        return sorted(list(self._events_by_plugin.get(plugin_id, set())))

    def get_activation_time(self, plugin_id: str) -> Optional[float]:
        return self._activation_times.get(plugin_id)

    def activate_plugin(self, plugin_id: str) -> bool:
        """Synchronously activate a specific plugin if not already activated."""
        with self._lock:
            if plugin_id in self._activated_plugins:
                return True
            if plugin_id in self._activating_plugins:
                logger.warning("Circular activation detected for plugin '%s'", plugin_id)
                return False

            self._activating_plugins.add(plugin_id)
        diag = self._diagnostics_provider(plugin_id) if self._diagnostics_provider else None
        if diag:
            diag.transition(PluginState.ACTIVATING, reason="Activation triggered")

        start_time = time.time()
        success = True
        try:
            if self._activator:
                res = self._activator(plugin_id)
                if res is False:
                    success = False
        except Exception as exc:
            logger.error("Activation failed for plugin '%s': %s", plugin_id, exc)
            if diag:
                diag.transition(
                    PluginState.FAILED,
                    reason=f"Activation error: {exc}",
                    error=str(exc),
                )
            success = False
            raise
        finally:
            with self._lock:
                self._activating_plugins.discard(plugin_id)

        if success:
            duration = time.time() - start_time
            with self._lock:
                self._activated_plugins.add(plugin_id)
                self._activation_times[plugin_id] = duration
            if diag:
                diag.active_since = time.time()
                diag.transition(PluginState.ACTIVE, reason=f"Activated in {duration*1000:.1f}ms")
            logger.info("Plugin '%s' activated successfully in %.2fms", plugin_id, duration * 1000)
            return True

        return False

    def trigger_event(self, event_name: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Trigger an activation event, activating all plugins bound to it.
        
        Returns the list of plugin_ids that were newly activated.
        """
        candidates = self._plugins_by_event.get(event_name, set())
        activated: List[str] = []
        for plugin_id in list(candidates):
            if plugin_id not in self._activated_plugins:
                try:
                    if self.activate_plugin(plugin_id):
                        activated.append(plugin_id)
                except Exception as exc:
                    logger.warning("Failed to trigger activation for '%s' on '%s': %s", plugin_id, event_name, exc)
        return activated

    def trigger_command(self, command_id: str) -> List[str]:
        """Convenience helper to trigger onCommand:<command_id>."""
        return self.trigger_event(f"onCommand:{command_id}")

    def trigger_hook(self, hook_name: str) -> List[str]:
        """Convenience helper to trigger onHook:<hook_name>."""
        return self.trigger_event(f"onHook:{hook_name}")

    def trigger_view(self, view_id: str) -> List[str]:
        """Convenience helper to trigger onView:<view_id>."""
        return self.trigger_event(f"onView:{view_id}")

    def activate_eager_plugins(self) -> List[str]:
        """Activate all plugins registered with eager '*' event."""
        return self.trigger_event("*")

    def reset(self) -> None:
        """Clear all runtime activation state."""
        self._events_by_plugin.clear()
        self._plugins_by_event.clear()
        self._activated_plugins.clear()
        self._activating_plugins.clear()
        self._activation_times.clear()
