"""System health and startup readiness."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends

import web.context as ctx
import web.helpers as ws_helpers
from web.context import get_root_dir
from web.deps import ProjectSession, get_project_session

router = APIRouter(tags=["system"])


@router.get("/api/system/readiness")
def system_readiness(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    """Aggregate checks for settings UI and agent health probes."""
    root = session.root_dir if session.has_project else None
    checks: Dict[str, Any] = {
        "api": {"ok": True, "label": "API 服务"},
        "single_process": {
            "ok": True,
            "label": "单进程模式",
            "hint": "请勿使用 uvicorn --workers；任务状态保存在进程内存中。",
        },
    }

    token = os.environ.get("NOVEL_AGENT_ACCESS_TOKEN", "").strip()
    checks["remote_token"] = {
        "ok": True,
        "label": "远程访问令牌",
        "configured": bool(token),
    }

    if root and root.is_dir():
        from novel_agent.pipeline import llm_config_error
        from novel_agent.services.novel_run_guard import build_readiness_report

        llm_err = llm_config_error(root)
        checks["llm"] = {
            "ok": llm_err is None,
            "label": "日常模型",
            "hint": llm_err or "已配置可用模型",
        }
        report = build_readiness_report(root)
        checks["book"] = {
            "ok": report.get("ok", False),
            "label": "开书清单",
            "pending": report.get("pending") or [],
        }
        try:
            from web.context import _get_task_manager

            tm = _get_task_manager()
            checks["tasks"] = {
                "ok": True,
                "label": "后台任务",
                "active": tm.has_active_tasks(),
            }
        except Exception as exc:
            checks["tasks"] = {"ok": False, "label": "后台任务", "error": str(exc)}
    else:
        checks["book"] = {
            "ok": False,
            "label": "开书清单",
            "hint": "请先在书库打开一本书。",
        }

    try:
        from web.context import get_plugin_manager

        pm = get_plugin_manager()
        catalog = pm.list_plugin_catalog()
        enabled = sum(1 for p in catalog if p.get("enabled"))
        untrusted_enabled = [
            p["name"]
            for p in catalog
            if p.get("enabled") and p.get("source") == "local" and not p.get("trusted")
        ]
        checks["plugins"] = {
            "ok": len(untrusted_enabled) == 0,
            "label": "插件",
            "enabled_count": enabled,
            "untrusted_enabled": untrusted_enabled,
            "hint": "本地插件需先信任再启用，等同于运行第三方代码。",
        }
    except Exception:
        checks["plugins"] = {"ok": True, "label": "插件", "skipped": True}

    all_ok = all(c.get("ok", True) for c in checks.values() if isinstance(c, dict))
    return {"ok": all_ok, "checks": checks, "active_project_id": session.project_id}


@router.get("/api/system/onboarding")
def onboarding_status() -> Dict[str, Any]:
    """Lightweight status for first-run onboarding wizard."""
    registry = ctx.project_manager._read_registry()
    projects = registry.get("projects") or {}
    project_count = len(projects)
    demo_available = (ws_helpers._demo_projects_dir() / "demo-factory-novel").is_dir()

    llm_ready = False
    if project_count > 0 or ctx._active_project_id:
        try:
            root = get_root_dir()
            from novel_agent.pipeline import llm_config_error

            llm_ready = llm_config_error(root) is None
        except Exception:
            llm_ready = False
    else:
        config_dir = ctx.BASE_DIR / "config"
        if (config_dir / "pipeline.yaml").is_file() or (config_dir / "models.json").is_file():
            try:
                from novel_agent.pipeline import llm_config_error

                llm_ready = llm_config_error(ctx.BASE_DIR) is None
            except Exception:
                llm_ready = False

    return {
        "has_projects": project_count > 0,
        "project_count": project_count,
        "llm_ready": llm_ready,
        "demo_available": demo_available,
        "demo_id": "demo-factory-novel",
        "suggested_next": "import_demo" if not project_count else ("configure_llm" if not llm_ready else "open_factory"),
    }