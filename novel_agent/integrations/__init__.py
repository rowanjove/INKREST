"""External agent integrations (CLI, MCP, HTTP helpers)."""

from novel_agent.integrations.agent_bridge import (
    build_agent_snapshot,
    list_projects,
    resolve_project_root,
    tail_project_logs,
)

__all__ = [
    "build_agent_snapshot",
    "list_projects",
    "resolve_project_root",
    "tail_project_logs",
]