#!/usr/bin/env python3
"""
Novel Agent MCP server — read-only tools for external AI agents.

Run: python -m mcp_server.server
Env:
  NOVEL_AGENT_ROOT — workspace root (projects.json parent)
  NOVEL_AGENT_API_URL — optional live backend (default http://127.0.0.1:8000)
  NOVEL_AGENT_ACCESS_TOKEN — optional X-Novel-Agent-Token
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP

from novel_agent.integrations.agent_bridge import (
    build_agent_snapshot,
    default_base_dir,
    list_projects,
    resolve_project_root,
    set_default_base_dir,
    tail_project_logs,
)
from novel_agent.integrations import http_client

mcp = FastMCP("novel-agent")

_root_env = os.environ.get("NOVEL_AGENT_ROOT", "").strip()
if _root_env:
    set_default_base_dir(Path(_root_env))


def _use_http() -> bool:
    return os.environ.get("NOVEL_AGENT_MCP_MODE", "auto").lower() in (
        "http",
        "api",
        "remote",
    ) or (
        os.environ.get("NOVEL_AGENT_MCP_MODE", "auto").lower() == "auto"
        and _http_reachable()
    )


def _http_reachable() -> bool:
    try:
        http_client.fetch_health()
        return True
    except Exception:
        return False


@mcp.tool()
def novel_agent_health() -> str:
    """Check backend health or offline workspace root."""
    if _use_http():
        try:
            return json.dumps(http_client.fetch_health(), ensure_ascii=False, indent=2)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    return json.dumps(
        {"ok": True, "mode": "offline", "base_dir": str(default_base_dir())},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def novel_agent_list_projects() -> str:
    """List registered novel projects and active_id."""
    return json.dumps(list_projects(), ensure_ascii=False, indent=2)


@mcp.tool()
def novel_agent_snapshot(project_id: str = "") -> str:
    """
    Full status snapshot: batch progress, pending chapters, readiness, outline title.
    project_id empty uses active project (offline) or server active (http).
    """
    if _use_http():
        try:
            path = "/api/agent/snapshot"
            if project_id.strip():
                data = http_client.api_get(path, params={"project_id": project_id.strip()})
            else:
                data = http_client.api_get(path)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    try:
        root = resolve_project_root(project_id=project_id.strip() or None)
        pid = project_id.strip() or list_projects().get("active_id") or ""
        return json.dumps(
            build_agent_snapshot(root, project_id=pid),
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def novel_agent_runtime_logs(since_id: int = 0, limit: int = 80) -> str:
    """
    Tail in-memory runtime logs from a running backend (pipeline / LLM calls).
    Requires server at NOVEL_AGENT_API_URL.
    """
    try:
        data = http_client.fetch_runtime_logs(since_id=since_id, limit=limit)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc), "hint": "Start web server or use novel_agent_file_logs"}, ensure_ascii=False)


@mcp.tool()
def novel_agent_file_logs(project_id: str = "", lines: int = 80) -> str:
    """Tail novel_agent.log on disk for a project (works offline)."""
    try:
        root = resolve_project_root(project_id=project_id.strip() or None)
        return json.dumps(
            tail_project_logs(root, max_lines=min(max(lines, 1), 500)),
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def novel_agent_pipeline_alerts() -> str:
    """Pipeline alerts (stale outline, batch retry, external review) via HTTP."""
    try:
        return json.dumps(
            http_client.api_get("/api/pipeline-alerts"),
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def novel_agent_tasks() -> str:
    """List chapter generation tasks from running backend."""
    try:
        return json.dumps(http_client.fetch_tasks(), ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()