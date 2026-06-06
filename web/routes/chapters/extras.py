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

router = APIRouter()

@router.get("/api/scrapbook")
def get_scrapbook(query: Optional[str] = "", chapter_id: Optional[str] = None) -> List[Dict[str, Any]]:
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


_PIPELINE_ALERT_STAGES = {
    "quality_blocked": "质量门禁未通过，落库已暂停",
    "approval_rejected": "审批未通过，已回滚审校检查点",
    "batch_retry": "批量运行已跳过，待重试本章",
    "external_review_pending": "已标记待外审，请平台试发后回改",
}


@router.get("/api/pipeline-alerts")
def list_pipeline_alerts() -> Dict[str, Any]:
    """Chapters whose checkpoint indicates a blocked or rejected pipeline gate."""
    root = ws_server.require_project_root()
    chapters_root = root / "workspace" / "chapters"

    alerts: List[Dict[str, Any]] = []
    if not chapters_root.exists():
        chapters_root.mkdir(parents=True, exist_ok=True)
    for chapter_dir in sorted(chapters_root.glob("chapter_*")):
        checkpoint_path = chapter_dir / "checkpoint.json"
        if not checkpoint_path.exists():
            continue
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if checkpoint.get("resolved_at"):
            continue

        last_stage = str(checkpoint.get("last_stage") or "")
        if last_stage not in _PIPELINE_ALERT_STAGES:
            continue

        chapter_id = checkpoint.get("chapter_id") or chapter_dir.name.replace("chapter_", "")
        quality_summary: Dict[str, Any] = {}
        quality_path = chapter_dir / "reports" / "quality.json"
        if quality_path.exists():
            try:
                quality = json.loads(quality_path.read_text(encoding="utf-8"))
                guard = quality.get("guard_summary") or {}
                quality_summary = {
                    "mode": quality.get("mode"),
                    "overall_pass": quality.get("overall_pass"),
                    "overall_status": guard.get("overall_status"),
                    "blocked_by": guard.get("blocked_by") or [],
                }
            except (json.JSONDecodeError, OSError):
                pass

        alerts.append(
            {
                "chapter_id": chapter_id,
                "last_stage": last_stage,
                "message": _PIPELINE_ALERT_STAGES[last_stage],
                "completed_stages": checkpoint.get("completed_stages") or [],
                "timestamp": checkpoint.get("timestamp"),
                "quality": quality_summary,
                "source": "checkpoint",
            }
        )

    seen_ids = {a["chapter_id"] for a in alerts}
    try:
        from novel_agent.services.batch_retry_queue import list_pending_retries

        for item in list_pending_retries(root):
            cid = str(item.get("chapter_id") or "")
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)
            alerts.append(
                {
                    "chapter_id": cid,
                    "last_stage": "batch_retry",
                    "message": item.get("message")
                    or _PIPELINE_ALERT_STAGES["batch_retry"],
                    "completed_stages": [],
                    "timestamp": item.get("timestamp"),
                    "quality": {},
                    "source": "batch_retry",
                    "arc_id": item.get("arc_id"),
                    "retry_reason": item.get("reason"),
                }
            )
    except Exception:
        pass

    try:
        from novel_agent.services.external_review import list_pending_external

        for item in list_pending_external(root):
            cid = str(item.get("chapter_id") or "")
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)
            alerts.append(
                {
                    "chapter_id": cid,
                    "last_stage": "external_review_pending",
                    "message": _PIPELINE_ALERT_STAGES["external_review_pending"],
                    "completed_stages": [],
                    "timestamp": item.get("updated_at"),
                    "quality": {},
                    "source": "external_review",
                    "external_note": item.get("note", ""),
                }
            )
    except Exception:
        pass

    alerts.sort(
        key=lambda a: (
            a.get("last_stage") not in ("quality_blocked", "batch_retry"),
            str(a.get("chapter_id")),
        )
    )
    return {"alerts": alerts}


@router.patch("/api/chapters/{chapter_id}/external-review")
def patch_external_review(chapter_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    from web.models import ExternalReviewUpdate

    from novel_agent.services.external_review import set_external_review_status

    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    req = ExternalReviewUpdate(**body)
    row = set_external_review_status(
        ws_server.get_root_dir(),
        safe_id,
        req.status,
        note=req.note or "",
    )
    return {"chapter_id": safe_id, **row}


@router.post("/api/chapters/export-trial")
def export_chapters_for_trial(body: Dict[str, Any]) -> Dict[str, Any]:
    """Plain-text bundle for pasting to external platforms."""
    from web.models import TrialExportRequest

    req = TrialExportRequest(**body)
    root = ws_server.get_root_dir()
    chapters_root = root / "workspace" / "chapters"
    ids = req.chapter_ids
    if not ids:
        for d in sorted(chapters_root.glob("chapter_*")) if chapters_root.is_dir() else []:
            ids.append(d.name.replace("chapter_", ""))
    parts: List[str] = []
    exported: List[str] = []
    for raw_id in ids[:50]:
        safe_id = ws_server._validate_id(str(raw_id), "chapter_id")
        chapter_dir = chapters_root / f"chapter_{safe_id}"
        if not chapter_dir.is_dir():
            continue
        plan = ws_server._read_json(chapter_dir / "plan.json")
        body_text = ws_server._read_text(chapter_dir / "chapter_final.txt").strip()
        if not body_text:
            continue
        title = (plan.get("chapter_title") or "").strip()
        if req.include_titles and title:
            parts.append(f"=== 第 {safe_id} 章 {title} ===\n\n{body_text}")
        else:
            parts.append(f"=== 第 {safe_id} 章 ===\n\n{body_text}")
        exported.append(safe_id)
    text = "\n\n---\n\n".join(parts)
    if not text:
        raise HTTPException(400, "没有可导出的章节正文")
    return {
        "chapter_ids": exported,
        "text": text,
        "char_count": len(text),
    }


@router.post("/api/pipeline-alerts/{chapter_id}/dismiss")
def dismiss_pipeline_alert(chapter_id: str) -> Dict[str, Any]:
    """Mark a pipeline alert as handled without deleting chapter artifacts."""
    from datetime import datetime

    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
    checkpoint_path = chapter_dir / "checkpoint.json"
    if not checkpoint_path.exists():
        try:
            from novel_agent.services.batch_retry_queue import dismiss_batch_retry

            if dismiss_batch_retry(ws_server.get_root_dir(), safe_id):
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
        from novel_agent.services.batch_retry_queue import dismiss_batch_retry

        dismiss_batch_retry(ws_server.get_root_dir(), safe_id)
    except Exception:
        pass
    return {"status": "ok", "chapter_id": safe_id, "resolved_at": checkpoint["resolved_at"]}
