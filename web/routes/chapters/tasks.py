"""Shared imports for chapter route modules."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException

from web.deps import ProjectSession, RequireProjectDep, coerce_project_session
from pydantic import BaseModel, Field

import web.context as ws_server
import web.helpers as ws_helpers

ws_server._validate_id = ws_helpers._validate_id
ws_server._read_json = ws_helpers._read_json
ws_server._read_text = ws_helpers._read_text
ws_server.get_outline = ws_helpers.get_outline
ws_server._delete_chapter_dir = ws_helpers._delete_chapter_dir
ws_server.logger = logging.getLogger("web.server")

from web.models import (
    ChapterRequest,
    BatchChapterRequest,
    TaskStatus,
    ChapterSummary,
    ChapterDetail,
    NovelChatRequest,
    SaveChapterRequest,
)
from novel_agent.scripts.count_chars import count_chinese_chars, wordcount_report

router = APIRouter()


@router.post("/api/chapters/run")
async def run_chapter(req: ChapterRequest, session: ProjectSession = RequireProjectDep) -> TaskStatus:
    session = coerce_project_session(session)
    outline = ws_server.get_outline()
    if not outline or not outline.get("chosen_title"):
        raise HTTPException(400, "生成章节要求在大纲中确定小说最终名称。")
    try:
        # 清理已有的 checkpoint.json，确保是重新运行而非恢复
        safe_id = ws_server._validate_id(req.chapter_id, "chapter_id")
        chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
        checkpoint_path = chapter_dir / "checkpoint.json"
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
            except OSError as e:
                ws_server.logger.warning("Failed to delete checkpoint file %s: %s", checkpoint_path, e)
        
        task_id = await ws_server._get_task_manager().submit_chapter(
            chapter_id=req.chapter_id,
            goal=req.goal,
            dry_run=req.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    task = await ws_server._get_task_manager().get_task_async(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return TaskStatus(**task)


@router.post("/api/chapters/{chapter_id}/resume-audit")
async def resume_chapter_audit(chapter_id: str, session: ProjectSession = RequireProjectDep) -> TaskStatus:
    session = coerce_project_session(session)
    """Resume from audit checkpoint without wiping generation (e.g. quality_blocked)."""
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")

    checkpoint_path = chapter_dir / "checkpoint.json"
    if not checkpoint_path.exists():
        raise HTTPException(
            400,
            f"Chapter {safe_id} has no checkpoint; use full rewrite instead.",
        )

    plan = ws_server._read_json(chapter_dir / "plan.json")
    goal = (
        plan.get("chapter_goal")
        or plan.get("detailed_synopsis")
        or plan.get("chapter_title")
        or f"Resume audit for chapter {safe_id}"
    )
    try:
        task_id = await ws_server._get_task_manager().submit_chapter(
            chapter_id=safe_id,
            goal=goal,
            dry_run=False,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    task = await ws_server._get_task_manager().get_task_async(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return TaskStatus(**task)


@router.post("/api/chapters/{chapter_id}/rerun-gate")
async def rerun_chapter_gate(chapter_id: str, session: ProjectSession = RequireProjectDep) -> TaskStatus:
    session = coerce_project_session(session)
    """Re-run unified_gate only (requires existing final_text + audit.json)."""
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")
    final_path = chapter_dir / "chapter_final.txt"
    if not final_path.is_file() or not final_path.read_text(encoding="utf-8").strip():
        raise HTTPException(400, "本章尚无正文，无法只重跑门禁")
    audit_path = chapter_dir / "reports" / "audit.json"
    if not audit_path.is_file():
        raise HTTPException(400, "缺少审校报告，请先完成审校或重试审校")
    try:
        task_id = await ws_server._get_task_manager().submit_chapter_gate_only(safe_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    task = await ws_server._get_task_manager().get_task_async(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return TaskStatus(**task)


@router.post("/api/chapters/{chapter_id}/rewrite")
async def rewrite_chapter(chapter_id: str, session: ProjectSession = RequireProjectDep) -> TaskStatus:
    session = coerce_project_session(session)
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")
        
    # 清理已有的 checkpoint.json，保证重写会完整重新跑 Steps 2-13
    checkpoint_path = chapter_dir / "checkpoint.json"
    if checkpoint_path.exists():
        try:
            checkpoint_path.unlink()
        except OSError as e:
            ws_server.logger.warning("Failed to delete checkpoint file %s: %s", checkpoint_path, e)
            
    plan = ws_server._read_json(chapter_dir / "plan.json")
    goal = (
        plan.get("chapter_goal")
        or plan.get("detailed_synopsis")
        or plan.get("chapter_title")
        or f"Rewrite chapter {safe_id}"
    )
    try:
        task_id = await ws_server._get_task_manager().submit_chapter(
            chapter_id=safe_id,
            goal=goal,
            dry_run=False,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    task = await ws_server._get_task_manager().get_task_async(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return TaskStatus(**task)


@router.get("/api/chapters/{chapter_id}/suggest-goal")
def suggest_chapter_goal(chapter_id: str, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    root = session.root_dir
    outline = ws_server.get_outline()
    
    # 1. 尝试从 outline.json 里面查是否有该章节的预设大纲目标
    if outline:
        chapters = outline.get("chapters") or []
        for ch in chapters:
            if str(ch.get("chapter_id")) == str(safe_id):
                goal = ch.get("goal") or ch.get("chapter_goal")
                if goal:
                    return {"goal": goal, "source": "outline_preset", "message": "已从作品大纲中恢复该章预设目标"}

    # 2. 若无预设，从上下文（前后章节摘要）使用 AI 预测
    try:
        current_num = int(safe_id)
    except ValueError:
        current_num = 1
        
    prev_id = f"{current_num - 1:03d}"
    next_id = f"{current_num + 1:03d}"
    
    prev_summary = ""
    next_summary = ""
    
    prev_dir = root / "workspace" / "chapters" / f"chapter_{prev_id}"
    if prev_dir.exists():
        prev_summary = ws_server._read_text(prev_dir / "chapter_summary.md")
        if not prev_summary:
            plan = ws_server._read_json(prev_dir / "plan.json")
            prev_summary = plan.get("chapter_goal", "")
            
    next_dir = root / "workspace" / "chapters" / f"chapter_{next_id}"
    if next_dir.exists():
        next_summary = ws_server._read_text(next_dir / "chapter_summary.md")
        if not next_summary:
            plan = ws_server._read_json(next_dir / "plan.json")
            next_summary = plan.get("chapter_goal", "")

    from novel_agent.pipeline import PipelineConfig
    config = PipelineConfig.from_config(root)
    llm = config.get_llm("managing_editor")
    
    title = "未命名"
    if outline:
        titles = outline.get("title_options", ["未命名"])
        title = titles[0] if isinstance(titles, list) and titles else str(titles)

    prompt = f"""你是一名资深网文主编。现在有一部小说的第 {safe_id} 章内容缺失了，需要你根据作品大纲以及前后的章节摘要，智能预测并拟定第 {safe_id} 章的章节写作目标（Goal）。

【作品基本设定】
书名/主题: {title} / {outline.get("core_theme", "未设定") if outline else "未设定"}
一句话梗概: {outline.get("logline", "未设定") if outline else "未设定"}
核心冲突: {outline.get("conflict", "未设定") if outline else "未设定"}
主角: {outline.get("protagonist", {}).get("name", "主角") if outline else "主角"}

【前一章 (第 {prev_id} 章) 摘要】
{prev_summary or "（无历史章节或暂无摘要）"}

【后一章 (第 {next_id} 章) 摘要】
{next_summary or "（无后续章节或暂无摘要）"}

【任务要求】
请根据上述上下文，为第 {safe_id} 章撰写一段具体、清晰的“章节写作目标（Goal）”。
章节目标需要承上启下，交代本章需要发生的关键剧情冲突、人物互动或状态变化，字数在 50-150 字之间。
直接输出该章节目标的文本，不要包含任何旁白、前言或 Markdown 标记。"""

    try:
        predicted_goal = llm.generate("managing_editor", prompt).strip()
        return {"goal": predicted_goal, "source": "ai_predicted", "message": "已由 AI 结合上下文自动预测该章大纲目标"}
    except Exception as e:
        ws_server.logger.warning("Failed to predict chapter goal using LLM: %s", e)
        return {
            "goal": f"第 {safe_id} 章：围绕主线，继续剧情发展，衔接上下文冲突。",
            "source": "fallback",
            "message": "AI 预测失败，生成了默认章节目标"
        }


class RewriteBatchRequest(BaseModel):
    chapter_ids: List[str]
    dry_run: bool = False


@router.post("/api/chapters/run-batch")
async def run_batch(req: BatchChapterRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    outline = ws_server.get_outline()
    if not outline or not outline.get("chosen_title"):
        raise HTTPException(400, "生成章节要求在大纲中确定小说最终名称。")
    chapters = [ch.model_dump() for ch in req.chapters]
    batch_id = await ws_server._get_task_manager().submit_batch(chapters, req.dry_run)
    return {"batch_id": batch_id, "chapter_count": len(chapters)}


@router.post("/api/chapters/rewrite-batch")
async def run_rewrite_batch(req: RewriteBatchRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    outline = ws_server.get_outline()
    if not outline or not outline.get("chosen_title"):
        raise HTTPException(400, "生成章节要求在大纲中确定小说最终名称。")
    
    chapters_to_run = []
    for chapter_id in req.chapter_ids:
        safe_id = ws_server._validate_id(chapter_id, "chapter_id")
        chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
        if not chapter_dir.exists():
            continue
            
        # 清理已有的 checkpoint.json，保证重写会完整重新跑
        checkpoint_path = chapter_dir / "checkpoint.json"
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
            except OSError as e:
                ws_server.logger.warning("Failed to delete checkpoint file %s: %s", checkpoint_path, e)
                
        plan = ws_server._read_json(chapter_dir / "plan.json")
        goal = (
            plan.get("chapter_goal")
            or plan.get("detailed_synopsis")
            or plan.get("chapter_title")
            or f"Rewrite chapter {safe_id}"
        )
        chapters_to_run.append({
            "chapter_id": safe_id,
            "goal": goal,
            "dry_run": req.dry_run
        })
        
    if not chapters_to_run:
        raise HTTPException(400, "没有找到有效的可重写章节。")
        
    batch_id = await ws_server._get_task_manager().submit_batch(chapters_to_run, req.dry_run)
    return {"batch_id": batch_id, "chapter_count": len(chapters_to_run)}


@router.get("/api/chapters/tasks")
async def list_tasks(session: ProjectSession = RequireProjectDep) -> List[TaskStatus]:
    session = coerce_project_session(session)
    tasks = await ws_server._get_task_manager().list_tasks_async()
    return [TaskStatus(**t) for t in tasks]


@router.get("/api/chapters/tasks/queue")
async def get_task_queue(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Project-scoped chapter task queue snapshot and concurrency limits."""
    session = coerce_project_session(session)
    from novel_agent.services.execution_policy import build_execution_snapshot

    manager = ws_server._get_task_manager()
    return {
        **build_execution_snapshot(session.root_dir),
        **manager.get_queue_snapshot(),
    }


@router.get("/api/chapters/tasks/{task_id}")
async def get_task(task_id: str, session: ProjectSession = RequireProjectDep) -> TaskStatus:
    session = coerce_project_session(session)
    task = await ws_server._get_task_manager().get_task_async(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return TaskStatus(**task)


@router.post("/api/chapters/tasks/{task_id}/abort")
async def abort_task(task_id: str, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    task_manager = ws_server._get_task_manager()
    success = await task_manager.abort_task(task_id)
    if not success:
        return {"status": "ignored", "message": f"Task {task_id} not running or not found"}
    return {"status": "aborted", "task_id": task_id}
