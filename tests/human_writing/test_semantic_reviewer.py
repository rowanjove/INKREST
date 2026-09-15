"""Unit tests for HWESemanticReviewer (PRD §8.1, §39, §40)."""

import pytest
from novel_agent.human_writing.semantic_reviewer import (
    HWESemanticReviewer,
    should_run_semantic_review,
)


def test_should_run_semantic_review_gating():
    """Verify gating conditions conforming to PRD §39."""
    # Clean text, normal mode -> False
    assert not should_run_semantic_review(template_risk=10.0, mode="normal")

    # High risk (> 35) -> True
    assert should_run_semantic_review(template_risk=36.0, mode="normal")

    # Strict mode -> True
    assert should_run_semantic_review(template_risk=5.0, mode="strict")

    # User explicitly requested -> True
    assert should_run_semantic_review(template_risk=5.0, user_requested=True)

    # Publish stage -> True
    assert should_run_semantic_review(template_risk=5.0, is_publish=True)

    # Style editor ran -> True
    assert should_run_semantic_review(template_risk=5.0, style_ran=True)


def test_heuristic_semantic_reviewer_catches_editorial_and_emotion():
    """Verify offline heuristic fallback detects author emotion explanation and fatalism."""
    reviewer = HWESemanticReviewer(llm_client=None)

    text = (
        "他深吸了一口气，他意识到自己其实正在害怕这个对手。\n"
        "殊不知，命运的齿轮已经悄然转动。\n"
        "林默拔出了配枪。"
    )

    # Should trigger because template_risk > 35
    issues = reviewer.review(text, template_risk=40.0)
    assert len(issues) >= 2

    types = {i.type for i in issues}
    assert "HWE.SEMANTIC.EMOTION_EXPLANATION" in types
    assert "HWE.SEMANTIC.AUTHOR_EDITORIAL" in types

    for issue in issues:
        assert issue.hwe.source == "semantic_model"
        assert issue.fix != ""


def test_model_response_parsing():
    """Verify JSON parsing and conversion to HWEIssue models."""
    mock_json = """
    [
        {
            "type": "HWE.SEMANTIC.POV_LEAK",
            "text": "苏然心中暗自盘算着逃脱的路线",
            "why": "在林默的第三人称限知视角中，不可直接获知苏然的隐秘内心算计。",
            "fix": "改为林默观察到苏然的眼神游移在窗户与后门之间。",
            "line": 1
        }
    ]
    """

    class MockLLM:
        def generate(self, system: str, prompt: str) -> str:
            return f"```json\n{mock_json}\n```"

    reviewer = HWESemanticReviewer(llm_client=MockLLM())
    text = "苏然心中暗自盘算着逃脱的路线。林默靠在墙角抽烟。"

    issues = reviewer.review(text, user_requested=True)
    assert len(issues) == 1
    assert issues[0].type == "HWE.SEMANTIC.POV_LEAK"
    assert "限知视角" in issues[0].why
    assert issues[0].hwe.start == 0
    assert issues[0].hwe.end == len("苏然心中暗自盘算着逃脱的路线")
