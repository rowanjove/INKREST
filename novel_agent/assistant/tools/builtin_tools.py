"""Builtin tools for ShanShan Assistant with strict permission level control.

Categorized into:
- Level 0 (Read): get_project_meta, get_current_chapter, get_chapter_outline, get_character, get_world_rules, get_quality_report
- Level 1 (Search): search_story
- Level 3 (Proposal): propose_text_patch
- Level 4 (Ops/Mutation): test_model_connection, retry_chapter, rerun_gate
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.models import EditorRange
from novel_agent.assistant.patch.service import PatchService
from novel_agent.assistant.tools.registry import PermissionLevel, ToolRegistry, get_tool_registry


def register_builtin_tools(
    registry: Optional[ToolRegistry] = None,
    story_adapter: Optional[StoryAdapter] = None,
    patch_service: Optional[PatchService] = None,
    root_dir: Optional[Path] = None,
) -> ToolRegistry:
    """Registers all standard builtin tools into the specified or global ToolRegistry."""
    reg = registry or get_tool_registry()

    def _get_adapter(explicit_project_dir: Optional[str] = None) -> StoryAdapter:
        if explicit_project_dir:
            return StoryAdapter(Path(explicit_project_dir))
        if story_adapter:
            return story_adapter
        return StoryAdapter(root_dir)

    def _get_patch_service(explicit_project_dir: Optional[str] = None) -> PatchService:
        if explicit_project_dir:
            return PatchService(Path(explicit_project_dir))
        if patch_service:
            return patch_service
        return PatchService(root_dir)

    # ================= LEVEL 0: READ TOOLS =================

    async def get_project_meta(project_id: Optional[str] = None) -> Dict[str, Any]:
        """获取当前作品的基础信息，如书名、类型、立意前提及目标章节数。"""
        adapter = _get_adapter()
        return adapter.get_project_meta()

    reg.register(
        name="get_project_meta",
        description="获取当前小说的元数据（书名、类型、题材背景等）",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_project_meta,
        parameters_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID（可选）"}
            },
        },
    )

    async def get_current_chapter(
        chapter_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取指定章节的大纲、字数及正文预览。"""
        adapter = _get_adapter()
        outline = adapter.get_chapter_outline(chapter_id) or {}
        text = adapter.get_chapter_text(chapter_id)
        return {
            "chapter_id": chapter_id,
            "outline": outline,
            "text_length": len(text),
            "text_preview": text[:1000] if text else "",
            "full_text": text,
        }

    reg.register(
        name="get_current_chapter",
        description="读取指定章节的大纲和正文内容",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_current_chapter,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节号（如 '001' 或 '1'）"},
                "project_id": {"type": "string", "description": "项目ID（可选）"},
            },
            "required": ["chapter_id"],
        },
    )

    async def get_chapter_outline(
        chapter_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取指定章节的大纲规划。"""
        adapter = _get_adapter()
        outline = adapter.get_chapter_outline(chapter_id)
        return outline or {"error": f"未找到第 {chapter_id} 章的大纲"}

    reg.register(
        name="get_chapter_outline",
        description="获取指定章节的详细分章大纲",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_chapter_outline,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节号"},
                "project_id": {"type": "string", "description": "项目ID（可选）"},
            },
            "required": ["chapter_id"],
        },
    )

    async def get_character(
        name_or_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取指定角色的设定卡片（外貌、性格、动机、口吻、关系等）。"""
        adapter = _get_adapter()
        char = adapter.get_character_by_name_or_id(name_or_id)
        return char or {"error": f"未找到角色 '{name_or_id}' 的设定卡片"}

    reg.register(
        name="get_character",
        description="根据角色名或ID查询角色设定卡片",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_character,
        parameters_schema={
            "type": "object",
            "properties": {
                "name_or_id": {"type": "string", "description": "角色名字或ID"},
                "project_id": {"type": "string", "description": "项目ID（可选）"},
            },
            "required": ["name_or_id"],
        },
    )

    async def get_world_rules(project_id: Optional[str] = None) -> Dict[str, Any]:
        """获取作品的世界观设定与规则约束。"""
        adapter = _get_adapter()
        rules = adapter.get_world_rules()
        return rules or {"world_rules": []}

    reg.register(
        name="get_world_rules",
        description="读取作品的世界观设定与世界规则",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_world_rules,
        parameters_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID（可选）"}
            },
        },
    )

    async def get_quality_report(
        chapter_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取指定章节的统一质检门禁报告。"""
        adapter = _get_adapter()
        rep = adapter.get_gate_report(chapter_id)
        return rep or {"error": f"第 {chapter_id} 章暂无门禁质检报告"}

    reg.register(
        name="get_quality_report",
        description="读取指定章节的质检门禁诊断报告",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=get_quality_report,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节号"},
                "project_id": {"type": "string", "description": "项目ID（可选）"},
            },
            "required": ["chapter_id"],
        },
    )

    # ================= LEVEL 1: SEARCH TOOLS =================

    async def search_story(
        query: str,
        before_chapter: Optional[str] = None,
        limit: int = 5,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """全文检索作品事实与前文记忆（支持 before_chapter 防剧透）。"""
        adapter = _get_adapter()
        return adapter.search_story_memory(query, before_chapter=before_chapter, limit=limit)

    reg.register(
        name="search_story",
        description="通过全文检索作品已写正文与大纲记忆，避免设定冲突与未来剧情透底",
        permission_level=PermissionLevel.LEVEL_1_SEARCH,
        handler=search_story,
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或疑问"},
                "before_chapter": {"type": "string", "description": "截止章节号（防剧透过滤）"},
                "limit": {"type": "integer", "description": "返回最多结果条数", "default": 5},
            },
            "required": ["query"],
        },
    )

    # ================= LEVEL 3: PROPOSAL TOOLS =================

    async def propose_text_patch(
        chapter_id: str,
        original_text: str,
        proposed_text: str,
        reason: str = "",
        source_range: Optional[Dict[str, int]] = None,
        skill_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """提议对稿件的修改（生成 Diff Proposal，不直接写入文件，需用户在界面确认）。"""
        service = _get_patch_service()
        range_obj = None
        if source_range and "from_pos" in source_range and "to_pos" in source_range:
            range_obj = EditorRange(from_pos=source_range["from_pos"], to_pos=source_range["to_pos"])

        patch = service.create_patch(
            chapter_id=chapter_id,
            original_text=original_text,
            proposed_text=proposed_text,
            reason=reason,
            skill_id=skill_id,
            source_range=range_obj,
            project_id=project_id,
        )
        return {
            "patch_id": patch.id,
            "status": patch.status.value,
            "chapter_id": patch.chapter_id,
            "original_text": patch.original_text,
            "proposed_text": patch.proposed_text,
            "reason": patch.reason,
            "requires_confirmation": True,
        }

    reg.register(
        name="propose_text_patch",
        description="对指定章节正文生成修改提议（安全提议，不会直接篡改文件，需用户接受）",
        permission_level=PermissionLevel.LEVEL_3_PROPOSAL,
        handler=propose_text_patch,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "修改的章节号"},
                "original_text": {"type": "string", "description": "原稿对应片段"},
                "proposed_text": {"type": "string", "description": "建议修改后的文字"},
                "reason": {"type": "string", "description": "修改原因或说明"},
                "source_range": {
                    "type": "object",
                    "properties": {
                        "from_pos": {"type": "integer"},
                        "to_pos": {"type": "integer"},
                    },
                },
                "skill_id": {"type": "string", "description": "关联的技能ID"},
            },
            "required": ["chapter_id", "original_text", "proposed_text"],
        },
        requires_confirmation=True,
    )

    # ================= LEVEL 4: OPS / MUTATION TOOLS =================

    async def test_model_connection(
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """测试模型连通性与响应。"""
        try:
            import web.routes.assistant as assistant_module
            llm = assistant_module._get_assistant_llm(root_dir)
            if not llm:
                return {"success": False, "error": "未配置大模型或模型处于占位状态"}
            if hasattr(llm, "test"):
                return llm.test()
            return {"success": True, "message": f"模型客户端 {type(llm).__name__} 可用"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    reg.register(
        name="test_model_connection",
        description="测试当前系统配置的大模型连通性",
        permission_level=PermissionLevel.LEVEL_4_MUTATION,
        handler=test_model_connection,
        parameters_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string", "description": "服务商名称（可选）"},
                "model_id": {"type": "string", "description": "模型ID（可选）"},
            },
        },
        requires_confirmation=False,  # Testing connection is safe to run
    )

    async def retry_chapter(
        chapter_id: str,
        goal: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """提交重新生成指定章节任务（需要确认）。"""
        try:
            from web.routes.chapters.tasks import rewrite_chapter
            from web.server import get_project_session
            session = get_project_session()
            task = await rewrite_chapter(str(chapter_id), session)
            return {
                "success": True,
                "task_id": task.task_id,
                "message": f"第 {chapter_id} 章已提交重新生成",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    reg.register(
        name="retry_chapter",
        description="提交重新生成/重写指定章节任务（影响正文，需确认）",
        permission_level=PermissionLevel.LEVEL_4_MUTATION,
        handler=retry_chapter,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节号"},
                "goal": {"type": "string", "description": "生成目标（可选）"},
            },
            "required": ["chapter_id"],
        },
        requires_confirmation=True,
    )

    async def rerun_gate(
        chapter_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """重跑指定章节门禁质检（需要确认）。"""
        try:
            from web.routes.chapters.tasks import rerun_chapter_gate
            from web.server import get_project_session
            session = get_project_session()
            task = await rerun_chapter_gate(str(chapter_id), session)
            return {
                "success": True,
                "task_id": task.task_id,
                "message": f"第 {chapter_id} 章已提交门禁重跑",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    reg.register(
        name="rerun_gate",
        description="对指定章节重新运行质检门禁（需确认）",
        permission_level=PermissionLevel.LEVEL_4_MUTATION,
        handler=rerun_gate,
        parameters_schema={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节号"},
            },
            "required": ["chapter_id"],
        },
        requires_confirmation=True,
    )

    return reg
