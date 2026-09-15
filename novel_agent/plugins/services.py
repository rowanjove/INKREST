"""Service Tokens and Dependency Injection for INKREST Plugin Platform 2.0.

Provides standard service tokens and a registry for core and plugin-contributed
services. Plugins request services via tokens rather than directly importing internal
modules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set


# Core service tokens
SERVICE_PROJECT_READER = "inkrest.project.reader"
SERVICE_PROJECT_WRITER = "inkrest.project.writer"
SERVICE_LLM = "inkrest.llm"
SERVICE_EMBEDDING = "inkrest.embedding"
SERVICE_VECTOR_STORE = "inkrest.vector_store"
SERVICE_STORAGE = "inkrest.storage"
SERVICE_SECRETS = "inkrest.secrets"
SERVICE_EVENT_BUS = "inkrest.event_bus"
SERVICE_COMMANDS = "inkrest.command_registry"
SERVICE_LOGGER = "inkrest.logger"


class ServiceNotFoundError(KeyError):
    pass


class ServiceRegistry:
    """Registry managing injected services and tokens."""

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._owners: Dict[str, str] = {}  # token -> owner (core or plugin_id)

    def register(self, token: str, instance: Any, owner: str = "core") -> None:
        """Register a service under a token."""
        self._services[token] = instance
        self._owners[token] = owner

    def get(self, token: str, default: Optional[Any] = None) -> Any:
        """Retrieve a service by token. Raises ServiceNotFoundError if not found and no default."""
        if token in self._services:
            return self._services[token]
        if default is not None:
            return default
        raise ServiceNotFoundError(f"Service token not found: '{token}'")

    def has(self, token: str) -> bool:
        """Check if a service token is registered."""
        return token in self._services

    def unregister(self, token: str) -> bool:
        """Unregister a service by token."""
        if token in self._services:
            del self._services[token]
            self._owners.pop(token, None)
            return True
        return False

    def unregister_by_owner(self, owner: str) -> None:
        """Unregister all services provided by a specific plugin or component."""
        tokens_to_remove = [tok for tok, o in self._owners.items() if o == owner]
        for tok in tokens_to_remove:
            self.unregister(tok)

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all available service tokens with owner metadata."""
        return {
            token: {
                "owner": self._owners.get(token, "unknown"),
                "type": type(self._services[token]).__name__,
            }
            for token in self._services
        }
