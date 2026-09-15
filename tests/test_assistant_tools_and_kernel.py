"""Tests for ShanShan Assistant Phase 3: Builtin Tools, RunTracker, and Controlled Kernel."""

import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.kernel import ShanShanKernel
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import (
    ActiveEditorContext,
    EditorRange,
    PatchStatus,
    RunRecord,
    ToolCallStep,
)
from novel_agent.assistant.patch.service import PatchService
from novel_agent.assistant.tools.builtin_tools import register_builtin_tools
from novel_agent.assistant.tools.registry import (
    PermissionLevel,
    ToolDefinition,
    ToolRegistry,
)
from novel_agent.assistant.trace.run_tracker import RunTracker


@pytest.fixture
def temp_project(tmp_path):
    proj_dir = tmp_path / "test_project"
    proj_dir.mkdir()
    (proj_dir / "workspace").mkdir()
    (proj_dir / "config").mkdir()
    (proj_dir / "assets").mkdir()
    (proj_dir / "data").mkdir()
    (proj_dir / "workspace" / "chapters").mkdir()

    # Meta
    (proj_dir / "config" / "project_meta.json").write_text(
        json.dumps({"title": "星际黎明", "genre": "科幻", "premise": "人类远征"}),
        encoding="utf-8",
    )

    # Outline
    (proj_dir / "workspace" / "outline.json").write_text(
        json.dumps({
            "chosen_title": "星际黎明",
            "genre": "科幻",
            "macro_outline": [
                {
                    "arc_id": 1,
                    "title": "启航卷",
                    "chapter_list": [
                        {"chapter_id": "001", "title": "星港之夜", "chapter_goal": "登舰出发"},
                        {"chapter_id": "002", "title": "光速航行", "chapter_goal": "穿越虫洞"},
                    ]
                }
            ]
        }),
        encoding="utf-8",
    )

    # Character cards
    (proj_dir / "assets" / "character_cards.yaml").write_text(
        """
characters:
  - id: char_jiangxin
    name: 江炘
    role: 舰长
    personality: 沉着冷静，杀伐果断
""",
        encoding="utf-8",
    )

    # Chapter 001 text
    ch1_dir = proj_dir / "workspace" / "chapters" / "chapter_001"
    ch1_dir.mkdir()
    (ch1_dir / "chapter.txt").write_text("夜色降临，江炘站在指挥室前，注视着港口的巨型运输舰。", encoding="utf-8")

    return proj_dir


def test_tool_registry_permissions():
    reg = ToolRegistry()
    reg.register(
        name="test_read",
        description="test read tool",
        permission_level=PermissionLevel.LEVEL_0_READ,
        handler=lambda: "read_ok",
    )
    reg.register(
        name="test_mutate",
        description="test mutate tool",
        permission_level=PermissionLevel.LEVEL_4_MUTATION,
        handler=lambda: "mutate_ok",
    )

    assert reg.can_auto_execute("test_read") is True
    assert reg.can_auto_execute("test_mutate") is False

    read_def = reg.get("test_read").definition
    assert read_def.requires_confirmation is False

    mutate_def = reg.get("test_mutate").definition
    assert mutate_def.requires_confirmation is True


@pytest.mark.asyncio
async def test_builtin_tools_execution(temp_project):
    adapter = StoryAdapter(temp_project)
    patch_service = PatchService(temp_project)
    reg = ToolRegistry()
    register_builtin_tools(reg, story_adapter=adapter, patch_service=patch_service, root_dir=temp_project)

    # 1. Level 0: get_project_meta
    tool_meta = reg.get("get_project_meta")
    meta_res = await tool_meta.execute()
    assert meta_res["title"] == "星际黎明"

    # 2. Level 0: get_current_chapter
    tool_ch = reg.get("get_current_chapter")
    ch_res = await tool_ch.execute(chapter_id="001")
    assert ch_res["text_length"] > 0
    assert "江炘" in ch_res["text_preview"]

    # 3. Level 0: get_character
    tool_char = reg.get("get_character")
    char_res = await tool_char.execute(name_or_id="江炘")
    assert char_res["role"] == "舰长"

    # 4. Level 1: search_story
    tool_search = reg.get("search_story")
    search_res = await tool_search.execute(query="指挥室")
    assert len(search_res) >= 1
    assert search_res[0].get("source_chapter") == "001" or "001" in search_res[0].get("memory_id", "")


    # 5. Level 3: propose_text_patch
    tool_patch = reg.get("propose_text_patch")
    patch_res = await tool_patch.execute(
        chapter_id="001",
        original_text="夜色降临",
        proposed_text="深邃的夜色笼罩了星港",
        reason="加强氛围",
    )
    assert patch_res["status"] == "proposed"
    assert patch_res["requires_confirmation"] is True
    assert patch_res["patch_id"].startswith("patch_")


@pytest.mark.asyncio
async def test_run_tracker_and_persistence(temp_project):
    store = AssistantStore(temp_project)
    tracker = RunTracker(store)

    run = tracker.start_run(project_id="test_proj", skill_id="polish")
    assert run.status == "running"

    step = tracker.record_step(
        run_id=run.id,
        tool_name="get_character",
        tool_input={"name_or_id": "江炘"},
        tool_output={"name": "江炘"},
        permission_level=0,
        status="success",
        elapsed_ms=12,
    )
    assert step.tool_name == "get_character"

    finished = tracker.finish_run(run.id, status="completed", output_text="已为您查证江炘资料")
    assert finished.status == "completed"
    assert len(finished.steps) == 1

    # Verify SQLite persistence
    persisted = store.get_run(run.id)
    assert persisted is not None
    assert persisted.id == run.id
    assert persisted.skill_id == "polish"
    assert len(persisted.steps) == 1
    assert persisted.steps[0].tool_name == "get_character"


@pytest.mark.asyncio
async def test_kernel_controlled_loop_auto_execute(temp_project):
    kernel = ShanShanKernel(root_dir=temp_project)

    # Mock LLM that asks for character info first, then answers
    responses = [
        '===TOOL_CALL===\n{"name": "get_character", "arguments": {"name_or_id": "江炘"}}',
        '江炘是启航舰队的舰长，性格沉着冷静。',
    ]

    async def mock_llm(prompt: str) -> str:
        return responses.pop(0)

    result = await kernel.run(
        user_message="江炘是谁？",
        llm_caller=mock_llm,
        project_id="test_proj",
    )

    assert result.status == "completed"
    assert "江炘是启航舰队的舰长" in result.reply
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == "get_character"
    assert result.steps[0].permission_level == 0


@pytest.mark.asyncio
async def test_kernel_max_steps_limit(temp_project):
    kernel = ShanShanKernel(root_dir=temp_project)

    # Mock LLM that keeps looping tool calls
    async def infinite_tool_caller(prompt: str) -> str:
        return '===TOOL_CALL===\n{"name": "get_project_meta", "arguments": {}}'

    result = await kernel.run(
        user_message="循环测试",
        llm_caller=infinite_tool_caller,
        max_steps=3,
    )

    # Must be bounded by max_steps
    assert len(result.steps) == 3


@pytest.mark.asyncio
async def test_kernel_plan_act_ops_confirmation(temp_project):
    kernel = ShanShanKernel(root_dir=temp_project)

    # LLM requests Level 4 mutation tool retry_chapter
    async def ops_caller(prompt: str) -> str:
        return '===TOOL_CALL===\n{"name": "retry_chapter", "arguments": {"chapter_id": "001"}}'

    result = await kernel.run(
        user_message="重新生成第1章",
        llm_caller=ops_caller,
    )

    # Must require confirmation, not execute automatically
    assert result.status == "requires_confirmation"
    assert result.action_proposal is not None
    assert result.action_proposal["name"] == "retry_chapter"
    assert result.action_proposal["requires_confirmation"] is True
    assert len(result.actions) == 1
    assert result.actions[0]["type"] == "kernel_confirm_action"
