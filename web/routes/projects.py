import copy
import json
import uuid
import zipfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import httpx
import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, current_project_info, get_project_session
from web.llm_errors import model_provider_http_error
import logging

ws_server._write_yaml = ws_helpers._write_yaml
ws_server._validate_id = ws_helpers._validate_id
ws_server._ensure_dirs = ws_helpers._ensure_dirs
ws_server._init_prompt_defaults = ws_helpers._init_prompt_defaults
ws_server._sync_outline_to_character_cards = ws_helpers._sync_outline_to_character_cards
ws_server._sync_outline_to_world_bible = ws_helpers._sync_outline_to_world_bible
ws_server._preserve_outline_identity = ws_helpers._preserve_outline_identity
ws_server.logger = logging.getLogger("web.server")
from pydantic import BaseModel

from web.models import (
    ProjectCreateRequest,
    NovelPlanRequest,
    ChapterPlanRequest,
    NovelRunRequest,
    AnalyzeIntroRequest,
    GenerateCoverRequest,
    SaveCoverRequest,
    RewriteDescriptionRequest,
    UpdateDescriptionRequest,
    UpdatePlatformRequest,
    UpdateAuthorLabelRequest,
)
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.control.chapter_window import build_pacing_report, normalize_chapter_window
from novel_agent.control.genre_genes import ensure_genre_genes
from novel_agent.control.outline_structure import normalize_macro_outline


router = APIRouter()


class ProjectPinRequest(BaseModel):
    pinned: bool = True


MAX_PROJECT_ZIP_BYTES = 50 * 1024 * 1024
MAX_PROJECT_ZIP_FILES = 5000
MAX_PROJECT_ZIP_UNCOMPRESSED_BYTES = 500 * 1024 * 1024


@router.get("/api/projects")
def list_projects() -> List[Dict[str, Any]]:
    return ws_server.project_manager.list_projects()


@router.put("/api/projects/{pid}/pin")
def pin_project(pid: str, req: ProjectPinRequest) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    return ws_server.project_manager.set_pinned(pid, req.pinned)


@router.get("/api/projects/current")
def get_current_project(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    return current_project_info(session)


_SENSITIVE_LOG_KEYS = frozenset({
    "token", "access_token", "api_key", "password", "secret", "authorization",
})


def _sanitize_debug_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        lowered = str(key).lower()
        if lowered in _SENSITIVE_LOG_KEYS or lowered.endswith("_token") or lowered.endswith("_key"):
            sanitized[key] = "***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_debug_payload(value)
        else:
            sanitized[key] = value
    return sanitized


@router.post("/api/pet/debug-log")
def pet_debug_log(payload: Dict[str, Any]):
    safe_payload = _sanitize_debug_payload(payload if isinstance(payload, dict) else {})
    ws_server.logger.info("[PET DEBUG] %s", json.dumps(safe_payload, ensure_ascii=False))
    return {"status": "ok"}


@router.post("/api/projects")
def create_project(req: ProjectCreateRequest) -> Dict[str, Any]:
    result = ws_server.project_manager.create_project(req.name, req.description)
    pid = result["id"]
    project_dir = ws_server.BASE_DIR / "projects" / pid

    if req.preset_id:
        ws_server.preset_manager.apply_preset(req.preset_id, project_dir)
    elif req.preset_theme:
        ws_server.preset_manager.apply_composition(
            channel=req.preset_channel or "general",
            theme=req.preset_theme,
            mechanisms=req.preset_mechanisms,
            cool_points=req.preset_cool_points,
            project_dir=project_dir,
        )

    # Save extended metadata
    meta = {}
    if req.genre:
        meta["genre"] = req.genre
    if req.channel:
        meta["channel"] = req.channel
    if req.target_chapters > 0:
        meta["target_chapters"] = req.target_chapters
    scale_profile = req.scale_profile if req.scale_profile.get("max_chapters") else resolve_scale_profile(
        target_chapters=req.target_chapters or None,
        scale=req.scale or str(req.scale_profile.get("scale", "")),
        scale_label=req.scale_label or str(req.scale_profile.get("label", "")),
    )
    if scale_profile:
        meta["scale"] = scale_profile.get("scale", "")
        meta["scale_label"] = scale_profile.get("label", "")
        meta["scale_profile"] = scale_profile
    if req.target_chars_per_chapter:
        meta["target_chars_per_chapter"] = req.target_chars_per_chapter
    # 保存平台特征代号，默认为起点
    meta["platform"] = req.platform or "qidian"
    
    if meta:
        meta_path = project_dir / "config" / "project_meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save outline if provided
    if req.outline:
        outline = dict(req.outline)
        if scale_profile:
            outline["scale_profile"] = scale_profile
        if req.target_chapters > 0:
            outline["target_chapters"] = req.target_chapters
        scale_key = str(scale_profile.get("scale") or req.scale or "").strip().lower()
        target_n = int(outline.get("target_chapters") or req.target_chapters or 20)
        if outline.get("macro_outline"):
            outline["macro_outline"] = normalize_macro_outline(
                outline.get("macro_outline") or [],
                target_chapters=target_n,
                scale=scale_key,
            )
        outline = ensure_genre_genes(outline)
        ws_dir = project_dir / "workspace"
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    scale_key = str(scale_profile.get("scale") or req.scale or "").strip().lower()
    if scale_key:
        from novel_agent.services.long_form_preset import sync_pipeline_for_scale

        sync_pipeline_for_scale(project_dir, scale=scale_key)

    # Update target chars in pipeline config
    if req.target_chars_per_chapter and len(req.target_chars_per_chapter) == 2:
        config_path = project_dir / "config" / "pipeline.yaml"
        if config_path.exists():
            import yaml
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            cfg.setdefault("chapter", {})["default_target_chars"] = req.target_chars_per_chapter
            ws_server._write_yaml(config_path, cfg)

    return result


def _demo_projects_root() -> Path:
    return ws_helpers._demo_projects_dir()


def _find_existing_demo_project(demo_id: str) -> Optional[str]:
    data = ws_server.project_manager._read_registry()
    for pid in data.get("projects", {}):
        meta_path = ws_server.BASE_DIR / "projects" / pid / "config" / "project_meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(meta.get("demo_id") or "") == demo_id:
            return pid
    return None


def _demo_project_title(outline: Dict[str, Any]) -> str:
    chosen = str(outline.get("chosen_title") or "").strip()
    if chosen:
        return chosen
    options = outline.get("title_options")
    if isinstance(options, list) and options:
        first = str(options[0]).strip()
        if first:
            return first
    return "示例书"


@router.post("/api/projects/import-demo")
def import_demo_project(demo_id: str = Query("demo-factory-novel")) -> Dict[str, Any]:
    ws_server._validate_id(demo_id, "demo_id")
    existing = _find_existing_demo_project(demo_id)
    if existing:
        with ws_server._project_lock:
            ws_server.project_manager.switch_project(existing)
            ws_server.activate_project(existing)
        info = ws_server.project_manager._read_registry().get("projects", {}).get(existing, {})
        return {
            "id": existing,
            "name": info.get("name", existing),
            "description": info.get("description", ""),
            "status": "existing",
            "demo_id": demo_id,
        }

    source = _demo_projects_root() / demo_id
    if not source.is_dir():
        raise HTTPException(404, f"Demo project '{demo_id}' not found")

    pid = uuid.uuid4().hex[:8]
    project_dir = ws_server.BASE_DIR / "projects" / pid

    outline = {}
    outline_path = source / "workspace" / "outline.json"
    if outline_path.is_file():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            outline = {}
    title = _demo_project_title(outline)
    description = "内置示例书，用于体验工厂生产流程。"
    now = datetime.now().isoformat()

    with ws_server._project_lock:
        shutil.copytree(source, project_dir)
        ws_server.project_manager.register_project(
            pid,
            {
                "name": title,
                "description": description,
                "created_at": now,
                "updated_at": now,
                "pinned": True,
                "pinned_at": now,
            },
            set_active=True,
        )
        ws_server.activate_project(pid)

    return {
        "id": pid,
        "name": title,
        "description": description,
        "status": "imported",
        "demo_id": demo_id,
    }


@router.delete("/api/projects/{pid}")
def delete_project(pid: str) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    with ws_server._project_lock:
        projects_root = (ws_server.BASE_DIR / "projects").resolve()
        project_dir = (projects_root / pid).resolve()
        if projects_root not in project_dir.parents:
            raise HTTPException(400, "Invalid project_id: path traversal detected")
        if ws_server._task_registry.has_active_tasks(project_dir):
            raise HTTPException(
                409,
                "Cannot delete project while generation tasks are running",
            )
        ws_server.project_manager.delete_project(pid)
    return {"status": "deleted"}


@router.post("/api/projects/{pid}/switch")
def switch_project(pid: str) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    with ws_server._project_lock:
        result = ws_server.project_manager.switch_project(pid)
        ws_server.activate_project(pid)
    return result





@router.post("/api/novel/analyze-intro")
def analyze_novel_intro(req: AnalyzeIntroRequest) -> Dict[str, Any]:
    from novel_agent.pipeline import PipelineConfig
    root = ws_server.get_root_dir()
    config = PipelineConfig.from_config(root)
    
    llm = config.get_llm("chief_editor")
    
    prompt = f"""你是一名专业的网文主编与文学策划专家。请阅读分析以下粘贴的关于一部新小说的素材（包括大纲、构想、脑洞或设定）。你的任务是提炼核心设定，并将其整理成结构化的 JSON 格式，以便自动创建系统项目。
    
【输入素材】
{req.text}

【输出格式要求】
必须直接输出合法的 JSON 代码，不要包含任何前言、旁白或 Markdown 标记（例如不要包裹 ```json 块，直接以 {{ 开头，以 }} 结尾）。
JSON 字段及嵌套结构必须严格按照以下定义：
{{
  "name": "提炼出的最终小说书名（如果素材中没有提及，请根据风格创意起一个好听的网文书名，不要带书名号）",
  "description": "一句话小说梗概/简介（100字以内）",
  "genre": "小说题材类型（例如：玄幻、都市、科幻、历史、游戏、悬疑、仙侠）",
  "context": {{
    "theme": "小说的核心主题、爽点或基调",
    "target_chapters": 100,
    "target_chars": [2000, 3000],
    "summary_card": {{
      "title_suggestions": ["书名候选1", "书名候选2", "书名候选3"],
      "logline": "一句话故事线",
      "genre_positioning": "题材细分定位（如：都市异能、凡人流、无限流、系统逆袭）",
      "target_reader": "目标读者群体",
      "reader_promise": ["读者承诺1", "读者承诺2"],
      "tone": "小说文风基调（如：热血爽快、轻松搞笑、阴暗悬疑、合理严谨）"
    }},
    "protagonist": {{
      "name": "主角姓名（如果素材中没写，请起一个合适的主角名）",
      "desire": "主角的核心目标/原初动机",
      "flaw": "主角的缺陷、创伤或阻碍",
      "edge": "主角的核心优势、金手指或外挂（如：系统、重生成长、无敌体质、神级悟性）"
    }},
    "world_rules": ["世界观规则或力量等级设定1", "世界观规则或力量等级设定2"],
    "antagonistic_forces": ["敌对势力/反派设定1", "敌对势力/反派设定2"],
    "conflict": "贯穿全书的核心矛盾冲突或最大反派"
  }}
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
            
        parsed_data = json.loads(response_text)
        return parsed_data
    except Exception as e:
        ws_server.logger.warning("Failed to analyze intro text: %s", e)
        raise HTTPException(400, f"大模型分析小说设定失败：{e}")





@router.post("/api/projects/{pid}/rewrite-description")
def rewrite_description(pid: str, req: RewriteDescriptionRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    
    # 读大纲作为参考
    outline_path = project_dir / "workspace" / "outline.json"
    title = pid
    genre = "网络小说"
    protagonist_name = "主角"
    protagonist_edge = "金手指"
    protagonist_desire = "动机"
    conflict = "核心矛盾"
    
    if outline_path.exists():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            title = outline.get("chosen_title") or title
            genre = outline.get("genre") or genre
            proto = outline.get("protagonist", {})
            protagonist_name = proto.get("name") or protagonist_name
            protagonist_edge = proto.get("edge") or protagonist_edge
            protagonist_desire = proto.get("desire") or protagonist_desire
            conflict = outline.get("conflict") or conflict
        except Exception:
            pass
            
    from novel_agent.pipeline import PipelineConfig
    config = PipelineConfig.from_config(project_dir)
    llm = config.get_llm("chief_editor")
    
    prompt_rewrite = f"""你是一名资深的网文主编，极其擅长为番茄小说、起点中文网等热门平台的小说撰写吸睛的爆款简介。
请根据以下小说的基本信息、题材、核心矛盾和大纲，重写小说的作品简介。

【小说基本信息】
书名: {title}
题材: {genre}
当前简介: {req.old_description}

【小说详细设定与核心矛盾】
主角: {protagonist_name}
主角金手指: {protagonist_edge}
主角动机: {protagonist_desire}
核心矛盾冲突: {conflict}

【重写风格要求】
{req.style}风格。{req.user_preference if req.user_preference else ""}

【字数与格式要求】
- 简介长度请控制在 150 到 300 字之间（适合番茄作品上传的简介长度，精炼且富有张力）。
- 可以分段，排版清晰，可以使用网文简介常见的排版方式（如：一句核心吸睛语 + 几行正文介绍 + 境界划分/简短排比）。
- 请直接输出重写后的简介文本，不要带任何前言、旁白或 Markdown 标记。
"""
    try:
        rewritten = llm.generate("chief_editor", prompt_rewrite).strip()
        if rewritten.startswith("`") or rewritten.startswith('"'):
            rewritten = rewritten.strip("`\"'")
        return {"description": rewritten}
    except Exception as e:
        raise model_provider_http_error("简介重写", e)


@router.put("/api/projects/{pid}/author-label")
def update_author_label(pid: str, req: UpdateAuthorLabelRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    registry = ws_server.project_manager._read_registry()
    if pid not in registry.get("projects", {}):
        raise HTTPException(404, "Project not found")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    meta_path = project_dir / "config" / "project_meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    label = (req.author_label or "").strip()
    if label:
        meta["author_label"] = label
    else:
        meta.pop("author_label", None)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    ws_server.project_manager.touch_activity(pid)
    return {"status": "updated", "author_label": label}


@router.post("/api/projects/{pid}/update-description")
def update_description(pid: str, req: UpdateDescriptionRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    
    # 1. 更新全局项目注册表 projects.json
    registry = ws_server.project_manager._read_registry()
    if pid not in registry.get("projects", {}):
        raise HTTPException(404, "Project not found")
    registry["projects"][pid]["description"] = req.description
    registry["projects"][pid]["updated_at"] = datetime.now().isoformat()
    ws_server.project_manager._write_registry(registry)
    
    # 2. 同步写入项目的 project_meta.json
    meta_path = project_dir / "config" / "project_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    meta["description"] = req.description
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"status": "updated"}


@router.get("/api/platforms")
def get_platforms() -> List[Dict[str, Any]]:
    from novel_agent.control.platform_profiles import PLATFORM_PROFILES
    results = []
    for k, v in PLATFORM_PROFILES.items():
        results.append({
            "name": v["name"],
            "label": v["label"],
            "pacing_density": v["pacing_density"],
            "setting_detail_weight": v["setting_detail_weight"],
            "dialogue_ratio_range": v["dialogue_ratio_range"],
            "style_prompt": v["style_prompt"],
            "rules_blacklist": v.get("rules_blacklist", [])
        })
    return results


@router.get("/api/projects/{pid}/platform")
def get_project_platform(pid: str) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    meta_path = project_dir / "config" / "project_meta.json"
    platform_name = "qidian"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            platform_name = meta.get("platform", "qidian")
        except Exception:
            pass
    from novel_agent.control.platform_profiles import resolve_platform_profile
    profile = resolve_platform_profile(platform_name)
    return {"platform": platform_name, "label": profile["label"]}


@router.post("/api/projects/{pid}/platform")
def update_project_platform(pid: str, req: UpdatePlatformRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    meta_path = project_dir / "config" / "project_meta.json"
    
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    meta["platform"] = req.platform
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"status": "updated", "platform": req.platform}


from pydantic import BaseModel

class ApplyAdaptiveOutlineRequest(BaseModel):
    new_chapters: List[Dict[str, Any]]


@router.get("/api/projects/{pid}/serial-status")
def get_serial_status(pid: str) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
        
    store = ws_server.get_project_store(pid)
    
    import datetime
    today = datetime.date.today()
    today_chars = 0
    generated_chapters_count = 0
    
    ws_dir = project_dir / "workspace"
    chapters_dir = ws_dir / "chapters"
    if chapters_dir.exists():
        for ch_dir in chapters_dir.glob("chapter_*"):
            txt_path = ch_dir / "chapter_final.txt"
            if txt_path.exists():
                stat = txt_path.stat()
                mtime_date = datetime.date.fromtimestamp(stat.st_mtime)
                try:
                    content = txt_path.read_text(encoding="utf-8").strip()
                    if len(content) > 50:
                        generated_chapters_count += 1
                        if mtime_date == today:
                            from novel_agent.scripts.count_chars import count_chinese_chars
                            today_chars += count_chinese_chars(content)
                except (OSError, json.JSONDecodeError, ImportError):
                    pass
                    
    pending_candidates_count = 0
    try:
        candidates = store.list_state_change_candidates(chapter_id=None)
        pending_candidates_count = len([c for c in candidates if c.get("status") == "pending"])
    except Exception:
        pass
        
    recent_feedback = store.get_recent_feedback(limit=3)
    avg_bounce = 0.0
    if recent_feedback:
        avg_bounce = sum(r.get("bounce_rate", 0.0) for r in recent_feedback) / len(recent_feedback)
        
    crisis_level = "正常"
    if avg_bounce > 0.35:
        crisis_level = "重度危机"
    elif avg_bounce > 0.25:
        crisis_level = "中度警戒"
        
    progress_extra: Dict[str, Any] = {}
    try:
        from novel_agent.services.progress_summary import build_progress_summary

        progress_extra = build_progress_summary(project_dir)
    except Exception:
        progress_extra = {}

    return {
        "today_word_count": today_chars,
        "total_generated_chapters": generated_chapters_count,
        "disk_chapters_with_final": progress_extra.get("disk_chapters_with_final", generated_chapters_count),
        "authoritative_completed": progress_extra.get("authoritative_completed", 0),
        "library_indexed": progress_extra.get("library_indexed", 0),
        "pending_total": progress_extra.get("pending_total", 0),
        "progress_note": progress_extra.get("progress_note", ""),
        "pending_candidates_count": pending_candidates_count,
        "avg_bounce_rate": avg_bounce,
        "crisis_level": crisis_level,
    }


@router.get("/api/projects/{pid}/comments")
def get_project_comments(pid: str) -> List[Dict[str, Any]]:
    ws_server._validate_id(pid, "project_id")
    store = ws_server.get_project_store(pid)
    
    recent_fb = store.get_recent_feedback(limit=3)
    
    from novel_agent.control.serial_engine import generate_virtual_comments
    all_comments = []
    
    if recent_fb:
        for fb in reversed(recent_fb):
            ch_id = fb["chapter_id"]
            bounce = fb["bounce_rate"]
            ch_comments = generate_virtual_comments(ch_id, bounce)
            for c in ch_comments:
                c["chapter_label"] = f"第 {ch_id} 章"
            all_comments.extend(ch_comments)
    else:
        ch_comments = generate_virtual_comments("001", 0.12)
        for c in ch_comments:
            c["chapter_label"] = "新书试读"
        all_comments.extend(ch_comments)
        
    return all_comments


@router.post("/api/projects/{pid}/outline/adaptive-rewrite")
def adaptive_rewrite_outline(pid: str) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
        
    store = ws_server.get_project_store(pid)
    
    from novel_agent.pipeline import PipelineConfig
    config = PipelineConfig.from_config(project_dir)
    llm = config.get_llm("chief_editor")
    
    from novel_agent.control.serial_engine import compute_adaptive_outline
    old_ch, new_ch = compute_adaptive_outline(project_dir, store, llm)
    
    return {
        "old_chapters": old_ch,
        "new_chapters": new_ch
    }


@router.post("/api/projects/{pid}/outline/apply-adaptive")
def apply_adaptive_outline(pid: str, req: ApplyAdaptiveOutlineRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
        
    ws_dir = project_dir / "workspace"
    
    new_map = {ch["chapter_id"]: ch for ch in req.new_chapters if "chapter_id" in ch}
    if not new_map:
        return {"status": "no_changes"}
        
    arc_files = sorted(list(ws_dir.glob("arc_*.json")))
    for arc_file in arc_files:
        try:
            arc_data = json.loads(arc_file.read_text(encoding="utf-8"))
            modified = False
            for ch in arc_data.get("chapters", []):
                ch_id = ch.get("chapter_id")
                if ch_id in new_map:
                    new_val = new_map[ch_id]
                    ch["title"] = new_val.get("chapter_title", ch.get("title", ""))
                    ch["goal"] = new_val.get("chapter_goal", new_val.get("detailed_synopsis", ch.get("goal", "")))
                    ch["must_include"] = new_val.get("handoff_to_scene_planner", {}).get("must_include", ch.get("must_include", []))
                    ch["must_not_include"] = new_val.get("handoff_to_scene_planner", {}).get("must_not_include", ch.get("must_not_include", []))
                    modified = True
            if modified:
                arc_file.write_text(json.dumps(arc_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            raise HTTPException(500, f"Failed to rewrite arc file {arc_file.name}: {e}")
            
    return {"status": "applied"}


@router.get("/api/projects/{pid}/state-candidates")
def get_project_state_candidates(pid: str) -> List[Dict[str, Any]]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
    store = ws_server.get_project_store(pid)
    return store.list_state_change_candidates(chapter_id=None)


@router.post("/api/projects/{pid}/state-candidates/approve-all")
def approve_all_project_candidates(pid: str) -> Dict[str, Any]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
    store = ws_server.get_project_store(pid)
    candidates = store.list_state_change_candidates(chapter_id=None)
    approved_count = 0
    for c in candidates:
        if c.get("status") == "pending" and "id" in c:
            store.accept_candidate(str(c["id"]))
            approved_count += 1
    return {"status": "success", "message": f"Approved {approved_count} candidates"}

# Include sub-router for project archives (Zip import/export)
from web.routes.projects_archive import router as archive_router
router.include_router(archive_router)
