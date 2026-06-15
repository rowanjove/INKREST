import json
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

import web.context as ws_server
from novel_agent.persona.shanshan import (
    SHANSHAN_CHAT_PERSONA,
    SHANSHAN_REPLY_LLM_ERROR,
    SHANSHAN_REPLY_NO_LLM,
)

router = APIRouter()


# ---- Request & Response Models ----

class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class AssistantChatResponse(BaseModel):
    reply: str
    actions: List[Dict[str, Any]] = []


# ---- Software Handbook & Troubleshooting Guide ----

HANDBOOK = """
### 栖墨 INKREST 使用手册与排障（山山版）

1. **新建与体量**
   - 书库 →「新建作品」：快速创建 / AI 引导 / 粘贴解析 三选一。
   - AI 引导默认完整步骤以锁定主题；可选「精简建档」跳过深度规划 7–10 步。
   - 体量档位：微型～无限连载；超长篇/无限连载只定卷级骨架，细章由工作台按「本轮章数」滚动生成，续跑在**章节维护**。

2. **日常写作路径**
   - **大纲**：生成或确认卷纲、体量（macro_outline）。
   - **工作台**：按本轮章数自动续跑；暂停后到**章节维护**续跑全书批量。
   - **章节列表 / 章节详情**：阅读正文、看重试；**统一门禁报告**在章节详情页（unified_gate）。
   - **套路工坊**：组装套路后跳转新建页预填，不重复弹窗创建。

3. **任务失败与重试**
   - **429 / 限流**：降并发、换 Key、稍后重试。
   - **超时 / 504**：检查代理与 base_url。
   - **单章失败**：诊断或对话可「重试该章」（清 checkpoint）；若提示统一门禁未过，引导用户打开 `/chapters/{章号}` 看门禁明细后再改稿或重试。
   - **全书批量暂停（熔断）**：只在**章节维护**续跑，勿在对话里擅自重启全书。

4. **模型配置**
   - **设置 → 模型**：日常档（daily_model_id）驱动大部分生成；可为 `llm.assistant` 单独配山山对话模型。
   - Static 占位无法真实生成；写作档/逻辑档在模型路由中分角色绑定。

5. **山山能力边界**
   - 可：解释状态、指路页面、测模型、重试单章。
   - 不可：改大纲、删项目、代写正文、在对话中直接续跑全书批量。
"""


# ---- API Endpoints ----

@router.post("/api/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(req: AssistantChatRequest) -> AssistantChatResponse:
    """AI Assistant Chat Endpoint for pet assistant."""
    import web.routes.assistant as assistant_module
    llm = assistant_module._get_assistant_llm()
    
    if not llm:
        return AssistantChatResponse(
            reply=SHANSHAN_REPLY_NO_LLM,
            actions=[
                {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}},
                {"label": "测试当前模型", "type": "test_model", "payload": {}}
            ]
        )
        
    from web.deps import coerce_project_session
    from web.routes.assistant import build_assistant_context

    context_data = await build_assistant_context(coerce_project_session(None))
    
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
            from datetime import datetime
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
            " — 续跑请到章节维护操作，不要在此直接重启全书."
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

    system_context = f"""
【小说生成系统当前状态】
- 当前活跃项目: {proj_name}
- 作品概况: {work_str}
- AI 工厂控制台: {factory_str}
- 工厂建议动作:
{factory_commands_str}
- 全书批量: {batch_str}
- 待处理章节（章节维护同源）:
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

{system_context}

【软件使用手册与常见错误指南】
{HANDBOOK}

【对话历史记录】
{history_str}

【当前用户输入】
用户: {req.message}

【任务要求】
1. 按上文人设回复，支持 Markdown 排版。
2. 结合 system 状态；有失败任务或配置问题时点明原因并给出可执行建议。
3. 如果用户的提问或当前问题可以通过特定快捷操作解决，请在回答的最后新起一行，输出动作指令：
格式如下：
===ACTIONS===
[
  {{"type": "navigate", "label": "查看详细日志", "payload": {{"route": "/logs"}}}}
]

可用的 ACTION 类型说明：
- navigate: 路由跳转。参数 {{"route": "路径"}}。常用：
  '/' 书库，'/create' 新建，'/outline' 大纲，'/workspace' 工作台，
  '/config' 设置，'/chapters/maintenance' 章节维护（续跑/待处理），'/logs' 日志中心，
  '/chapters/{{章号}}' 章节详情（统一门禁报告在此，章号如 001、012）
- test_model: 测试当前模型连通性。不需要参数。
- retry_task: 重新运行任务。参数包含 {{"chapter_id": "章节号", "goal": "章节目标"}}
- auto_repair_chapter: 提交章节自动修复（降 AI 味/质量阻断）。参数 {{"chapter_id": "章节号"}}
- rerun_gate: 只重跑门禁（用户已改稿后）。参数 {{"chapter_id": "章节号"}}
- factory_intent: 执行工厂控制台建议动作。参数 {{"intent": "create|plan|run|monitor|repair|export"}}
- 若失败任务有 gate_summary 且与门禁相关，优先建议 navigate 到该章详情，再视情况 auto_repair_chapter 或 rerun_gate。
- 工厂状态为 blocked 时，优先解释 operator_brief，并给出 factory_intent repair 或 auto_repair_chapter。
- 用户问「继续写」「为什么停了」「导出」时，优先使用 factory_intent 与上方「工厂建议动作」列表对齐。
"""
    
    try:
        llm_response = await llm.agenerate(role="山山助手", prompt=system_prompt)
        parsed = assistant_module._parse_chat_response(llm_response)
        return AssistantChatResponse(
            reply=parsed.get("reply", ""),
            actions=parsed.get("actions", [])
        )
    except Exception as e:
        ws_server.logger.error("LLM generation failed in assistant chat: %s", e)
        return AssistantChatResponse(
            reply=SHANSHAN_REPLY_LLM_ERROR.format(detail=str(e)),
            actions=[
                {"label": "测试模型连通性", "type": "test_model", "payload": {}},
                {"label": "去模型配置页", "type": "navigate", "payload": {"route": "/config"}}
            ]
        )
