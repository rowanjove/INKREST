import asyncio
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import web.context as ws_server
from web.deps import ProjectSession, get_project_session
from novel_agent.persona.shanshan import (
    SHANSHAN_CHAT_PERSONA,
    SHANSHAN_REPLY_LLM_ERROR,
    SHANSHAN_REPLY_NO_LLM,
)
from novel_agent.services.assistant_knowledge import format_story_context_for_shanshan
from novel_agent.services.assistant_diagnostics import generate_offline_heuristic_reply

from novel_agent.assistant.models import (
    ActiveEditorContext,
    AssistantPatch,
    PatchStatus,
    SourceType,
)
from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.context.resolver import StoryContextResolver, ResolvedContextBundle
from novel_agent.assistant.skills.registry import get_skill_registry, SkillDefinition
from novel_agent.assistant.patch.service import PatchService

router = APIRouter()


# ---- Request & Response Models ----

class AssistantChatRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None
    editor_context: Optional[ActiveEditorContext] = None
    skill_id: Optional[str] = None
    thread_id: Optional[str] = None


class AssistantChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    reply: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    chips: List[Dict[str, str]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    patch: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    thread_id: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)




class PatchActionRequest(BaseModel):
    patch_id: str


# ---- Software Handbook & Troubleshooting Guide ----

HANDBOOK = """
### 栖墨 INKREST 使用手册与排障（山山版）

1. **新建与体量**
   - 书库 →「新建作品」：快速创建 / AI 引导 / 粘贴解析 三选一。
   - AI 引导默认完整步骤以锁定主题；可选「精简建档」跳过深度规划 7–10 步。
   - 体量档位：微型～无限连载；超长篇/无限连载只定卷级骨架，细章按「本轮章数」滚动生成，续跑在**生产中心**。

2. **日常写作路径**
   - **大纲**：生成或确认卷纲、体量（macro_outline）。
   - **生产中心**：查看运行、审校修复、费用与日志；暂停后在此处理问题并确认续跑。
   - **章节列表 / 章节详情**：阅读正文、看重试；**统一门禁报告**在章节详情页（unified_gate）。
   - **套路工坊**：组装套路后跳转新建页预填，不重复弹窗创建。

3. **任务失败与重试**
   - **429 / 限流**：降并发、换 Key、稍后重试。
   - **超时 / 504**：检查代理与 base_url。
   - **单章失败**：诊断或对话可「重试该章」（清 checkpoint）；若提示统一门禁未过，引导用户打开 `/chapters/{章号}` 看门禁明细后再改稿或重试。
   - **全书批量暂停（熔断）**：只在**生产中心**确认续跑，勿在对话里擅自重启全书。

4. **模型配置**
   - **设置 → 模型**：日常档（daily_model_id）驱动大部分生成；可为 `llm.assistant` 单独配山山对话模型。
   - Static 占位无法真实生成；写作档/逻辑档在模型路由中分角色绑定。

5. **山山能力边界**
   - 可：解释状态、指路页面、测模型、重试单章、分析作品角色与大纲、提供门禁修改建议。
   - 写作时：提供正文续写、润色、扩写、对白调优等修改提议（以可撤销 Patch 呈现），不可强制静默改写。
   - 不可：擅自删项目、在对话中直接续跑全书批量。
"""


def _resolve_skill(req: AssistantChatRequest) -> Optional[SkillDefinition]:
    registry = get_skill_registry()
    if req.skill_id:
        s = registry.get(req.skill_id)
        if s:
            return s
    found = registry.find_by_command(req.message)
    if found:
        return found
    from novel_agent.assistant.router import IntentRouter
    detected = IntentRouter.detect_skill(req.message, req.editor_context)
    if detected:
        return registry.get(detected)
    return None



def _build_shanshan_prompt(
    session: ProjectSession,
    req: AssistantChatRequest,
    context_data: Dict[str, Any],
    resolved_bundle: Optional[ResolvedContextBundle] = None,
    active_skill: Optional[SkillDefinition] = None,
) -> str:
    """Build a comprehensive context-aware prompt for ShanShan."""
    active_proj = context_data.get("active_project")
    proj_name = active_proj.get("name") if active_proj else "未选择项目"
    running_tasks = context_data.get("running_tasks", [])
    failed_tasks = context_data.get("failed_tasks", [])

    running_str = ", ".join([f"任务{t['id']}(第{t.get('chapter_id')}章)" for t in running_tasks]) or "无"

    work = context_data.get("work") or {}
    try:
        from novel_agent.services.assistant_snapshot import format_work_snapshot_line
        work_str = format_work_snapshot_line(work)
    except Exception:
        work_str = "未加载作品概况"

    factory = context_data.get("factory") or {}
    try:
        from novel_agent.services.assistant_snapshot import format_factory_brief
        factory_str = format_factory_brief(factory) if factory else "工厂状态未加载"
    except Exception:
        factory_str = "工厂状态未加载"
    factory_commands = factory.get("commands") if isinstance(factory.get("commands"), list) else []
    factory_command_lines = [
        f"- {item.get('label')}: {item.get('reason')}"
        for item in factory_commands[:4]
        if isinstance(item, dict)
    ]
    factory_commands_str = "\n".join(factory_command_lines) if factory_command_lines else "无"

    failed_lines = []
    for t in failed_tasks:
        line = f"- 章节 {t.get('chapter_id')}: 错误 [{t.get('error')}]"
        if t.get("gate_summary"):
            line += f" | {t['gate_summary']}"
        failed_lines.append(line)
    failed_str = "\n".join(failed_lines) if failed_lines else "无"

    runtime_lines = []
    for row in (context_data.get("agent_runtime_logs") or [])[-20:]:
        ts = row.get("timestamp")
        ts_label = ""
        if isinstance(ts, (int, float)):
            ts_label = datetime.fromtimestamp(ts if ts < 1e12 else ts / 1000).strftime("%H:%M:%S")
        runtime_lines.append(
            f"- [{ts_label}] {row.get('level', 'info')} {row.get('step') or ''} {row.get('message', '')}".strip()
        )
    runtime_str = "\n".join(runtime_lines) if runtime_lines else "无（尚无流水线输出）"

    sys_tail = context_data.get("system_log_tail") or []
    sys_tail_str = "\n".join(f"- {ln[:220]}" for ln in sys_tail[-15:]) if sys_tail else "无"
    log_paths = context_data.get("system_log_paths") or {}
    log_path_str = log_paths.get("project") or log_paths.get("workspace") or "未找到日志文件"

    batch = context_data.get("novel_batch") or {}
    if batch.get("paused"):
        batch_str = (
            f"已暂停（原因: {batch.get('pause_reason') or 'circuit_breaker'}，"
            f"卷 {batch.get('last_arc_id') or '—'} / 章 {batch.get('last_chapter_id') or '—'}）"
            " — 续跑请到生产中心操作，不要在此直接重启全书."
        )
    else:
        batch_str = "未暂停"

    pending = context_data.get("pipeline_pending") or {}
    pending_lines = []
    for row in (pending.get("retries") or [])[:5]:
        pending_lines.append(
            f"- 第 {row.get('chapter_id')} 章 [批量跳过·待重试] {row.get('message') or row.get('reason') or ''}"
        )
    for row in (pending.get("gate_blocked") or [])[:5]:
        pending_lines.append(
            f"- 第 {row.get('chapter_id')} 章 [{row.get('last_stage')}] 需改稿或重试审校"
        )
    repair_hint = ""
    if pending.get("gate_blocked"):
        first = pending["gate_blocked"][0]
        from novel_agent.services.assistant_snapshot import format_repair_steps_hint
        repair_hint = format_repair_steps_hint(
            str(first.get("chapter_id") or ""),
            str(first.get("last_stage") or ""),
        )
    pending_str = (
        f"共 {pending.get('pending_total', 0)} 项"
        f"（门禁阻断 {pending.get('pending_gate_count', 0)}，批量跳过 {pending.get('pending_retry_count', 0)}）\n"
        + ("\n".join(pending_lines) if pending_lines else "无")
        + (f"\n排障建议: {repair_hint}" if repair_hint else "")
    )

    resolved_block = resolved_bundle.formatted_prompt_block if resolved_bundle else ""

    skill_instruction = ""
    if active_skill:
        skill_instruction = f"""
【当前激活技能：{active_skill.name} ({active_skill.command})】
{active_skill.system_instruction}
"""

    patch_instruction = ""
    if (active_skill and active_skill.produces_patch) or (req.editor_context and req.editor_context.selected_text):
        patch_instruction = """
【正文修改 Patch 指令要求】
如果你为用户提出了针对文段的具体改写、润色、扩写或续写内容，请务必在回答末尾以结构化 Patch 格式输出修改方案，格式如下：
===PATCH===
{
  "proposed_text": "此处填写完整的替换文本或接续文本",
  "reason": "一句话简述修改理由（例如：强化人物隐忍情绪，删除两次重复动词）"
}
"""

    system_context = f"""
{resolved_block}

【小说生成系统当前状态】
- 当前活跃项目: {proj_name}
- 作品概况: {work_str}
- AI 工厂控制台: {factory_str}
- 工厂建议动作:
{factory_commands_str}
- 全书批量: {batch_str}
- 待处理章节（生产中心审校队列同源）:
{pending_str}
- 运行中的任务: {running_str}
- 最近失败的任务:
{failed_str}
- 最近 Agent 实时日志（日志中心同源，节选）:
{runtime_str}
- 底层服务日志文件（{log_path_str}，节选）:
{sys_tail_str}
"""

    history_lines = []
    for turn in req.history[-5:]:
        role = "用户" if turn.get("role") == "user" else "山山"
        history_lines.append(f"{role}: {turn.get('content')}")
    history_str = "\n".join(history_lines) if history_lines else "无"

    system_prompt = f"""{SHANSHAN_CHAT_PERSONA}

{skill_instruction}

{system_context}

【软件使用手册与常见错误指南】
{HANDBOOK}

【对话历史记录】
{history_str}

【当前用户输入】
用户: {req.message}

【任务要求】
1. 按上文人设回复，支持 Markdown 排版。
2. 结合 system 状态与作品设定档案；有失败任务、门禁卡点或配置问题时点明原因并给出可执行建议。
3. 回答中如涉及作品设定事实，请明确指出依据出处。
{patch_instruction}
4. 如果用户的提问或当前问题可以通过特定快捷操作解决，请在回答的最后新起一行，输出动作指令：
格式如下：
===ACTIONS===
[
  {{"type": "navigate", "label": "查看详细日志", "payload": {{"route": "/logs"}}}}
]

可用的 ACTION 类型说明：
- navigate: 路由跳转。参数 {{"route": "路径"}}。常用：
  '/' 书库，'/create' 新建，'/outline' 大纲，'/workspace' 工作台，
  '/config' 设置，'/production?tab=reviews' 审校修复，'/production?tab=logs' 日志，
  '/writer?chapter={{章号}}' 正文编辑（章号如 001、012）
- test_model: 测试当前模型连通性。不需要参数。
- retry_task: 重新运行任务。参数包含 {{"chapter_id": "章节号", "goal": "章节目标"}}
- auto_repair_chapter: 提交章节自动修复（降 AI 味/质量阻断）。参数 {{"chapter_id": "章节号"}}
- rerun_gate: 只重跑门禁（用户已改稿后）。参数 {{"chapter_id": "章节号"}}
- factory_intent: 执行工厂控制台建议动作。参数 {{"intent": "create|plan|run|monitor|repair|export"}}
- inspect_gate_detail: 获取章节详细门禁诊断。参数 {{"chapter_id": "章节号"}}

5. 在回答的最末尾（若有动作指令，则在动作指令之后），可以输出 2~3 个适合用户下一步提问的简短追问建议（每个不超过15字）：
格式如下：
===SUGGESTIONS===
["查看第 1 章门禁详情", "下一章看点建议", "全书暂停了怎么续跑"]
"""
    return system_prompt


def _parse_patch_from_text(text: str) -> tuple[str, Optional[Dict[str, Any]]]:
    """Extract ===PATCH=== JSON block from text."""
    if "===PATCH===" not in text:
        return text, None
    parts = text.split("===PATCH===", 1)
    reply = parts[0].strip()
    patch_str = parts[1].strip()

    # If there are subsequent markers like ===ACTIONS=== or ===SUGGESTIONS===, cut before them
    next_marker = re.search(r'===(?:ACTIONS|SUGGESTIONS)===', patch_str)
    subsequent = ""
    if next_marker:
        subsequent = patch_str[next_marker.start():]
        patch_str = patch_str[:next_marker.start()].strip()

    patch_data = None
    try:
        json_match = re.search(r'\{.*\}', patch_str, re.DOTALL)
        if json_match:
            patch_data = json.loads(json_match.group(0))
        else:
            patch_data = json.loads(patch_str)
    except Exception as e:
        ws_server.logger.warning("Failed to parse patch json: %s", e)

    full_reply = (reply + "\n\n" + subsequent).strip() if subsequent else reply
    return full_reply, patch_data


class PreferenceCreateRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    content: str = Field(..., min_length=1)
    preference_type: str = "style"
    scope: str = "global"


# ---- API Endpoints ----

@router.get("/api/assistant/preferences")
async def list_assistant_preferences(
    session: ProjectSession = Depends(get_project_session),
):
    """Returns global and project-level author preferences."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    project_id = session.project_id if session.has_project else None
    prefs = store.list_preferences(project_id)
    return {"preferences": [p.model_dump() for p in prefs]}


@router.post("/api/assistant/preferences")
async def create_assistant_preference(
    req: PreferenceCreateRequest,
    session: ProjectSession = Depends(get_project_session),
):
    """Creates a new author writing preference."""
    import uuid
    from novel_agent.assistant.memory.store import AssistantStore
    from novel_agent.assistant.models import AuthorPreference
    store = AssistantStore(session.root_dir if session.has_project else None)
    pref = AuthorPreference(
        id=f"pref_{uuid.uuid4().hex[:8]}",
        scope=req.scope,
        project_id=session.project_id if req.scope == "project" else None,
        preference_type=req.preference_type,
        content=req.content,
    )
    saved = store.save_preference(pref)
    return {"success": True, "preference": saved.model_dump()}


@router.delete("/api/assistant/preferences/{pref_id}")
async def delete_assistant_preference(
    pref_id: str,
    session: ProjectSession = Depends(get_project_session),
):
    """Deletes an author preference."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    deleted = store.delete_preference(pref_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"success": True, "deleted_id": pref_id}


@router.post("/api/assistant/context/preview")
async def preview_assistant_context(
    req: AssistantChatRequest,
    session: ProjectSession = Depends(get_project_session),
):
    """Inspects context bundle composition and token budget without triggering LLM."""
    adapter = StoryAdapter(session.root_dir if session.has_project else None)
    resolver = StoryContextResolver(adapter)
    active_skill = _resolve_skill(req)
    resolved_bundle = resolver.resolve(
        req.message, req.editor_context, active_skill.id if active_skill else None
    )
    return {
        "chips": resolved_bundle.chips,
        "citations": [c.model_dump() for c in resolved_bundle.citations],
        "budget_breakdown": resolved_bundle.budget_breakdown,
        "total_chars": resolved_bundle.total_chars,
        "preview_text": resolved_bundle.formatted_prompt_block[:1500],
    }


@router.get("/api/assistant/skills")
async def list_assistant_skills():
    """Returns all registered skills for ShanShan Assistant."""
    registry = get_skill_registry()
    return {"skills": [s.model_dump() for s in registry.list_skills()]}


@router.get("/api/assistant/patches")
async def list_assistant_patches(
    chapter_id: Optional[str] = None,
    session: ProjectSession = Depends(get_project_session),
):
    """Lists recent patches for the active project."""
    service = PatchService(session.root_dir if session.has_project else None)
    project_id = session.project_id if session.has_project else None
    patches = service.list_patches(project_id=project_id, chapter_id=chapter_id)
    return {"patches": [p.model_dump() for p in patches]}


@router.post("/api/assistant/patches/{patch_id}/apply")
async def apply_assistant_patch(
    patch_id: str,
    session: ProjectSession = Depends(get_project_session),
):
    """Applies a proposed patch to chapter manuscript."""
    service = PatchService(session.root_dir if session.has_project else None)
    res = service.apply_patch(patch_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to apply patch"))
    patch = res.get("patch")
    return {
        "success": True,
        "patch": patch.model_dump() if patch else None,
        "new_text": res.get("new_text"),
    }


@router.post("/api/assistant/patches/{patch_id}/reject")
async def reject_assistant_patch(
    patch_id: str,
    session: ProjectSession = Depends(get_project_session),
):
    """Rejects a proposed patch."""
    service = PatchService(session.root_dir if session.has_project else None)
    updated = service.reject_patch(patch_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Patch not found")
    return {"success": True, "patch": updated.model_dump()}


@router.post("/api/assistant/patches/{patch_id}/revert")
async def revert_assistant_patch(
    patch_id: str,
    session: ProjectSession = Depends(get_project_session),
):
    """Reverts an accepted patch."""
    service = PatchService(session.root_dir if session.has_project else None)
    res = service.revert_patch(patch_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to revert patch"))
    patch = res.get("patch")
    return {
        "success": True,
        "patch": patch.model_dump() if patch else None,
        "reverted_text": res.get("reverted_text"),
    }


@router.get("/api/assistant/tools")
async def list_assistant_tools():
    """Lists registered tools for ShanShan Assistant."""
    from novel_agent.assistant.tools.builtin_tools import register_builtin_tools
    reg = register_builtin_tools()
    defs = reg.list_definitions()
    return {
        "tools": [
            {
                "name": d.name,
                "description": d.description,
                "permission_level": d.permission_level.value,
                "requires_confirmation": d.requires_confirmation,
                "parameters_schema": d.parameters_schema,
            }
            for d in defs
        ]
    }


@router.get("/api/assistant/runs")
async def list_assistant_runs(
    limit: int = 50,
    session: ProjectSession = Depends(get_project_session),
):
    """Lists recent runs trace for the project."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    project_id = session.project_id if session.has_project else None
    runs = store.list_runs(project_id=project_id, limit=limit)
    return {"runs": [r.model_dump() for r in runs]}


@router.get("/api/assistant/runs/{run_id}")
async def get_assistant_run(
    run_id: str,
    session: ProjectSession = Depends(get_project_session),
):
    """Gets details and steps trace of a specific agent run."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run.model_dump()}


class ActionConfirmRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    action: Dict[str, Any]


@router.post("/api/assistant/runs/{run_id}/confirm")
async def confirm_assistant_run_action(
    run_id: str,
    req: ActionConfirmRequest,
    session: ProjectSession = Depends(get_project_session),
):
    """Confirms and executes a pending action that required explicit confirmation."""
    from novel_agent.assistant.kernel import ShanShanKernel
    kernel = ShanShanKernel(root_dir=session.root_dir if session.has_project else None)
    result = await kernel.run(
        user_message="确认执行操作",
        user_confirmed=True,
        confirmed_action=req.action,
        confirm_run_id=run_id,
        project_id=session.project_id if session.has_project else None,
    )
    return result.model_dump()


class CreateThreadRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    title: str = "新对话"


@router.get("/api/assistant/threads")
async def list_assistant_threads(
    limit: int = 50,
    session: ProjectSession = Depends(get_project_session),
):
    """Lists recent conversation threads."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    project_id = session.project_id if session.has_project else None
    threads = store.list_threads(project_id=project_id, limit=limit)
    return {"threads": threads}


@router.post("/api/assistant/threads")
async def create_assistant_thread(
    req: Optional[CreateThreadRequest] = None,
    session: ProjectSession = Depends(get_project_session),
):
    """Creates a new assistant chat thread."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    project_id = session.project_id if session.has_project else None
    title = req.title if req and req.title else "新对话"
    thread = store.create_thread(title=title, project_id=project_id)
    return {"thread": thread}


@router.get("/api/assistant/threads/{thread_id}/messages")
async def list_assistant_thread_messages(
    thread_id: str,
    limit: int = 100,
    session: ProjectSession = Depends(get_project_session),
):
    """Lists messages in a conversation thread."""
    from novel_agent.assistant.memory.store import AssistantStore
    store = AssistantStore(session.root_dir if session.has_project else None)
    messages = store.list_messages(thread_id=thread_id, limit=limit)
    return {"messages": messages}


@router.post("/api/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    req: AssistantChatRequest,
    session: ProjectSession = Depends(get_project_session),
) -> AssistantChatResponse:
    """AI Assistant Chat Endpoint for pet assistant."""
    import web.routes.assistant as assistant_module
    from web.routes.assistant import build_assistant_context

    context_data = await build_assistant_context(session)
    llm = assistant_module._get_assistant_llm(session.root_dir)

    adapter = StoryAdapter(session.root_dir if session.has_project else None)
    resolver = StoryContextResolver(adapter)
    active_skill = _resolve_skill(req)
    resolved_bundle = resolver.resolve(req.message, req.editor_context, active_skill.id if active_skill else None)

    from novel_agent.assistant.trace.run_tracker import RunTracker
    from novel_agent.assistant.memory.store import AssistantStore

    store = AssistantStore(session.root_dir if session.has_project else None)
    tracker = RunTracker(store)

    thread_id = req.thread_id
    if not thread_id:
        t = store.create_thread(
            title=req.message[:30],
            project_id=session.project_id if session.has_project else None,
        )
        thread_id = t["id"]

    # Record user message in thread
    store.add_message(
        thread_id=thread_id,
        role="user",
        content=req.message,
        skill_id=active_skill.id if active_skill else None,
    )

    run = tracker.start_run(
        project_id=session.project_id if session.has_project else None,
        thread_id=thread_id,
        skill_id=active_skill.id if active_skill else None,
    )

    if not llm:
        offline = generate_offline_heuristic_reply(
            req.message,
            session.root_dir if session.has_project else None,
            context_data,
        )
        reply_text = offline.get("reply", SHANSHAN_REPLY_NO_LLM)
        tracker.finish_run(run.id, status="completed", output_text=reply_text)
        store.add_message(
            thread_id=thread_id,
            role="assistant",
            content=reply_text,
            skill_id=active_skill.id if active_skill else None,
        )
        return AssistantChatResponse(
            reply=reply_text,
            actions=offline.get("actions", []),
            suggestions=offline.get("suggestions", []),
            chips=resolved_bundle.chips,
            citations=[c.model_dump() for c in resolved_bundle.citations],
            run_id=run.id,
            thread_id=thread_id,
            steps=[],
        )


    system_prompt = _build_shanshan_prompt(
        session, req, context_data, resolved_bundle, active_skill
    )

    try:
        llm_response = await llm.agenerate(role="山山助手", prompt=system_prompt)
        text_no_patch, patch_data = _parse_patch_from_text(llm_response)
        parsed = assistant_module._parse_chat_response(text_no_patch)

        # Handle patch creation if patch data is found or if skill produces patch
        patch_model = None
        if patch_data and isinstance(patch_data, dict):
            proposed_text = patch_data.get("proposed_text") or ""
            reason = patch_data.get("reason") or (active_skill.name if active_skill else "山山提议修改")
            if proposed_text and req.editor_context and req.editor_context.chapter_id:
                patch_service = PatchService(session.root_dir if session.has_project else None)
                patch_model = patch_service.create_patch(
                    project_id=session.project_id or "default",
                    chapter_id=req.editor_context.chapter_id,
                    original_text=req.editor_context.selected_text or "",
                    proposed_text=proposed_text,
                    reason=reason,
                    skill_id=active_skill.id if active_skill else None,
                    source_range=req.editor_context.selection_range,
                )

        final_reply_text = parsed.get("reply", "")
        tracker.finish_run(run.id, status="completed", output_text=final_reply_text)
        store.add_message(
            thread_id=thread_id,
            role="assistant",
            content=final_reply_text,
            skill_id=active_skill.id if active_skill else None,
            patch_id=patch_model.id if patch_model else None,
        )
        return AssistantChatResponse(
            reply=final_reply_text,
            actions=parsed.get("actions", []),
            suggestions=parsed.get("suggestions", []),
            chips=resolved_bundle.chips,
            citations=[c.model_dump() for c in resolved_bundle.citations],
            patch=patch_model.model_dump() if patch_model else None,
            run_id=run.id,
            thread_id=thread_id,
            steps=[s.model_dump() for s in run.steps],
        )
    except Exception as e:
        ws_server.logger.error("LLM generation failed in assistant chat: %s", e)
        offline = generate_offline_heuristic_reply(
            req.message,
            session.root_dir if session.has_project else None,
            context_data,
        )
        reply = offline.get("reply") if offline.get("reply") != SHANSHAN_REPLY_NO_LLM else SHANSHAN_REPLY_LLM_ERROR.format(detail=str(e))
        try:
            tracker.finish_run(run.id, status="failed", output_text=reply)
            store.add_message(
                thread_id=thread_id,
                role="assistant",
                content=reply,
                skill_id=active_skill.id if active_skill else None,
            )
        except Exception:
            pass
        return AssistantChatResponse(
            reply=reply,
            actions=offline.get("actions", [
                {"label": "测试模型连通性", "type": "test_model", "payload": {}},
                {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}}
            ]),
            suggestions=offline.get("suggestions", []),
            chips=resolved_bundle.chips,
            citations=[c.model_dump() for c in resolved_bundle.citations],
            run_id=run.id,
            thread_id=thread_id,
            steps=[s.model_dump() for s in run.steps],
        )



@router.post("/api/assistant/chat/stream")
async def assistant_chat_stream(
    req: AssistantChatRequest,
    session: ProjectSession = Depends(get_project_session),
):
    """Streaming AI Assistant Chat Endpoint for pet assistant (SSE)."""
    import web.routes.assistant as assistant_module
    from web.routes.assistant import build_assistant_context

    context_data = await build_assistant_context(session)
    llm = assistant_module._get_assistant_llm(session.root_dir)

    adapter = StoryAdapter(session.root_dir if session.has_project else None)
    resolver = StoryContextResolver(adapter)
    active_skill = _resolve_skill(req)
    resolved_bundle = resolver.resolve(req.message, req.editor_context, active_skill.id if active_skill else None)

    async def sse_generator() -> AsyncGenerator[str, None]:
        # Send initial context metadata event
        yield f"event: context\ndata: {json.dumps(resolved_bundle.to_dict(), ensure_ascii=False)}\n\n"

        if not llm:
            offline = generate_offline_heuristic_reply(
                req.message,
                session.root_dir if session.has_project else None,
                context_data,
            )
            reply = offline.get("reply", SHANSHAN_REPLY_NO_LLM)
            chunk_size = max(1, len(reply) // 8)
            for i in range(0, len(reply), chunk_size):
                chunk = reply[i : i + chunk_size]
                yield f"event: chunk\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.03)

            done_payload = {
                "reply": reply,
                "actions": offline.get("actions", []),
                "suggestions": offline.get("suggestions", []),
                "chips": resolved_bundle.chips,
                "citations": [c.model_dump() for c in resolved_bundle.citations],
                "patch": None,
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            return

        system_prompt = _build_shanshan_prompt(
            session, req, context_data, resolved_bundle, active_skill
        )
        accumulated = ""
        marker_encountered = False

        try:
            if hasattr(llm, "astream"):
                stream_iter = llm.astream(role="山山助手", prompt=system_prompt)
            else:
                full_resp = await llm.agenerate(role="山山助手", prompt=system_prompt)
                async def _mock_stream():
                    yield full_resp
                stream_iter = _mock_stream()

            buffer = ""
            async for chunk in stream_iter:
                accumulated += chunk
                if not marker_encountered:
                    buffer += chunk
                    match = re.search(r'===(?:PATCH|ACTIONS|SUGGESTIONS)===', buffer)
                    if match:
                        marker_encountered = True
                        pre_text = buffer[:match.start()]
                        if pre_text:
                            yield f"event: chunk\ndata: {json.dumps({'chunk': pre_text}, ensure_ascii=False)}\n\n"
                        buffer = ""
                    else:
                        LOOKAHEAD = 20
                        if len(buffer) > LOOKAHEAD:
                            safe_to_yield = buffer[:-LOOKAHEAD]
                            buffer = buffer[-LOOKAHEAD:]
                            yield f"event: chunk\ndata: {json.dumps({'chunk': safe_to_yield}, ensure_ascii=False)}\n\n"

            if not marker_encountered and buffer:
                match = re.search(r'===(?:PATCH|ACTIONS|SUGGESTIONS)===', buffer)
                if match:
                    pre_text = buffer[:match.start()]
                    if pre_text:
                        yield f"event: chunk\ndata: {json.dumps({'chunk': pre_text}, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: chunk\ndata: {json.dumps({'chunk': buffer}, ensure_ascii=False)}\n\n"

            text_no_patch, patch_data = _parse_patch_from_text(accumulated)
            parsed = assistant_module._parse_chat_response(text_no_patch)

            patch_model = None
            if patch_data and isinstance(patch_data, dict):
                proposed_text = patch_data.get("proposed_text") or ""
                reason = patch_data.get("reason") or (active_skill.name if active_skill else "山山提议修改")
                if proposed_text and req.editor_context and req.editor_context.chapter_id:
                    patch_service = PatchService(session.root_dir if session.has_project else None)
                    patch_model = patch_service.create_patch(
                        project_id=session.project_id or "default",
                        chapter_id=req.editor_context.chapter_id,
                        original_text=req.editor_context.selected_text or "",
                        proposed_text=proposed_text,
                        reason=reason,
                        skill_id=active_skill.id if active_skill else None,
                        source_range=req.editor_context.selection_range,
                    )

            done_payload = {
                "reply": parsed.get("reply", ""),
                "actions": parsed.get("actions", []),
                "suggestions": parsed.get("suggestions", []),
                "chips": resolved_bundle.chips,
                "citations": [c.model_dump() for c in resolved_bundle.citations],
                "patch": patch_model.model_dump() if patch_model else None,
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        except Exception as e:
            ws_server.logger.error("LLM streaming failed in assistant chat: %s", e)
            offline = generate_offline_heuristic_reply(
                req.message,
                session.root_dir if session.has_project else None,
                context_data,
            )
            err_reply = SHANSHAN_REPLY_LLM_ERROR.format(detail=str(e))
            yield f"event: chunk\ndata: {json.dumps({'chunk': err_reply}, ensure_ascii=False)}\n\n"
            done_payload = {
                "reply": err_reply,
                "actions": offline.get("actions", [
                    {"label": "测试模型连通性", "type": "test_model", "payload": {}},
                    {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}}
                ]),
                "suggestions": offline.get("suggestions", []),
                "chips": resolved_bundle.chips,
                "citations": [c.model_dump() for c in resolved_bundle.citations],
                "patch": None,
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
