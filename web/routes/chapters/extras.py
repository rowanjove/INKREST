"""Shared imports for chapter route modules."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException
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
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

router = APIRouter()

@router.get("/api/scrapbook")
def get_scrapbook(
    query: Optional[str] = "",
    chapter_id: Optional[str] = None,
    session: ProjectSession = RequireProjectDep,
) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    store = ws_server._get_task_manager().store
    return store.search_scrapbook(query=query, chapter_id=chapter_id)


class FeedbackRequest(BaseModel):
    chapter_id: str
    bounce_rate: float
    retention_rate: float
    active_readers: int


@router.post("/api/projects/{pid}/feedback")
def save_feedback(pid: str, req: FeedbackRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    safe_chapter_id = ws_server._validate_id(req.chapter_id, "chapter_id")
    store = ws_server.get_project_store(pid)
    store.save_reader_feedback(safe_chapter_id, req.bounce_rate, req.retention_rate, req.active_readers)
    return {"status": "saved"}


@router.get("/api/projects/{pid}/feedback")
def list_feedback(pid: str) -> List[Dict[str, Any]]:
    ws_server._validate_id(pid, "project_id")
    store = ws_server.get_project_store(pid)
    return store.get_recent_feedback(limit=100)


@router.get("/api/projects/{pid}/golden-check")
def golden_check(pid: str) -> Dict[str, Any]:
    import json
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    
    chapters_content = {}
    for i in (1, 2, 3):
        ch_id = f"{i:03d}"
        ch_dir = project_dir / "workspace" / "chapters" / f"chapter_{ch_id}"
        txt_path = ch_dir / "chapter_final.txt"
        plan_path = ch_dir / "plan.json"
        
        title = f"第 {i} 章"
        if plan_path.exists():
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                title = plan.get("chapter_title", title)
            except (OSError, json.JSONDecodeError):
                pass
                
        text = ""
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8").strip()
            
        chapters_content[ch_id] = {
            "title": title,
            "text": text,
            "has_content": bool(text and len(text) > 50)
        }
        
    if not any(c["has_content"] for c in chapters_content.values()):
        return {
            "status": "pending",
            "message": "黄金三章 (1-3 章) 尚未生成，请生成正文后再进行质检。",
            "checks": []
        }
        
    prompt_materials = []
    for ch_id, ch_data in chapters_content.items():
        if ch_data["has_content"]:
            prompt_materials.append(f"【{ch_data['title']} (ID: {ch_id})】\n{ch_data['text'][:1500]}...(略)")
            
    prompt_text = "\n\n".join(prompt_materials)
    
    from novel_agent.pipeline import PipelineConfig
    config = PipelineConfig.from_config(project_dir)
    llm = config.get_llm("chief_editor")
    
    prompt = f"""你是一名极其严苛的网文总编辑，专职负责番茄、起点等知名平台的精品小说签约与前三章（黄金三章）质检。
请阅读并评估以下提供的新书前三章内容片段，对其在平台签约潜力、读者留存率进行打分和诊断。

【前三章正文片段】
{prompt_text}

【诊断指标与输出格式】
你必须输出且仅输出符合以下 JSON 格式的字符串，不要有任何 Markdown 包裹标记或前后旁白。
{{
  "overall_score": 85,
  "summary": "一句话整体质检评价",
  "checks": [
    {{
      "indicator": "金手指展现节奏",
      "status": "pass",
      "score": 90,
      "reason": "金手指是否在第一章迅速出现并产生期待感。"
    }},
    {{
      "indicator": "核心期待感与矛盾",
      "status": "warning",
      "score": 75,
      "reason": "核心危机或冲突的铺垫是否到位。"
    }},
    {{
      "indicator": "避坑红线检测",
      "status": "pass",
      "score": 85,
      "reason": "有无明显劝退读者的毒点。"
    }}
  ],
  "suggestions": [
    "针对第1章的具体修改改进建议...",
    "针对第2章的具体修改改进建议...",
    "针对第3章的具体修改改进建议..."
  ]
}}
"""
    try:
        response_text = llm.generate("chief_editor", prompt).strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        parsed = json.loads(response_text)
        parsed["status"] = "success"
        return parsed
    except Exception as exc:
        ws_server.logger.warning("Golden check failed: %s", exc)
        return {
            "status": "error",
            "message": f"黄金三章质检模型执行失败: {exc}",
            "checks": []
        }


@router.get("/api/pipeline-alerts")
def list_pipeline_alerts(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Chapters whose checkpoint indicates a blocked or rejected pipeline gate."""
    from novel_agent.services.pipeline_pending import collect_pipeline_alerts_cached

    session = coerce_project_session(session)
    root = session.root_dir
    chapters_root = root / "workspace" / "chapters"
    if not chapters_root.exists():
        chapters_root.mkdir(parents=True, exist_ok=True)
    return {"alerts": collect_pipeline_alerts_cached(root)}


@router.patch("/api/chapters/{chapter_id}/external-review")
def patch_external_review(
    chapter_id: str,
    body: Dict[str, Any],
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    from web.models import ExternalReviewUpdate

    from novel_agent.services.external_review import set_external_review_status

    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    req = ExternalReviewUpdate(**body)
    row = set_external_review_status(
        session.root_dir,
        safe_id,
        req.status,
        note=req.note or "",
    )
    return {"chapter_id": safe_id, **row}


@router.post("/api/chapters/export-trial")
def export_chapters_for_trial(
    body: Dict[str, Any],
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    """Plain-text bundle for pasting to external platforms."""
    from web.models import TrialExportRequest

    req = TrialExportRequest(**body)
    from novel_agent.services.publishing_workspace import build_trial_bundle

    try:
        return build_trial_bundle(
            session.root_dir,
            chapter_ids=list(req.chapter_ids),
            include_titles=req.include_titles,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/pipeline-alerts/{chapter_id}/dismiss")
def dismiss_pipeline_alert(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    """Mark a pipeline alert as handled without deleting chapter artifacts."""
    from datetime import datetime

    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    checkpoint_path = chapter_dir / "checkpoint.json"
    if not checkpoint_path.exists():
        try:
            from novel_agent.services.batch_retry_queue import dismiss_batch_retry

            if dismiss_batch_retry(session.root_dir, safe_id):
                return {
                    "status": "ok",
                    "chapter_id": safe_id,
                    "resolved_at": datetime.now().isoformat(),
                }
        except Exception:
            pass
        raise HTTPException(404, f"Chapter {safe_id} has no checkpoint")

    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(400, f"Invalid checkpoint: {exc}") from exc

    checkpoint["resolved_at"] = datetime.now().isoformat()
    checkpoint_path.write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        from novel_agent.services.pipeline_pending import invalidate_pipeline_alerts_cache

        invalidate_pipeline_alerts_cache(session.root_dir)
    except Exception:
        pass
    try:
        from novel_agent.services.batch_retry_queue import dismiss_batch_retry

        dismiss_batch_retry(session.root_dir, safe_id)
    except Exception:
        pass
    return {"status": "ok", "chapter_id": safe_id, "resolved_at": checkpoint["resolved_at"]}
