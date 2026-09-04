"""Lightweight assistant context endpoints for the desktop pet."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import web.context as ws_server
from web.deps import (
    ProjectSession,
    RequireProjectDep,
    coerce_project_session,
    current_project_info,
    get_project_session,
    task_manager_for,
)

router = APIRouter()


# ---- Request & Response Models ----

class FixRequest(BaseModel):
    fix_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---- Helper Functions ----

def _summarize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    progress = task.get("progress") if isinstance(task.get("progress"), dict) else {}
    return {
        "id": task.get("task_id", ""),
        "status": task.get("status", ""),
        "chapter_id": task.get("chapter_id"),
        "goal": task.get("goal", ""),
        "error": task.get("error"),
        "step": progress.get("step"),
        "progress": progress,
    }


def _active_project_summary() -> Optional[Dict[str, str]]:
    try:
        manager = ws_server.project_manager
        active_id = manager.get_active_id() or ws_server._active_project_id
        if not active_id:
            return None
        for project in manager.list_projects():
            if project.get("id") == active_id:
                return {"id": active_id, "name": project.get("name", active_id)}
        return {"id": active_id, "name": active_id}
    except Exception:
        if ws_server._active_project_id:
            return {"id": ws_server._active_project_id, "name": ws_server._active_project_id}
        return None


def _get_chapter_goal_fallback(
    chapter_id: str,
    root_dir: Optional[Path] = None,
) -> Optional[str]:
    """Retrieve the chapter goal using multiple fallback sources to avoid missing data."""
    if not chapter_id:
        return None
    # Fallback 1: SQLite state store
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore
        root = Path(root_dir or ws_server.get_root_dir())
        store = SQLiteStateStore(root)
        for ch in store.get_chapters():
            if str(ch.get("chapter_id")) == str(chapter_id):
                goal = ch.get("goal") or ch.get("chapter_goal")
                if goal:
                    return goal
    except Exception:
        pass

    # Fallback 2: outline.json
    try:
        outline = ws_server.get_outline(root_dir)
        if outline:
            chapters = outline.get("chapters") or []
            for ch in chapters:
                if str(ch.get("chapter_id")) == str(chapter_id):
                    goal = ch.get("goal") or ch.get("chapter_goal")
                    if goal:
                        return goal
    except Exception:
        pass

    # Fallback 3: plan.json
    try:
        safe_id = ws_server._validate_id(chapter_id, "chapter_id")
        root = Path(root_dir or ws_server.get_root_dir())
        chapter_dir = root / "workspace" / "chapters" / f"chapter_{safe_id}"
        if chapter_dir.exists():
            plan = ws_server._read_json(chapter_dir / "plan.json")
            goal = (
                plan.get("chapter_goal")
                or plan.get("detailed_synopsis")
                or plan.get("chapter_title")
            )
            if goal:
                return goal
    except Exception:
        pass

    # Fallback 4: Default generic goal
    return f"重新生成第 {chapter_id} 章内容"


def _get_assistant_llm(root_dir: Optional[Path] = None) -> Any:
    """Resolve and create LLM client for assistant."""
    try:
        from novel_agent.pipeline import load_pipeline_settings
        root = Path(root_dir or ws_server.get_root_dir())
        current = load_pipeline_settings(root)
        
        llm_config = current.get("llm", {}).get("assistant")
        
        if not llm_config:
            llm_settings = current.get("llm", {})
            daily_model_id = llm_settings.get("daily_model_id") or llm_settings.get("default_model_id")
            if daily_model_id:
                llm_config = {"model_ref": daily_model_id}

        if not llm_config:
            llm_config = current.get("llm", {}).get("default")
            
        if not llm_config:
            llm_config = current.get("llm", {})
            
        if not llm_config:
            return None
            
        if "model_ref" in llm_config:
            from web.model_library import ModelLibrary
            try:
                stored = ModelLibrary(root).get_model(llm_config["model_ref"])
                stored_cfg = {k: v for k, v in stored.items() if k != "id"}
                llm_config = {**stored_cfg, **llm_config}
            except Exception:
                pass
            
        provider = llm_config.get("provider", "static")
        if provider == "static":
            from web.model_library import ModelLibrary
            lib = ModelLibrary(root)
            raw_models = lib._load().get("models", {})
            text_models = [{"id": mid, **m} for mid, m in raw_models.items() if m.get("type", "text") == "text"]
            if text_models:
                llm_config = text_models[0]
            else:
                return None
            
        from novel_agent.agents.base import create_llm
        return create_llm(llm_config)
    except Exception as e:
        ws_server.logger.warning("Failed to load assistant LLM client: %s", e)
        return None


def _parse_chat_response(text: str) -> Dict[str, Any]:
    """Parse output text of the assistant LLM to extract actions and suggestions."""
    import re
    text = text.strip()
    actions: List[Dict[str, Any]] = []
    suggestions: List[str] = []

    sug_marker = "===SUGGESTIONS==="
    if sug_marker in text:
        parts = text.split(sug_marker, 1)
        text = parts[0].strip()
        sug_str = parts[1].strip()
        try:
            sug_match = re.search(r'\[.*?\]', sug_str, re.DOTALL)
            if sug_match:
                parsed_sugs = json.loads(sug_match.group(0))
                if isinstance(parsed_sugs, list):
                    suggestions = [str(s) for s in parsed_sugs if isinstance(s, (str, int))]
        except Exception as e:
            ws_server.logger.warning("Failed to parse assistant suggestions: %s", e)

    marker = "===ACTIONS==="
    if marker in text:
        parts = text.split(marker, 1)
        reply = parts[0].strip()
        actions_str = parts[1].strip()

        try:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', actions_str, re.DOTALL)
            if json_match:
                actions = json.loads(json_match.group(0))
            else:
                actions = json.loads(actions_str)
        except Exception as e:
            ws_server.logger.warning("Failed to parse assistant chat actions: %s", e)
    else:
        reply = text

    from web.assistant_actions import sanitize_assistant_actions

    return {
        "reply": reply,
        "actions": sanitize_assistant_actions(actions),
        "suggestions": suggestions,
    }


# ---- API Endpoints ----

async def build_assistant_context(session: ProjectSession) -> Dict[str, Any]:
    """Build compact software-state summary for the pet bubble (HTTP or internal callers)."""
    session = coerce_project_session(session)
    tasks: List[Dict[str, Any]] = []
    try:
        tasks = await task_manager_for(session).list_tasks_async()
    except Exception:
        tasks = []

    running = [
        _summarize_task(task)
        for task in tasks
        if task.get("status") in ("pending", "running")
    ]
    pipeline_active = False
    import time as _time

    for task in tasks:
        if task.get("status") not in ("pending", "running"):
            continue
        goal = str(task.get("goal") or "")
        tid = str(task.get("task_id") or task.get("id") or "")
        if tid.startswith("novel-auto") or tid.startswith("novel-cont") or goal.startswith("Novel"):
            pipeline_active = True
            break
        prog = task.get("progress") if isinstance(task.get("progress"), dict) else {}
        if prog.get("status") == "running" or prog.get("step"):
            pipeline_active = True
            break
    if not pipeline_active:
        try:
            from web.runtime_log_buffer import tail_runtime_logs

            now = _time.time()
            for row in tail_runtime_logs(40):
                if row.get("type") != "progress" or row.get("status") != "running":
                    continue
                ts = float(row.get("timestamp") or 0)
                if ts and now - ts <= 180:
                    pipeline_active = True
                    break
        except Exception:
            pass
    seen_chapters = set()
    failed_tasks = []
    for task in tasks:
        ch_id = task.get("chapter_id")
        if ch_id:
            if ch_id not in seen_chapters:
                seen_chapters.add(ch_id)
                if task.get("status") == "failed":
                    failed_tasks.append(task)
        else:
            if task.get("status") == "failed":
                failed_tasks.append(task)
    failed = [
        _summarize_task(task)
        for task in reversed(failed_tasks[:5])
    ]

    recent_logs = []
    for task in tasks[-5:]:
        if task.get("error"):
            recent_logs.append({
                "level": "error",
                "message": task.get("error"),
                "chapter_id": task.get("chapter_id"),
                "task_id": task.get("task_id"),
                "source": "task",
            })

    root: Optional[Any] = session.root_dir if session.has_project else None

    agent_runtime_logs: List[Dict[str, Any]] = []
    system_log_tail: List[str] = []
    system_log_paths: Dict[str, str] = {}
    try:
        from web.runtime_log_buffer import read_system_log_tail, tail_runtime_logs

        proj_id = session.project_id if session.has_project else ""
        agent_runtime_logs = tail_runtime_logs(60, project_id=proj_id)
        base_logs = ws_server.BASE_DIR / "logs" / "novel_agent.log"
        system_log_paths = {
            "workspace": str(base_logs),
            "hint": "接口调用明细见日志中心；任务错误见 recent_logs / agent_runtime_logs",
        }
        if root:
            proj_log = root / "logs" / "novel_agent.log"
            if proj_log.is_file():
                system_log_paths["project"] = str(proj_log)
                system_log_tail = read_system_log_tail(proj_log, 40)
        if not system_log_tail:
            system_log_tail = read_system_log_tail(base_logs, 40)
    except Exception:
        pass

    merged_recent = list(recent_logs)
    for row in agent_runtime_logs[-25:]:
        if row.get("level") in ("error", "warn", "warning"):
            merged_recent.append(
                {
                    "level": row.get("level") if row.get("level") != "warning" else "warn",
                    "message": row.get("message"),
                    "chapter_id": row.get("chapter_id"),
                    "source": row.get("source") or "agent",
                    "step": row.get("step"),
                }
            )
    merged_recent = merged_recent[-30:]

    novel_batch: Dict[str, Any] = {
        "paused": False,
        "pause_reason": "",
        "last_arc_id": "",
        "last_chapter_id": "",
        "fail_streak": 0,
    }
    if session.has_project and root:
        try:
            from novel_agent.services.arc_queue import load_arc_progress

            progress = load_arc_progress(root)
            novel_batch = {
                "paused": progress.get("status") == "paused",
                "pause_reason": str(progress.get("pause_reason") or ""),
                "last_arc_id": str(progress.get("last_arc_id") or ""),
                "last_chapter_id": str(progress.get("last_chapter_id") or ""),
                "fail_streak": int(progress.get("fail_streak") or 0),
            }
        except Exception:
            pass

    pipeline_pending: Dict[str, Any] = {
        "pending_total": 0,
        "pending_retry_count": 0,
        "pending_gate_count": 0,
        "retries": [],
        "gate_blocked": [],
    }
    try:
        if root:
            from novel_agent.services.pipeline_pending import summarize_pipeline_pending

            pipeline_pending = summarize_pipeline_pending(root)
    except Exception:
        pass

    work: Dict[str, Any] = {
        "scale": "",
        "scale_label": "",
        "target_chapters": 0,
        "chapters_written": 0,
        "has_macro_outline": False,
    }
    try:
        if root:
            from novel_agent.services.assistant_snapshot import (
                enrich_task_summaries,
                load_work_snapshot,
            )

            work = load_work_snapshot(root)
            running = enrich_task_summaries(root, running)
            failed = enrich_task_summaries(root, failed)
    except Exception:
        pass

    factory: Dict[str, Any] = {}
    if root:
        try:
            from web.factory_summaries import build_factory_dashboard
            from web.routes.factory import _running_task_count

            factory = build_factory_dashboard(
                root,
                session.project_id,
                _running_task_count(session),
            )
        except Exception:
            factory = {}

    return {
        "backend_health": "ok",
        "active_project": current_project_info(session) if session.has_project else None,
        "pipeline_active": pipeline_active,
        "work": work,
        "factory": factory,
        "running_tasks": running,
        "failed_tasks": failed,
        "recent_logs": merged_recent,
        "agent_runtime_logs": agent_runtime_logs,
        "system_log_tail": system_log_tail,
        "system_log_paths": system_log_paths,
        "novel_batch": novel_batch,
        "pipeline_pending": pipeline_pending,
    }


@router.get("/api/assistant/context")
async def get_assistant_context(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    """Return a compact software-state summary for the pet bubble."""
    return await build_assistant_context(session)


@router.get("/api/assistant/diagnose")
async def get_assistant_diagnose(
    ignored_task_ids: Optional[str] = None,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Perform quick diagnostic check of the system state."""
    session = coerce_project_session(session)
    active_project = current_project_info(session)
    if active_project.get("id") is None:
        active_project = None

    ignored_ids = ignored_task_ids.split(",") if ignored_task_ids else []
    tasks = []
    if session.has_project:
        try:
            tasks = await task_manager_for(session).list_tasks_async()
        except Exception:
            tasks = []

    from novel_agent.services.assistant_diagnostics import run_system_diagnostics
    return run_system_diagnostics(
        session.root_dir if session.has_project else None,
        active_project,
        tasks,
        ignored_ids,
        chapter_goal_resolver=lambda chapter_id: _get_chapter_goal_fallback(
            chapter_id,
            session.root_dir,
        ),
    )



@router.post("/api/assistant/fix")
async def execute_assistant_fix(req: FixRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Execute low-risk automatic fix action."""
    session = coerce_project_session(session)
    fix_type = req.fix_type
    payload = req.payload
    from web.assistant_actions import ALLOWED_FIX_TYPES

    if fix_type not in ALLOWED_FIX_TYPES:
        raise HTTPException(400, f"Unsupported fix type: {fix_type}")

    if fix_type == "test_model":
        try:
            from novel_agent.agents.base import OpenAILLM

            client = _get_assistant_llm(session.root_dir)
            if not client:
                return {
                    "success": False,
                    "error": "当前未配置任何大模型（处于 static 占位状态），无法测试。",
                }
            if isinstance(client, OpenAILLM):
                test_res = client.test()
                return {
                    "success": test_res.get("success", False),
                    "details": test_res,
                }
            return {
                "success": False,
                "error": f"当前模型类型 {type(client).__name__} 不支持标准连通性测试。",
            }
        except Exception as e:
            return {"success": False, "error": f"测试过程中发生异常：{str(e)}"}
            
    elif fix_type == "retry_task":
        chapter_id = payload.get("chapter_id")
        goal = payload.get("goal")
        if not goal and chapter_id:
            goal = _get_chapter_goal_fallback(chapter_id, session.root_dir)
        if not chapter_id or not goal:
            raise HTTPException(400, "Missing chapter_id or goal in payload")
            
        try:
            safe_id = ws_server._validate_id(chapter_id, "chapter_id")
            chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
            
            checkpoint_path = chapter_dir / "checkpoint.json"
            if checkpoint_path.exists():
                try:
                    checkpoint_path.unlink()
                except OSError as e:
                    ws_server.logger.warning("Failed to delete checkpoint file %s: %s", checkpoint_path, e)
                    
            task_id = await task_manager_for(session).submit_chapter(
                chapter_id=safe_id,
                goal=goal,
                dry_run=False,
            )
            return {
                "success": True,
                "task_id": task_id,
                "message": f"第 {safe_id} 章生成任务已重新启动，任务ID: {task_id}"
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif fix_type == "auto_repair_chapter":
        chapter_id = payload.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "Missing chapter_id in payload")
        try:
            from web.routes.chapters.tasks import rewrite_chapter

            task = await rewrite_chapter(str(chapter_id), session)
            return {
                "success": True,
                "task_id": task.task_id,
                "message": f"第 {chapter_id} 章已提交自动修复",
            }
        except HTTPException as exc:
            return {"success": False, "error": str(exc.detail)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif fix_type == "rerun_gate":
        chapter_id = payload.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "Missing chapter_id in payload")
        try:
            from web.routes.chapters.tasks import rerun_chapter_gate

            task = await rerun_chapter_gate(str(chapter_id), session)
            return {
                "success": True,
                "task_id": task.task_id,
                "message": f"第 {chapter_id} 章已提交门禁重跑",
            }
        except HTTPException as exc:
            return {"success": False, "error": str(exc.detail)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif fix_type == "inspect_gate_detail":
        chapter_id = payload.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "Missing chapter_id in payload")
        from novel_agent.services.assistant_knowledge import get_gate_diagnostic_detail
        details = get_gate_diagnostic_detail(session.root_dir, str(chapter_id))
        if not details:
            return {"success": False, "error": f"未找到第 {chapter_id} 章的门禁报告。"}
        return {
            "success": True,
            "details": details,
            "message": f"第 {chapter_id} 章门禁评分 {details.get('score', '—')}，{'已通过' if details.get('overall_pass') else '未通过（拦截项: ' + ', '.join(details.get('blocked_by', [])) + '）'}",
        }

    else:
        raise HTTPException(400, f"Unsupported fix type: {fix_type}")


# Include sub-routers for chat and editor
from web.routes.assistant_chat import router as chat_router
from web.routes.assistant_editor import router as editor_router

router.include_router(chat_router)
router.include_router(editor_router)
