"""Agent-facing HTTP API (snapshots + integration settings for MCP / CLI)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import web.context as ws_server
from web.deps import ProjectSession, get_project_session
from novel_agent.integrations.agent_bridge import (
    build_agent_snapshot,
    list_projects,
    tail_project_logs,
)
from novel_agent.integrations.agent_settings import (
    DEFAULT_AGENT_BRIDGE,
    load_agent_bridge_settings,
    save_agent_bridge_settings,
)
from web.security import ACCESS_TOKEN_ENV

router = APIRouter()


class AgentBridgeSettingsUpdate(BaseModel):
    mcp_mode: Optional[Literal["auto", "offline", "http"]] = None
    api_url_override: Optional[str] = None
    show_integration_hints: Optional[bool] = None


def _mcp_installed() -> bool:
    try:
        import mcp  # noqa: F401

        return True
    except ImportError:
        return False


def _build_mcp_config_snippet(base_dir: str, api_url: str) -> Dict[str, Any]:
    root = base_dir.replace("\\", "\\\\")
    return {
        "mcpServers": {
            "novel-agent": {
                "command": sys.executable,
                "args": ["-m", "mcp_server.server"],
                "cwd": base_dir,
                "env": {
                    "NOVEL_AGENT_ROOT": base_dir,
                    "NOVEL_AGENT_API_URL": api_url,
                },
            }
        }
    }


def _integration_info(api_url: str, session: ProjectSession) -> Dict[str, Any]:
    base = ws_server.BASE_DIR
    active = session.project_id or ""
    root_dir = str(base)
    project_root = str(session.root_dir)
    cli_py = str((base / "cli.py").resolve())
    return {
        "workspace_root": root_dir,
        "active_project_id": active,
        "active_project_root": project_root,
        "python_executable": sys.executable,
        "cli_path": cli_py,
        "mcp_installed": _mcp_installed(),
        "mcp_install_hint": "pip install -r requirements-mcp.txt",
        "access_token_env_set": bool(os.environ.get(ACCESS_TOKEN_ENV, "").strip()),
        "access_token_env_name": ACCESS_TOKEN_ENV,
        "docs_relative": "docs/AGENT-INTEGRATION.md",
        "skill_relative": "skills/novel-agent-bridge/SKILL.md",
        "api_endpoints": [
            "GET /api/agent/snapshot",
            "GET /api/agent/projects",
            "GET /api/agent/logs/tail",
            "GET /api/runtime-logs",
            "GET /api/pipeline-alerts",
        ],
        "cli_examples": [
            f'"{sys.executable}" "{cli_py}" agent projects --novel-root "{root_dir}"',
            f'"{sys.executable}" "{cli_py}" agent snapshot --novel-root "{root_dir}"',
            f'"{sys.executable}" "{cli_py}" agent logs --root-dir "{project_root}" --lines 80',
            f'"{sys.executable}" "{cli_py}" agent snapshot --http',
            f'"{sys.executable}" -m mcp_server.server',
        ],
        "mcp_config_json": _build_mcp_config_snippet(root_dir, api_url),
        "mcp_config_text": json.dumps(
            _build_mcp_config_snippet(root_dir, api_url),
            ensure_ascii=False,
            indent=2,
        ),
        "env_vars": {
            "NOVEL_AGENT_ROOT": root_dir,
            "NOVEL_AGENT_API_URL": api_url,
            "NOVEL_AGENT_ACCESS_TOKEN": "(服务端令牌，勿提交仓库)",
            "NOVEL_AGENT_MCP_MODE": "auto | offline | http",
        },
    }


@router.get("/api/agent/settings")
def get_agent_settings(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    """Workspace agent-bridge settings + copy-paste integration kit."""
    settings = load_agent_bridge_settings(ws_server.BASE_DIR)
    override = (settings.get("api_url_override") or "").strip()
    api_url = override or "http://127.0.0.1:8000"
    return {
        "settings": settings,
        "defaults": DEFAULT_AGENT_BRIDGE,
        "integration": _integration_info(api_url, session),
    }


@router.put("/api/agent/settings")
def put_agent_settings(
    body: AgentBridgeSettingsUpdate,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(400, "No fields to update")
    saved = save_agent_bridge_settings(ws_server.BASE_DIR, patch)
    override = (saved.get("api_url_override") or "").strip()
    api_url = override or "http://127.0.0.1:8000"
    return {
        "status": "updated",
        "settings": saved,
        "integration": _integration_info(api_url, session),
    }


@router.get("/api/agent/projects")
def agent_list_projects() -> Dict[str, Any]:
    return list_projects(ws_server.BASE_DIR)


@router.get("/api/agent/snapshot")
def agent_snapshot(
    project_id: Optional[str] = Query(None),
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Canonical V2 project state plus live integration-only diagnostics."""
    try:
        if project_id:
            ws_server._validate_id(project_id, "project_id")
            root = ws_server.BASE_DIR / "projects" / project_id
            if not root.is_dir():
                raise HTTPException(404, f"Project {project_id} not found")
        else:
            root = session.root_dir
            project_id = session.project_id or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc

    snap = build_agent_snapshot(root, project_id=project_id or "")
    try:
        from web.runtime_log_buffer import tail_runtime_logs

        snap["runtime_logs"] = tail_runtime_logs(40)
    except Exception:
        snap["runtime_logs"] = []
    snap["tasks_hint"] = (
        "active_tasks is canonical; GET /api/chapters/tasks includes retained task logs"
    )
    return snap


@router.get("/api/agent/logs/tail")
def agent_logs_tail(
    lines: int = Query(60, ge=1, le=500),
    project_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    try:
        if project_id:
            ws_server._validate_id(project_id, "project_id")
            root = ws_server.BASE_DIR / "projects" / project_id
        else:
            root = ws_server.get_root_dir()
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    if not root.is_dir():
        raise HTTPException(404, "Project root not found")
    return tail_project_logs(root, max_lines=lines)
