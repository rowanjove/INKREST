"""Dependency graph and topological sorting for INKREST Plugin Platform 2.0.

Validates plugin and service dependencies, detects cycles, and generates
proper initialization and activation ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


class ResolverError(ValueError):
    """Base error for dependency resolution failures."""
    pass


class CircularDependencyError(ResolverError):
    pass


class MissingDependencyError(ResolverError):
    pass


@dataclass
class PluginNode:
    plugin_id: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)  # plugin IDs required
    required_services: List[str] = field(default_factory=list)
    optional_services: List[str] = field(default_factory=list)
    provided_services: List[str] = field(default_factory=list)


class DependencyResolver:
    """Resolves dependencies and computes activation DAG."""

    def __init__(self) -> None:
        self._nodes: Dict[str, PluginNode] = {}

    def add_plugin(
        self,
        plugin_id: str,
        version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
        required_services: Optional[List[str]] = None,
        optional_services: Optional[List[str]] = None,
        provided_services: Optional[List[str]] = None,
    ) -> None:
        self._nodes[plugin_id] = PluginNode(
            plugin_id=plugin_id,
            version=version,
            dependencies=dependencies or [],
            required_services=required_services or [],
            optional_services=optional_services or [],
            provided_services=provided_services or [],
        )

    def resolve_order(self) -> List[str]:
        """Compute topological sort of plugins.
        
        Returns ordered list of plugin IDs from least dependent to most dependent.
        Raises MissingDependencyError if a required dependency is missing.
        Raises CircularDependencyError if a circular dependency cycle is detected.
        """
        # 1. Verify all required plugin dependencies exist
        for pid, node in self._nodes.items():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    raise MissingDependencyError(
                        f"Plugin '{pid}' requires '{dep}', but '{dep}' is not available."
                    )

        # 2. Build graph: dependency -> dependents, and in-degree counts
        in_degree: Dict[str, int] = {pid: 0 for pid in self._nodes}
        graph: Dict[str, List[str]] = {pid: [] for pid in self._nodes}

        for pid, node in self._nodes.items():
            for dep in node.dependencies:
                graph[dep].append(pid)
                in_degree[pid] += 1

        # 3. Kahn's Algorithm
        queue = [pid for pid, deg in in_degree.items() if deg == 0]
        ordered: List[str] = []

        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            curr = queue.pop(0)
            ordered.append(curr)

            for dependent in graph[curr]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(ordered) != len(self._nodes):
            remaining = {pid for pid, deg in in_degree.items() if deg > 0}
            raise CircularDependencyError(
                f"Circular dependency detected involving plugins: {sorted(remaining)}"
            )

        return ordered

    def check_service_dependencies(self, available_services: Set[str]) -> Dict[str, List[str]]:
        """Verify which plugins have all required services satisfied.
        
        Returns dict: {plugin_id: missing_service_tokens}
        """
        missing_by_plugin: Dict[str, List[str]] = {}
        # Also include services provided by nodes in graph
        all_services = set(available_services)
        for node in self._nodes.values():
            all_services.update(node.provided_services)

        for pid, node in self._nodes.items():
            missing = [s for s in node.required_services if s not in all_services]
            if missing:
                missing_by_plugin[pid] = missing
        return missing_by_plugin
