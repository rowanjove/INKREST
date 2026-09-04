import pytest

from novel_agent.agents.chapter_planner import ChapterPlannerAgent
from novel_agent.exceptions import LLMResponseError
from novel_agent.quality.golden_three import audit_golden_three
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.settings import quality_gate_blocks


def test_audit_golden_three_skips_later_chapters():
    result = audit_golden_three("任意正文", chapter_id="004")
    assert result["metrics"]["skipped"] is True
    assert result["pass"] is True


def test_audit_golden_three_warns_on_short_speechless_ending():
    result = audit_golden_three("林澈走了进去。", chapter_id="001")
    assert result["pass"] is True
    assert result["level"] == "warning"
    assert any("篇幅过短" in item for item in result["details"])


def test_quality_report_golden_three_is_report_only(tmp_path):
    report = build_quality_report(
        "林澈走了进去。",
        root_dir=tmp_path,
        chapter_id="001",
        mode="report_only",
    )
    assert report["checks"]["golden_three"]["pass"] is True
    assert quality_gate_blocks(report, "report_only") is False


def test_chapter_planner_rejects_thin_golden_three_beats():
    agent = ChapterPlannerAgent(llm=None)
    with pytest.raises(LLMResponseError, match="黄金三章"):
        agent._validate(
            {"beats": [{"content": "开场"}]},
            {"chapter_id": "001", "chapter_goal": "绑定系统"},
        )


def test_chapter_planner_accepts_two_golden_three_beats():
    agent = ChapterPlannerAgent(llm=None)
    result = agent._validate(
        {
            "beats": [
                {"content": "困境与金手指出现"},
                {"content": "留下今晚必须回应的悬念钩子"},
            ]
        },
        {"chapter_id": "001", "chapter_goal": "绑定系统"},
    )
    assert len(result["beats"]) == 2
