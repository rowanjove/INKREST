"""Lightweight assistant context endpoints for the desktop pet."""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import web.context as ws_server
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session, current_project_info, get_project_session

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


def _get_chapter_goal_fallback(chapter_id: str) -> Optional[str]:
    """Retrieve the chapter goal using multiple fallback sources to avoid missing data."""
    if not chapter_id:
        return None
    # Fallback 1: SQLite state store
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore
        store = SQLiteStateStore(ws_server.get_root_dir())
        for ch in store.get_chapters():
            if str(ch.get("chapter_id")) == str(chapter_id):
                goal = ch.get("goal") or ch.get("chapter_goal")
                if goal:
                    return goal
    except Exception:
        pass

    # Fallback 2: outline.json
    try:
        outline = ws_server.get_outline()
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
        chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
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


def _get_assistant_llm() -> Any:
    """Resolve and create LLM client for assistant."""
    try:
        from novel_agent.pipeline import load_pipeline_settings
        root = ws_server.get_root_dir()
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
    """Parse output text of the assistant LLM to extract actions."""
    import re
    text = text.strip()
    actions: List[Dict[str, Any]] = []
    marker = "===ACTIONS==="
    
    if marker in text:
        parts = text.split(marker)
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
        
    return {"reply": reply, "actions": actions}


# ---- API Endpoints ----

async def build_assistant_context(session: ProjectSession) -> Dict[str, Any]:
    """Build compact software-state summary for the pet bubble (HTTP or internal callers)."""
    session = coerce_project_session(session)
    tasks: List[Dict[str, Any]] = []
    try:
        tasks = await ws_server._get_task_manager().list_tasks_async()
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

        agent_runtime_logs = tail_runtime_logs(60)
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

            factory = build_factory_dashboard(root, session.project_id, _running_task_count())
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
    issues = []
    suggestions = []
    
    ignored_ids = ignored_task_ids.split(",") if ignored_task_ids else []
    
    if not active_project:
        issues.append({
            "code": "NO_ACTIVE_PROJECT",
            "level": "error",
            "message": "当前未选择或创建任何小说项目。",
        })
        suggestions.append({
            "label": "创建/选择项目",
            "type": "navigate",
            "payload": {"route": "/"}
        })
    else:
        root = session.root_dir
        try:
            from novel_agent.services.arc_queue import load_arc_progress

            batch_progress = load_arc_progress(root)
            if batch_progress.get("status") == "paused":
                reason = batch_progress.get("pause_reason") or "circuit_breaker"
                arc_id = batch_progress.get("last_arc_id") or "—"
                ch_id = batch_progress.get("last_chapter_id") or "—"
                streak = batch_progress.get("fail_streak") or 0
                issues.append({
                    "code": "NOVEL_BATCH_PAUSED",
                    "level": "warning",
                    "message": (
                        f"全书批量已暂停（{reason}），卷 {arc_id} / 章 {ch_id}"
                        + (f"，连续失败 {streak} 次" if streak else "")
                    ),
                })
                suggestions.append({
                    "label": "去章节维护续跑",
                    "type": "navigate",
                    "payload": {"route": "/chapters/maintenance"},
                })
        except Exception:
            pass

        # Check LLM Configuration
        try:
            from novel_agent.pipeline import load_pipeline_settings
            config_data = load_pipeline_settings(root)
            llm_settings = config_data.get("llm", {})
            
            from web.model_library import ModelLibrary
            lib = ModelLibrary(root)
            models_library = lib._load().get("models", {})
            
            default_model_id = llm_settings.get("daily_model_id") or llm_settings.get("default_model_id")
            
            def _should_use_library_default(settings_dict):
                if settings_dict.get("daily_model_id") or settings_dict.get("default_model_id") or settings_dict.get("default", {}).get("model_ref"):
                    return False
                prov = settings_dict.get("provider")
                nested_prov = settings_dict.get("default", {}).get("provider")
                return prov in (None, "", "static") and nested_prov in (None, "", "static")
                
            if not default_model_id and _should_use_library_default(llm_settings):
                default_model_id = next(iter(models_library), None)
                
            actual_provider = None
            if default_model_id and default_model_id in models_library:
                actual_provider = models_library[default_model_id].get("provider")
            else:
                nested_ref = llm_settings.get("default", {}).get("model_ref")
                if nested_ref and nested_ref in models_library:
                    actual_provider = models_library[nested_ref].get("provider")
                else:
                    actual_provider = llm_settings.get("default", {}).get("provider") or llm_settings.get("provider")
            
            provider = actual_provider or "static"
            
            if config_data.get("llm", {}).get("provider") == "":
                provider = ""
            
            if not provider:
                issues.append({
                    "code": "MISSING_LLM_CONFIG",
                    "level": "error",
                    "message": "项目默认模型（LLM）配置缺失，小说生成无法启动。",
                })
                suggestions.append({
                    "label": "配置项目模型",
                    "type": "navigate",
                    "payload": {"route": "/config"}
                })
            elif provider == "static":
                issues.append({
                    "code": "STATIC_LLM_WARNING",
                    "level": "warning",
                    "message": "当前项目日常档模型处于测试占位状态（Static），无法生成真实小说。您可以在模型路由中设定真实模型。",
                })
                suggestions.append({
                    "label": "配置项目日常档模型",
                    "type": "navigate",
                    "payload": {"route": "/config"}
                })
        except Exception as e:
            issues.append({
                "code": "CONFIG_LOAD_FAILED",
                "level": "error",
                "message": f"加载项目配置文件失败：{str(e)}",
            })
            
        # Check Tasks Status
        try:
            tasks = await ws_server._get_task_manager().list_tasks_async()
            seen_chapters = set()
            unresolved_failed = []
            for t in tasks:
                ch_id = t.get("chapter_id")
                if ch_id:
                    if ch_id not in seen_chapters:
                        seen_chapters.add(ch_id)
                        if t.get("status") == "failed":
                            unresolved_failed.append(t)
                else:
                    if t.get("status") == "failed":
                        unresolved_failed.append(t)
            failed_tasks = [t for t in unresolved_failed if t.get("task_id") not in ignored_ids]
            if failed_tasks:
                latest = failed_tasks[0]
                ch_id = latest.get("chapter_id")
                if ch_id:
                    goal = latest.get("goal") or _get_chapter_goal_fallback(ch_id)
                    gate_line = ""
                    try:
                        from novel_agent.services.assistant_snapshot import summarize_unified_gate

                        gs = summarize_unified_gate(root, str(ch_id))
                        if gs:
                            gate_line = f"；{gs}"
                    except Exception:
                        pass
                    issues.append({
                        "code": "RECENT_TASK_FAILED",
                        "level": "warning",
                        "message": f"最近章节任务 {ch_id} 执行失败：{latest.get('error')}{gate_line}",
                    })
                    suggestions.append({
                        "label": f"查看第 {ch_id} 章详情",
                        "type": "navigate",
                        "payload": {"route": f"/chapters/{ch_id}"},
                    })
                    suggestions.append({
                        "label": f"重试第 {ch_id} 章",
                        "type": "retry_task",
                        "payload": {"chapter_id": ch_id, "goal": goal}
                    })
                    suggestions.append({
                        "label": "查看详细日志",
                        "type": "navigate",
                        "payload": {"route": "/logs"},
                    })
        except Exception:
            pass
            
    status = "ok"
    if any(i["level"] == "error" for i in issues):
        status = "error"
    elif any(i["level"] == "warning" for i in issues):
        status = "warning"
        
    return {
        "status": status,
        "issues": issues,
        "suggestions": suggestions,
    }


@router.post("/api/assistant/fix")
async def execute_assistant_fix(req: FixRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Execute low-risk automatic fix action."""
    session = coerce_project_session(session)
    fix_type = req.fix_type
    payload = req.payload
    
    if fix_type == "test_model":
        try:
            from novel_agent.agents.base import OpenAILLM

            client = _get_assistant_llm()
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
            goal = _get_chapter_goal_fallback(chapter_id)
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
                    
            task_id = await ws_server._get_task_manager().submit_chapter(
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

            task = await rewrite_chapter(str(chapter_id))
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

            task = await rerun_chapter_gate(str(chapter_id))
            return {
                "success": True,
                "task_id": task.task_id,
                "message": f"第 {chapter_id} 章已提交门禁重跑",
            }
        except HTTPException as exc:
            return {"success": False, "error": str(exc.detail)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    else:
        raise HTTPException(400, f"Unsupported fix type: {fix_type}")


# Include sub-routers for chat and editor
from web.routes.assistant_chat import router as chat_router
from web.routes.assistant_editor import router as editor_router

router.include_router(chat_router)
router.include_router(editor_router)
