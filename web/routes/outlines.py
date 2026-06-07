import json
import copy
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request

import web.context as ws_server
import web.helpers as ws_helpers
from web.models import (
    NovelPlanRequest,
    ChapterPlanRequest,
    NovelRunRequest,
    NovelArcRunRequest,
    NovelContinueRequest,
)
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.control.chapter_window import build_pacing_report, normalize_chapter_window
from novel_agent.control.genre_genes import ensure_genre_genes
from novel_agent.control.outline_structure import normalize_macro_outline
from novel_agent.control.outline_validation import finalize_outline_for_save, validate_outline_document
from novel_agent.control.runtime_policy import format_scale_profile_for_chief_editor

router = APIRouter()


def _debug_novel_run_enabled() -> bool:
    import os

    return os.environ.get("NOVEL_AGENT_DEBUG_RUN", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _sync_and_ensure_assets(root: Path, outline: Dict[str, Any]):
    """大纲生成或更新时，一并确保并同步五大核心项目资产文件。"""
    # 1. 联动同步世界观
    try:
        ws_helpers._sync_outline_to_world_bible(root, outline)
    except Exception as exc:
        ws_server.logger.warning("Failed to sync outline to world bible: %s", exc)
        
    # 2. 联动同步角色卡
    try:
        ws_helpers._sync_outline_to_character_cards(root, outline)
    except Exception as exc:
        ws_server.logger.warning("Failed to sync outline to character cards: %s", exc)
        
    # 3–5. 风格指南 / 写作规则 / 敏感词库（统一默认模板）
    ws_helpers.ensure_writing_standards_assets(root)


@router.get("/api/outline")
def get_outline() -> Dict[str, Any]:
    outline_path = ws_server.get_root_dir() / "workspace" / "outline.json"
    if not outline_path.exists():
        return {}
    try:
        return json.loads(outline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@router.put("/api/outline")
def update_outline(body: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(400, "Outline must be a JSON object")
    incoming = dict(body)
    existing = get_outline()
    macro_touched = "macro_outline" in incoming
    if existing:
        merged = {**existing, **incoming}
        if not incoming.get("macro_outline") and existing.get("macro_outline"):
            merged["macro_outline"] = existing["macro_outline"]
        body = merged
    else:
        body = incoming
    body = ensure_genre_genes(body)
    sp = body.get("scale_profile") or {}
    scale = str(sp.get("scale") or "")
    target = int(body.get("target_chapters") or sp.get("target_chapters") or 20)
    if body.get("macro_outline"):
        body["macro_outline"] = normalize_macro_outline(
            body.get("macro_outline") or [],
            target_chapters=target,
            scale=scale,
        )
    root = ws_server.get_root_dir()
    
    # Sync scale_profile and target_chapters to project_meta.json
    scale_profile = body.get("scale_profile")
    target_chapters = body.get("target_chapters")
    meta_path = root / "config" / "project_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if scale_profile:
                meta["scale"] = scale_profile.get("scale", "")
                meta["scale_label"] = scale_profile.get("label", "")
                meta["scale_profile"] = scale_profile
            if target_chapters:
                meta["target_chapters"] = target_chapters
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            ws_server.logger.warning("Failed to sync project meta: %s", exc)

    # Sync default target chars to pipeline.yaml
    if scale_profile and scale_profile.get("target_chars"):
        chars_range = scale_profile.get("target_chars")
    else:
        chars_range = body.get("target_chars_per_chapter")
        
    if chars_range and isinstance(chars_range, list) and len(chars_range) == 2:
        config_path = root / "config" / "pipeline.yaml"
        if config_path.exists():
            try:
                import yaml
                cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                cfg.setdefault("chapter", {})["default_target_chars"] = [int(chars_range[0]), int(chars_range[1])]
                ws_helpers._write_yaml(config_path, cfg)
            except Exception as exc:
                ws_server.logger.warning("Failed to sync pipeline.yaml target chars: %s", exc)

    outline_path = root / "workspace" / "outline.json"
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    outline_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    if scale_profile:
        from novel_agent.services.long_form_preset import sync_pipeline_for_scale

        sync_pipeline_for_scale(root, scale=str(scale_profile.get("scale") or ""))

    # 同步更新项目名称到注册表 projects.json
    chosen_title = body.get("chosen_title")
    if chosen_title:
        try:
            pid = ws_server._active_project_id
            if pid:
                registry = ws_server.project_manager._read_registry()
                if pid in registry.get("projects", {}):
                    registry["projects"][pid]["name"] = chosen_title
                    ws_server.project_manager._write_registry(registry)
        except Exception as exc:
            ws_server.logger.warning("Failed to sync project name in projects.json: %s", exc)

    body = finalize_outline_for_save(body)
    validation = validate_outline_document(
        body,
        strict_macro=macro_touched and bool(body.get("macro_outline")),
    )
    if not validation["valid"]:
        raise HTTPException(400, "；".join(validation["errors"]))

    _sync_and_ensure_assets(root, body)
    from novel_agent.services.outline_sync import check_arc_queue_stale, record_outline_saved

    record_outline_saved(root, body)
    if ws_server._active_project_id:
        ws_server.project_manager.touch_activity(ws_server._active_project_id)
    stale = check_arc_queue_stale(root)
    return {
        **body,
        "validation_warnings": validation.get("warnings") or [],
        "arc_queue_stale": stale,
    }


@router.get("/api/outline/arc-queue-stale")
def get_arc_queue_stale() -> Dict[str, Any]:
    from novel_agent.services.outline_sync import check_arc_queue_stale

    return check_arc_queue_stale(ws_server.require_project_root())


@router.post("/api/outline/arc-queue-synced")
def mark_arc_queue_synced() -> Dict[str, Any]:
    from novel_agent.services.outline_sync import mark_arcs_synced_with_outline

    return mark_arcs_synced_with_outline(ws_server.require_project_root())


@router.post("/api/novel/plan")
def plan_novel(req: NovelPlanRequest) -> Dict[str, Any]:
    """Generate a macro-level novel outline without running chapters."""
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.agents.chief_editor import ChiefEditorAgent
    from novel_agent.prompts import PromptRepository

    root = ws_server.get_root_dir()
    config = PipelineConfig.from_config(root)
    prompts = PromptRepository(root)
    
    # 提取已有大纲设定作为 LLM 约束，防止更新大纲时主角名等变动
    existing_outline = get_outline()
    special_requirements = req.special_requirements or ""
    if existing_outline and not req.overwrite:
        constraints = []
        
        # 1. 继承书名限制
        existing_title = existing_outline.get("chosen_title") or (existing_outline.get("title_options")[0] if existing_outline.get("title_options") else None)
        if existing_title:
            constraints.append(f"作品名称必须为：{existing_title}")
            
        # 2. 继承主角属性限制
        existing_proto = existing_outline.get("protagonist", {})
        existing_proto_name = existing_proto.get("name")
        if existing_proto_name:
            constraints.append(f"主角姓名必须保持为：{existing_proto_name}")
            if existing_proto.get("desire"):
                constraints.append(f"主角核心目标/长期动机必须为：{existing_proto.get('desire')}")
            if existing_proto.get("flaw"):
                constraints.append(f"主角缺陷/创伤必须为：{existing_proto.get('flaw')}")
            if existing_proto.get("edge"):
                constraints.append(f"主角优势/特殊金手指必须为：{existing_proto.get('edge')}")
                
        # 3. 继承配角限制
        existing_cast = existing_outline.get("main_cast", [])
        if existing_cast:
            cast_names = []
            for c in existing_cast:
                if isinstance(c, dict) and c.get("name"):
                    cast_names.append(f"{c.get('name')}({c.get('role', '配角')})")
                elif isinstance(c, str):
                    cast_names.append(c)
            if cast_names:
                constraints.append(f"重要配角姓名与角色必须继续沿用：{', '.join(cast_names)}")
                
        if constraints:
            constraint_str = "\n【已有的大纲设定约束，必须严格遵守，绝对不要修改主角姓名或违背已有核心设定】:\n" + "\n".join(f"- {c}" for c in constraints)
            special_requirements = f"{special_requirements}\n{constraint_str}".strip()

    scale_profile = resolve_scale_profile(
        target_chapters=req.target_chapters,
        scale=req.scale,
        scale_label=req.scale_label,
    )
    scale_context = format_scale_profile_for_chief_editor(scale_profile)

    editor = ChiefEditorAgent(config.get_llm("chief_editor"), prompts)
    outline = editor.plan_novel(
        theme=req.theme,
        genre=req.genre,
        target_chapters=req.target_chapters,
        special_requirements=special_requirements,
        scale_context=scale_context,
    )
    if existing_outline and not req.overwrite:
        outline = ws_helpers._preserve_outline_identity(outline, existing_outline)

    if not outline.get("chosen_title") and outline.get("title_options"):
        opts = outline.get("title_options")
        if isinstance(opts, list) and opts:
            outline["chosen_title"] = opts[0]
        elif isinstance(opts, str) and opts.strip():
            outline["chosen_title"] = opts.strip()

    outline["scale_profile"] = scale_profile
    outline["target_chapters"] = req.target_chapters
    outline = finalize_outline_for_save(outline)
    validation = validate_outline_document(outline)
    # Save outline
    outline_path = root / "workspace" / "outline.json"
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    outline_path.write_text(
        json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sp = outline.get("scale_profile") or {}
    from novel_agent.services.long_form_preset import sync_pipeline_for_scale

    sync_pipeline_for_scale(root, scale=str(sp.get("scale") or req.scale or ""))

    # 同步更新项目名称到注册表 projects.json
    chosen_title = outline.get("chosen_title")
    if chosen_title:
        try:
            pid = ws_server._active_project_id
            if pid:
                registry = ws_server.project_manager._read_registry()
                if pid in registry.get("projects", {}):
                    registry["projects"][pid]["name"] = chosen_title
                    ws_server.project_manager._write_registry(registry)
        except Exception as exc:
            ws_server.logger.warning("Failed to sync project name in projects.json: %s", exc)

    _sync_and_ensure_assets(root, outline)
    from novel_agent.services.outline_sync import check_arc_queue_stale, record_outline_saved

    record_outline_saved(root, outline)
    return {
        **outline,
        "validation_warnings": validation.get("warnings") or [],
        "arc_queue_stale": check_arc_queue_stale(root),
        "planning_staged": req.target_chapters >= 200
        or str(scale_profile.get("scale") or "") in ("epic", "infinite", "long"),
    }


@router.post("/api/novel/chapter-plan")
def generate_chapter_plan(req: ChapterPlanRequest) -> Dict[str, Any]:
    from novel_agent.services.rolling_planner import _macro_arc_for_chapter, split_window_briefs
    from novel_agent.services.writing_context import (
        format_context_for_managing_editor,
        gather_recent_writing_context,
    )

    root = ws_server.get_root_dir()
    outline = get_outline()
    if not outline:
        raise HTTPException(400, "No outline found. Generate or save an outline first.")

    start = req.start_chapter
    macro_index, macro_arc = _macro_arc_for_chapter(outline, start)
    ctx = gather_recent_writing_context(root, before_chapter=start)
    writing_context = format_context_for_managing_editor(ctx)

    result = split_window_briefs(
        root,
        start_chapter=start,
        count=req.count,
        instructions=req.instructions,
        macro_arc_index=macro_index,
        writing_context=writing_context,
    )
    chapters = []
    arc_goal = macro_arc.get("goal", "推进主线")
    for index, chapter in enumerate(result.get("chapters", [])[: req.count]):
        chapter_id = chapter.get("chapter_id") or f"{start + index:03d}"
        chapters.append({
            "chapter_id": chapter_id,
            "title": chapter.get("chapter_title") or chapter.get("title") or f"第 {start + index} 章",
            "goal": chapter.get("chapter_goal") or chapter.get("goal") or arc_goal,
            "chapter_type": chapter.get("chapter_type", ""),
            "scene_type": chapter.get("scene_type", ""),
            "detail_level": chapter.get("detail_level", ""),
            "plot_task": chapter.get("plot_task", {}),
            "character_task": chapter.get("character_task", {}),
            "payoff_task": chapter.get("payoff_task", {}),
            "foreshadow": chapter.get("foreshadow", {}),
            "input_state": chapter.get("input_state", ""),
            "output_state": chapter.get("output_state", ""),
            "hook": chapter.get("hook", ""),
            "hook_type": chapter.get("hook_type", ""),
            "reader_payoff": chapter.get("reader_payoff", ""),
            "must_include": chapter.get("must_include", []),
            "must_not_include": chapter.get("must_not_include", []),
        })
    chapters = normalize_chapter_window(chapters)
    return {
        "outline": outline,
        "macro_arc_index": macro_index,
        "macro_arc_id": macro_arc.get("arc_id"),
        "macro_arc_name": macro_arc.get("name"),
        "arc": {k: v for k, v in result.items() if k != "chapters"},
        "chapters": chapters,
        "pacing_report": build_pacing_report(chapters),
        "writing_context_used": bool(ctx.get("recent_chapters")),
    }


@router.get("/api/outline/queue-status")
def get_outline_queue_status() -> Dict[str, Any]:
    from novel_agent.services.outline_queue_status import build_outline_queue_status

    root = ws_server.get_root_dir()

    def _complete(chapter_id: str) -> bool:
        d = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
        p = d / "chapter_final.txt"
        return p.is_file() and len(p.read_text(encoding="utf-8").strip()) > 100

    try:
        return build_outline_queue_status(root, complete_fn=_complete)
    except OSError:
        return build_outline_queue_status(root)


@router.get("/api/novel/batch-status")
def get_novel_batch_status() -> Dict[str, Any]:
    from novel_agent.services.arc_queue import load_arc_progress, load_workspace_arcs

    from novel_agent.services.progress_summary import build_progress_summary

    root = ws_server.get_root_dir()
    progress = load_arc_progress(root)
    arcs = load_workspace_arcs(root)
    summary = build_progress_summary(root)
    return {
        "status": progress.get("status", "idle"),
        "paused": progress.get("status") == "paused",
        "pause_reason": progress.get("pause_reason", ""),
        "last_arc_id": progress.get("last_arc_id", ""),
        "last_chapter_id": progress.get("last_chapter_id", ""),
        "fail_streak": progress.get("fail_streak", 0),
        "completed_chapters": progress.get("completed_chapters", 0),
        "arc_count": len(arcs),
        "progress": progress,
        "pending_retry_count": summary.get("pending_retry_count", 0),
        "pending_gate_count": summary.get("pending_gate_count", 0),
        "pending_total": summary.get("pending_total", 0),
        "authoritative_progress_note": summary.get("progress_note", ""),
        "progress_summary": summary,
    }


@router.get("/api/novel/autopilot-rounds")
def list_autopilot_rounds(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Read workspace/autopilot_rounds.jsonl for ops / monitor UI."""
    root = ws_server.get_root_dir()
    path = root / "workspace" / "autopilot_rounds.jsonl"
    rows: List[Dict[str, Any]] = []
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except json.JSONDecodeError:
                    continue
        except OSError:
            rows = []
    total = len(rows)
    start = max(0, int(offset))
    end = start + max(1, min(int(limit), 200))
    page = list(reversed(rows))[start:end]
    return {"total": total, "offset": start, "limit": limit, "rounds": page}


@router.get("/api/novel/cost-summary")
def novel_cost_summary() -> Dict[str, Any]:
    """SQLite llm_cost_log totals plus recent autopilot round token usage."""
    from novel_agent.services.cost_summary import build_cost_summary

    return build_cost_summary(ws_server.get_root_dir())


@router.get("/api/novel/progress-summary")
def novel_progress_summary() -> Dict[str, Any]:
    from novel_agent.services.progress_summary import build_progress_summary

    return build_progress_summary(ws_server.get_root_dir())


@router.get("/api/novel/arc-progress")
def get_arc_progress() -> Dict[str, Any]:
    from novel_agent.services.arc_queue import load_arc_progress, load_workspace_arcs

    root = ws_server.get_root_dir()
    arcs = load_workspace_arcs(root)
    return {
        "progress": load_arc_progress(root),
        "arcs": [
            {
                "arc_id": a.get("arc_id"),
                "arc_name": a.get("arc_name"),
                "chapter_count": len(a.get("chapters") or []),
            }
            for a in arcs
        ],
    }


@router.post("/api/novel/ensure-queue")
async def ensure_novel_queue(request: Request) -> Dict[str, Any]:
    """Build or replenish arc chapter queue without rewriting the macro outline."""
    import logging

    from novel_agent.pipeline import PipelineConfig
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.services.rolling_planner import prepare_queue_for_run

    root = ws_server.require_project_root()
    outline_path = root / "workspace" / "outline.json"
    if not outline_path.exists():
        raise HTTPException(400, "未找到作品大纲，请先生成大纲。")
    log = logging.getLogger("web.outlines")

    async def _client_cancelled() -> bool:
        return await request.is_disconnected()

    from web.runtime_log_buffer import append_runtime_log

    def _push_status(message: str) -> None:
        append_runtime_log(
            {"message": message, "step": "ensure_queue", "level": "info", "source": "web"}
        )

    try:
        log.info("ensure-queue: start (may call managing_editor LLM for arc split)")
        _push_status("同步卷队列开始（首次可能调用主编拆章，请稍候）…")
        config = PipelineConfig.from_config(root)
        orchestrator = NovelOrchestrator(config)
        stats = await prepare_queue_for_run(
            orchestrator,
            cancel_check=_client_cancelled,
            status_callback=_push_status,
        )
        _push_status(
            "同步卷队列完成"
            f"（新建卷 {stats.get('arcs_created', 0)}，补章 {stats.get('briefs_added', 0)}，"
            f"待写 {stats.get('pending_briefs', 0)}）"
        )
        log.info("ensure-queue: done %s", stats)
    except InterruptedError as exc:
        log.info("ensure-queue: cancelled (%s)", exc)
        _push_status("同步卷队列已取消")
        raise HTTPException(499, "同步卷队列已取消。") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logging.getLogger("web.outlines").exception("ensure-queue failed")
        raise HTTPException(
            500,
            f"同步卷队列失败：{exc}。请检查设置中的模型配置，或查看日志中心任务流水。",
        ) from exc
    from novel_agent.services.outline_sync import mark_arcs_synced_with_outline

    sync_meta = mark_arcs_synced_with_outline(root)
    return {"status": "ok", "arc_sync": sync_meta, **stats}


@router.post("/api/novel/run-arc")
async def run_novel_arc(req: NovelArcRunRequest) -> Dict[str, Any]:
    """Run chapter generation for one or more arcs (workspace/arc_*.json)."""
    if not _debug_novel_run_enabled():
        raise HTTPException(
            403,
            "调试接口已关闭。请设置环境变量 NOVEL_AGENT_DEBUG_RUN=1 或使用 ensure-queue + continue。",
        )
    outline_path = ws_server.get_root_dir() / "workspace" / "outline.json"
    if not outline_path.exists():
        raise HTTPException(400, "未找到作品大纲，请先生成大纲。")
    if not req.arc_id and not req.arc_ids and not req.start_arc_id:
        raise HTTPException(400, "请指定 arc_id、arc_ids 或 start_arc_id。")
    task_id = await ws_server._get_task_manager().submit_arc_run(
        arc_id=req.arc_id,
        arc_ids=req.arc_ids,
        start_arc_id=req.start_arc_id,
        resume=req.resume,
        max_chapters=req.max_chapters,
        dry_run=req.dry_run,
    )
    return {"task_id": task_id, "status": "pending"}


@router.get("/api/novel/readiness")
async def novel_readiness() -> Dict[str, Any]:
    """开书清单 / continue 前置条件（与前端 projectReadiness 对齐）。"""
    from novel_agent.services.novel_run_guard import build_readiness_report

    root = ws_server.get_root_dir()
    report = build_readiness_report(root)
    batch = {"paused": False}
    try:
        from novel_agent.services.arc_queue import load_arc_progress

        prog = load_arc_progress(root)
        batch = {
            "paused": prog.get("status") == "paused",
            "pause_reason": prog.get("pause_reason"),
            "last_arc_id": prog.get("last_arc_id"),
            "last_chapter_id": prog.get("last_chapter_id"),
            "fail_streak": prog.get("fail_streak"),
        }
    except Exception:
        pass
    return {**report, "novel_batch": batch}


@router.post("/api/novel/continue")
async def continue_novel(req: NovelContinueRequest) -> Dict[str, Any]:
    """Resume arc batch from saved progress (long/epic runs)."""
    from novel_agent.services.novel_run_guard import validate_novel_continue

    root = ws_server.get_root_dir()
    ok, detail = validate_novel_continue(root, force_resume=req.force_resume)
    if not ok:
        raise HTTPException(400, detail)

    try:
        task_id = await ws_server._get_task_manager().submit_novel_continue(
        resume=req.resume,
        max_chapters=req.max_chapters,
        dry_run=req.dry_run,
        autopilot=req.autopilot,
        full_book=req.full_book,
        chapters_per_round=req.chapters_per_round,
        max_rounds=req.max_rounds,
        )
    except ValueError as exc:
        from novel_agent.errors import ErrorCode, classify_exception, http_error_detail

        code, _hint = classify_exception(exc)
        status = 409 if code == ErrorCode.NOVEL_BATCH_RUNNING else 400
        if code == ErrorCode.UNKNOWN and "already running" in str(exc).lower():
            code = ErrorCode.NOVEL_BATCH_RUNNING
            status = 409
        raise HTTPException(status, http_error_detail(code)) from exc
    return {
        "task_id": task_id,
        "status": "pending",
        "autopilot": req.autopilot,
    }


@router.post("/api/novel/run")
async def run_novel(req: NovelRunRequest) -> Dict[str, Any]:
    """Run the full multi-chapter novel generation as a background task."""
    if not _debug_novel_run_enabled():
        raise HTTPException(
            403,
            "调试接口已关闭。请设置环境变量 NOVEL_AGENT_DEBUG_RUN=1 或使用工作台连写路径。",
        )
    outline_path = ws_server.get_root_dir() / "workspace" / "outline.json"
    if outline_path.exists():
        try:
            outline_data = json.loads(outline_path.read_text(encoding="utf-8"))
            if not outline_data.get("chosen_title"):
                raise HTTPException(400, "生成小说要求在大纲中确定小说最终名称。")
        except (json.JSONDecodeError, OSError):
            raise HTTPException(400, "大纲数据解析失败，请先生成大纲。")
    else:
        raise HTTPException(400, "未找到作品大纲，请先生成大纲。")

    task_id = await ws_server._get_task_manager().submit_novel(
        theme=req.theme,
        genre=req.genre,
        target_chapters=req.target_chapters,
        special_requirements=req.special_requirements,
        dry_run=req.dry_run,
    )
    return {"task_id": task_id, "status": "pending"}
