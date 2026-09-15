"""Unit tests for HWE HumanContextCompiler (PRD §7, §41)."""

from pathlib import Path
import pytest

from novel_agent.human_writing.context_compiler import (
    HumanContextCompiler,
    HumanPromptContext,
    compile_human_writing_prompt,
)


def test_context_compiler_basic():
    """Test basic compilation with default parameters."""
    compiler = HumanContextCompiler()
    ctx = HumanPromptContext(
        genre="都市悬疑",
        scene_type="高压对峙",
        pov="第三人称限知",
        characters=["林默", "周晴"],
        user_constraints=["严禁出现任何科幻机械神仙解局"],
    )
    result = compiler.compile(ctx)

    assert "[本章文风与去套路约束]" in result
    assert "【用户要求】严禁出现任何科幻机械神仙解局" in result
    assert "高压对峙" in result
    assert "第三人称限知" in result
    assert len(result) <= 1200


def test_priority_ordering_conforms_to_prd():
    """Verify that constraints strictly follow PRD §7.2 priority ordering."""
    compiler = HumanContextCompiler()
    ctx = HumanPromptContext(
        user_constraints=["必须在5分钟内离开房间"],
        author_style_profile={
            "tone": "冷峻克制、短句推进",
            "forbidden_tropes": ["机械降神", "突兀恋爱脑"],
        },
        character_voice={
            "林默": {
                "tone": "说话极快，自信果决",
                "catchphrases": ["按规矩办"],
            }
        },
        scene_type="高压对峙",
        pov="第三人称限知",
        recent_expression_memory=["喉结滚动", "指尖发冷"],
        genre="都市悬疑",
    )
    result = compiler.compile(ctx)

    idx_user = result.find("必须在5分钟内离开房间")
    idx_style = result.find("冷峻克制")
    idx_voice = result.find("林默")
    idx_scene = result.find("高压对峙")
    idx_memory = result.find("喉结滚动")
    idx_genre = result.find("悬疑质感")

    assert idx_user != -1
    assert idx_style != -1
    assert idx_voice != -1
    assert idx_scene != -1
    assert idx_memory != -1
    assert idx_genre != -1

    # PRD §7.2: User > Author Style > Character Voice > Scene/POV > Memory > Genre
    assert idx_user < idx_style < idx_voice < idx_scene < idx_memory < idx_genre


def test_character_voice_conflicts_suppress_generic_rules():
    """Verify PRD §18: Character Voice > Generic HWE Rule."""
    compiler = HumanContextCompiler()

    # Case 1: Character intentionally uses rhetorical questions
    ctx = HumanPromptContext(
        characters=["林默"],
        character_voice={
            "林默": {
                "tone": "说话充满攻击性，习惯高频反问与连续设问质问对方",
                "speech_patterns": ["每句话都以反问句收尾"],
            }
        },
        scene_type="交锋对话",
    )
    result = compiler.compile(ctx)

    assert "该角色固有口吻优先，不受通用句式规避限制" in result
    # Generic rhetorical slop rule must NOT appear in generic rules
    assert "HWE.DIALOGUE.RHETORICAL_OVERUSE" not in result
    assert "机械反问连击" not in result

    # Case 2: Character intentionally uses binary contrast (不是…而是…)
    ctx2 = HumanPromptContext(
        characters=["学者A"],
        character_voice={
            "学者A": {
                "tone": "习惯社论式思辨，极度偏好‘不是…而是…’的对比句式",
                "catchphrases": ["不是A而是B", "关键在于"],
            }
        },
    )
    result2 = compiler.compile(ctx2)
    assert "固有口吻优先" in result2
    # Generic binary contrast rule should be suppressed for this character
    assert "机械式否定翻转" not in result2


def test_recent_expression_saturation_warning():
    """Verify that recent expressions trigger saturation warning."""
    compiler = HumanContextCompiler()
    ctx = HumanPromptContext(
        recent_expression_memory=["喉结滚动", "指尖发冷", "空气仿佛凝固"],
    )
    result = compiler.compile(ctx)

    assert "【近期表达饱和预警】" in result
    assert "喉结滚动" in result
    assert "指尖发冷" in result
    assert "空气仿佛凝固" in result


def test_token_char_budget_trimming():
    """Verify PRD §41: Strict char budget limiter (max 1200 chars)."""
    compiler = HumanContextCompiler()

    # Create very large context
    user_rules = [f"测试用户要求{i}：严禁滥用任何第{i}套路" for i in range(10)]
    ctx = HumanPromptContext(
        user_constraints=user_rules,
        scene_type="高压对峙",
        recent_expression_memory=[f"高频词{i}" for i in range(20)],
        max_chars_budget=400,  # Strict tight budget
    )
    result = compiler.compile(ctx)

    assert len(result) <= 400
    assert "[本章文风与去套路约束]" in result
    # User constraint is highest priority, should be preserved
    assert "测试用户要求0" in result


def test_compile_human_writing_prompt_factory(tmp_path: Path):
    """Test convenience factory with mock scene and plan."""
    scene = {
        "scene_id": "scene_01",
        "type": "高压对峙",
        "characters": ["林默", "苏然"],
    }
    plan = {
        "chapter_id": "001",
        "pov": "第三人称限知",
    }
    block = compile_human_writing_prompt(
        root_dir=tmp_path,
        scene=scene,
        plan=plan,
        user_constraints=["避免过长环境描写"],
        genre="都市悬疑",
    )

    assert "[本章文风与去套路约束]" in result if "result" in locals() else "[本章文风与去套路约束]" in block
    assert "避免过长环境描写" in block
    assert "高压对峙" in block
    assert "第三人称限知" in block
    assert len(block) <= 1200
