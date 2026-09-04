"""Modular diagnostic rules and offline heuristics for the ShanShan assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import re


def run_system_diagnostics(
    root_dir: Optional[Path],
    active_project: Optional[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    ignored_task_ids: Optional[List[str]] = None,
    chapter_goal_resolver: Optional[Callable[[str], Optional[str]]] = None,
) -> Dict[str, Any]:
    """Perform comprehensive diagnostic check of the novel generation system."""
    issues: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []
    ignored_ids = set(ignored_task_ids or [])

    if not active_project or not active_project.get("id"):
        issues.append({
            "code": "NO_ACTIVE_PROJECT",
            "level": "error",
            "message": "当前未选择或创建任何小说项目。",
        })
        suggestions.append({
            "label": "创建/选择项目",
            "type": "navigate",
            "payload": {"route": "/"},
        })
        return {
            "status": "error",
            "issues": issues,
            "suggestions": suggestions,
        }

    root = root_dir
    if not root:
        return {
            "status": "ok",
            "issues": [],
            "suggestions": [],
        }

    # 1. Check Batch Pause
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
                "label": "去生产中心审校修复",
                "type": "navigate",
                "payload": {"route": "/production?tab=reviews"},
            })
    except Exception:
        pass

    # 2. Check LLM Configuration
    try:
        from novel_agent.pipeline import load_pipeline_settings
        config_data = load_pipeline_settings(root)
        llm_settings = config_data.get("llm", {})

        from web.model_library import ModelLibrary
        lib = ModelLibrary(root)
        models_library = lib._load().get("models", {})

        default_model_id = llm_settings.get("daily_model_id") or llm_settings.get("default_model_id")

        def _should_use_library_default(settings_dict: Dict[str, Any]) -> bool:
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
                "payload": {"route": "/config"},
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
                "payload": {"route": "/config"},
            })
    except Exception as e:
        issues.append({
            "code": "CONFIG_LOAD_FAILED",
            "level": "error",
            "message": f"加载项目配置文件失败：{str(e)}",
        })

    # 3. Check Tasks Status
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
            goal = latest.get("goal")
            if not goal and chapter_goal_resolver:
                try:
                    goal = chapter_goal_resolver(str(ch_id))
                except Exception:
                    goal = None
            goal = goal or f"重新生成第 {ch_id} 章内容"
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
                "payload": {"chapter_id": ch_id, "goal": goal},
            })
            suggestions.append({
                "label": "查看详细日志",
                "type": "navigate",
                "payload": {"route": "/logs"},
            })

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


def generate_offline_heuristic_reply(
    message: str,
    root_dir: Optional[Path],
    context_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Provide intelligent editorial responses locally when LLM is unconfigured or offline."""
    msg = message.strip().lower()
    
    # Check if asking about failed chapters / gate / review
    if any(kw in msg for kw in ["为什么没过", "门禁", "未通过", "失败", "报错", "卡住", "过审"]):
        failed_tasks = context_data.get("failed_tasks") or []
        pending = context_data.get("pipeline_pending") or {}
        gate_blocked = pending.get("gate_blocked") or []
        
        if failed_tasks or gate_blocked:
            target_ch = ""
            err_msg = ""
            if failed_tasks:
                target_ch = str(failed_tasks[0].get("chapter_id") or "")
                err_msg = str(failed_tasks[0].get("error") or "")
                gate_sum = failed_tasks[0].get("gate_summary") or ""
                if gate_sum:
                    err_msg += f"（{gate_sum}）"
            elif gate_blocked:
                target_ch = str(gate_blocked[0].get("chapter_id") or "")
                err_msg = f"阶段 [{gate_blocked[0].get('last_stage')}] 需改稿或重试审校"

            display_ch = target_ch.lstrip("0") or target_ch
            reply = (
                f"嗯，我帮你瞅了一眼：最近第 {display_ch} 章确实遇到了卡点。\n\n"
                f"- **卡点原因**：{err_msg or '触发了统一门禁质量阻断或执行异常'}\n"
                "- **建议处理步骤**：\n"
                f"  1. 点击下方按钮去「正文页」修改带有 AI 味或篇幅异常的段落；\n"
                f"  2. 改完后在生产中心或章节页点击「重跑门禁」；\n"
                f"  3. 门禁绿灯后在生产中心点击「继续生产」。"
            )

            return {
                "reply": reply,
                "actions": [
                    {"label": f"去修改第 {target_ch} 章正文", "type": "navigate", "payload": {"route": f"/writer?chapter={target_ch}"}},
                    {"label": "去生产中心审校队列", "type": "navigate", "payload": {"route": "/production?tab=reviews"}},
                    {"label": "提交自动修复", "type": "auto_repair_chapter", "payload": {"chapter_id": target_ch}},
                ],
                "suggestions": [
                    f"查看第 {target_ch} 章门禁详情",
                    "全书暂停了，怎么续跑？",
                    "日常档和逻辑档怎么选？",
                ],
            }

    # Check if asking about batch pause / continuation
    if any(kw in msg for kw in ["全书暂停", "续跑", "继续", "暂停了", "重启全书"]):
        batch = context_data.get("novel_batch") or {}
        if batch.get("paused"):
            reason = batch.get("pause_reason") or "circuit_breaker"
            reply = (
                f"全书批量目前处于**暂停保护状态**（原因：{reason}）。\n\n"
                "为了保证全书质量不滑坡，熔断机制在遇到连续异常或质量门禁阻断时会自动停下。\n\n"
                "**处理方法**：\n"
                "1. 先去「生产中心 → 审校修复」把待修章节解决；\n"
                "2. 确认无误后，在生产中心右上角点击「确认续跑」。\n\n"
                "*(注：出于安全考虑，山山不在对话里擅自重启全书批量哦。)*"
            )
            return {
                "reply": reply,
                "actions": [
                    {"label": "去生产中心处理并续跑", "type": "navigate", "payload": {"route": "/production?tab=reviews"}},
                    {"label": "查看详细日志", "type": "navigate", "payload": {"route": "/logs"}},
                ],
                "suggestions": ["当前作品还有哪些待处理？", "这章为什么没过审？"],
            }

    # Check if asking about models / config
    if any(kw in msg for kw in ["日常档", "逻辑档", "模型", "配置", "api", "key"]):
        reply = (
            "关于模型配置，山山的建议是：\n\n"
            "- **日常档 (daily_model_id)**：负责绝大部分正文生成与大批量写作，建议选用高性价比、响应快的模型；\n"
            "- **逻辑档 (reasoning_model_id)**：用于大纲推演、复杂伏笔解构与深度质量审校，建议选用推理能力较强的模型；\n"
            "- **山山助手**：可以在「设置 → 模型」里单独为我指定一个小模型，留空则默认继承日常档。"
        )
        return {
            "reply": reply,
            "actions": [
                {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}},
                {"label": "测试当前模型连通性", "type": "test_model", "payload": {}},
            ],
            "suggestions": ["这章为什么没过审？", "当前作品还有哪些待处理？"],
        }

    # Check if asking about characters / story
    if any(kw in msg for kw in ["主角", "角色", "人设", "登场", "人物"]):
        try:
            from novel_agent.services.assistant_knowledge import get_character_snapshots
            chars = get_character_snapshots(root_dir, limit=4)
            if chars:
                char_descs = [f"- **{c['name']}** ({c['role']})：{c['motivation'] or '目标待定'}" for c in chars]
                chars_text = "\n".join(char_descs)
                reply = f"目前本作登记的主要角色档案如下：\n\n{chars_text}\n\n需要调整人设可以在设定卡中修改，写正文时我会帮作者盯着人设一致性。"
                return {
                    "reply": reply,
                    "actions": [{"label": "去正文写作页", "type": "navigate", "payload": {"route": "/workspace"}}],
                    "suggestions": ["下一章剧情看点是什么？", "这章为什么没过审？"],
                }
        except Exception:
            pass

    # Generic fallback
    from novel_agent.persona.shanshan import SHANSHAN_REPLY_NO_LLM
    return {
        "reply": SHANSHAN_REPLY_NO_LLM,
        "actions": [
            {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}},
            {"label": "测试当前模型", "type": "test_model", "payload": {}},
        ],
        "suggestions": [
            "这章为什么没过审？",
            "全书暂停了，怎么续跑？",
            "日常档和逻辑档怎么选？",
            "当前作品还有哪些待处理？",
        ],
    }
