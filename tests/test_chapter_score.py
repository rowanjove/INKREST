from novel_agent.quality.chapter_score import compute_chapter_score
from novel_agent.quality.report import build_quality_report

ACTION_PROSE = (
    "林澈推开出租屋的门，雨水顺着袖口滴在地上。他走进屋里，看到桌上那封信。\n\n"
    "他伸手拿起信，转身走到窗边说：“今晚必须离开。”灯闪了两下，他拉开门走了出去。"
)


def test_empty_text_scores_below_keep_and_is_attached_to_report():
    report = build_quality_report("", mode="block_on_fail")
    score = report["chapter_score"]
    assert score["score"] < 6
    assert score["keep"] is False
    assert "non_empty_final_text" in score["blocked_by"]


def test_l0_failure_caps_score_below_six():
    result = compute_chapter_score(
        {
            "checks": {
                "scene_delta": {"pass": False, "score": 0, "level": "fail"},
                "style": {"pass": False, "score": 10, "level": "fail"},
            },
            "guard_summary": {
                "overall_status": "FAIL",
                "blocked_by": ["scene_delta"],
            },
        },
        ACTION_PROSE,
    )
    assert result["score"] < 6
    assert result["keep"] is False
    assert result["blocked_by"] == ["scene_delta"]


def test_l0_pass_keeps_score_even_when_l1_fails():
    result = compute_chapter_score(
        {
            "checks": {
                "scene_delta": {"pass": True, "score": 100, "level": "none"},
                "style": {"pass": False, "score": 20, "level": "fail"},
            },
            "guard_summary": {"overall_status": "WARN", "blocked_by": []},
        },
        ACTION_PROSE,
    )
    assert result["score"] >= 6
    assert result["keep"] is True
    assert result["blocked_by"] == []
    assert any("style" in reason for reason in result["reasons"])


def test_many_l1_failures_can_drop_below_keep_without_blocking_report_only():
    checks = {
        "scene_delta": {"pass": True, "score": 100, "level": "none"},
    }
    for index in range(12):
        checks[f"style_{index}"] = {"pass": False, "score": 0, "level": "fail"}
    result = compute_chapter_score(
        {"checks": checks, "guard_summary": {"overall_status": "WARN", "blocked_by": []}},
        ACTION_PROSE,
    )
    assert result["score"] < 6
    assert result["keep"] is False
    from novel_agent.quality.settings import quality_gate_blocks

    report = {
        "guard_summary": {"overall_status": "WARN", "blocked_by": []},
        "checks": checks,
        "chapter_score": result,
    }
    assert quality_gate_blocks(report, "block_on_fail") is True
    assert quality_gate_blocks(report, "report_only") is False
