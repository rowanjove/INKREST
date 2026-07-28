from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import web.context as ws_server
from web.llm_errors import model_provider_http_error
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

router = APIRouter()


# ---- Request & Response Models ----

class InlineRewriteRequest(BaseModel):
    text: str = Field(..., min_length=1)
    instruction: str = Field(..., min_length=1)
    chapter_id: Optional[str] = None
    goal: Optional[str] = None


class InlineRewriteResponse(BaseModel):
    rewritten_text: str


class InlineExpandRequest(BaseModel):
    before_text: str = Field(..., min_length=1)
    chapter_id: Optional[str] = None
    goal: Optional[str] = None


class InlineExpandResponse(BaseModel):
    expanded_text: str


# ---- API Endpoints ----

@router.post("/api/assistant/inline-rewrite", response_model=InlineRewriteResponse)
async def inline_rewrite(
    req: InlineRewriteRequest,
    session: ProjectSession = RequireProjectDep,
) -> InlineRewriteResponse:
    """Rewrite a selected text block based on user instructions."""
    import web.routes.assistant as assistant_module
    session = coerce_project_session(session)
    llm = assistant_module._get_assistant_llm(session.root_dir)
    if not llm:
        raise HTTPException(503, "Assistant LLM not configured")

    prompt = f"""你是一名极其专业的小说润色与编辑专家。你的任务是根据用户的指令对指定的小说片段进行重写或润色。

【小说当前背景】
章节号: {req.chapter_id or '未知'}
写作目标: {req.goal or '未设定'}

【修改指令】
{req.instruction}

【需要重写的原文本】
{req.text}

【写作要求】
1. 完全遵循用户的修改指令（如润色、精简、改变语气、细节扩写等）。
2. 保持与前后的章节语境一致，人设与世界观设定不要出现偏差。
3. 仅输出重写后的最终文本段落，严禁包含任何旁白、前言、多余的说明或 markdown 标记。"""

    try:
        response = await llm.agenerate(role="写作编辑助手", prompt=prompt)
        clean_text = response.strip()
        if clean_text and clean_text.startswith("```") and clean_text.endswith("```"):
            lines = (clean_text or "").splitlines()
            if len(lines) > 2:
                clean_text = "\n".join(lines[1:-1]).strip()
        return InlineRewriteResponse(rewritten_text=clean_text)
    except Exception as e:
        ws_server.logger.error("LLM generation failed in inline-rewrite: %s", e)
        raise model_provider_http_error("AI 改写", e)


@router.post("/api/assistant/inline-expand", response_model=InlineExpandResponse)
async def inline_expand(
    req: InlineExpandRequest,
    session: ProjectSession = RequireProjectDep,
) -> InlineExpandResponse:
    """Expand or continue writing from the current cursor context."""
    import web.routes.assistant as assistant_module
    session = coerce_project_session(session)
    llm = assistant_module._get_assistant_llm(session.root_dir)
    if not llm:
        raise HTTPException(503, "Assistant LLM not configured")

    context_text = req.before_text[-1500:] if len(req.before_text) > 1500 else req.before_text

    prompt = f"""你是一名优秀的网络文学作家。请根据光标前的历史上下文和当前章节的写作目标，在光标位置继续向下进行合理且生动的扩写/续写。

【小说当前背景】
章节号: {req.chapter_id or '未知'}
当前章节写作目标: {req.goal or '未设定'}

【光标前的历史文本 (历史上下文)】
{context_text}

【写作要求】
1. 紧密承接上文的语境、叙事节奏和情感色调。
2. 围绕写作目标展开，合理推进情节发展，进行适当的动作、神态、环境或心理描写。
3. 续写字数控制在 100 到 300 字之间。
4. 仅输出接续写下来的文本内容，不要重复上文，严禁包含任何旁白、前言、多余的说明或 markdown 标记。"""

    try:
        response = await llm.agenerate(role="续写助手", prompt=prompt)
        clean_text = response.strip()
        if clean_text and clean_text.startswith("```") and clean_text.endswith("```"):
            lines = (clean_text or "").splitlines()
            if len(lines) > 2:
                clean_text = "\n".join(lines[1:-1]).strip()
        return InlineExpandResponse(expanded_text=clean_text)
    except Exception as e:
        ws_server.logger.error("LLM generation failed in inline-expand: %s", e)
        raise model_provider_http_error("AI 扩写", e)
