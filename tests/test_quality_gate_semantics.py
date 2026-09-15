from novel_agent.quality.guard_registry import build_guard_summary
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.settings import quality_gate_blocks
from novel_agent.quality.decision import derive_quality_decision


def test_empty_text_blocks_only_in_strict_mode():
    report = build_quality_report("", mode="block_on_fail")
    assert report["guard_summary"]["overall_status"] == "FAIL"
    assert "non_empty_final_text" in report["guard_summary"]["blocked_by"]
    assert quality_gate_blocks(report, "block_on_fail") is True
    assert quality_gate_blocks(report, "report_only") is False


def test_l0_failure_is_hard_fail_and_blocks_when_strict():
    checks = {
        "scene_delta": {"pass": False, "level": "fail", "score": 0, "details": ["空文本"]},
        "style": {"pass": True, "level": "none", "score": 90, "details": []},
    }
    summary = build_guard_summary("林澈推开门走了进去。", checks)
    assert summary["overall_status"] == "FAIL"
    assert "scene_delta" in summary["blocked_by"]
    report = {"overall_pass": False, "guard_summary": summary, "checks": checks}
    assert quality_gate_blocks(report, "block_on_fail") is True
    assert quality_gate_blocks(report, "report_only") is False


def test_keep_false_blocks_only_in_strict_mode():
    report = {
        "guard_summary": {"overall_status": "WARN", "blocked_by": []},
        "checks": {},
        "chapter_score": {"keep": False, "score": 5.0, "blocked_by": ["scene_delta"]},
    }
    assert quality_gate_blocks(report, "block_on_fail") is True
    assert quality_gate_blocks(report, "report_only") is False


def test_style_failure_stays_warning_and_does_not_block():
    checks = {
        "scene_delta": {"pass": True, "level": "none", "score": 80, "details": []},
        "style": {"pass": False, "level": "fail", "score": 20, "details": ["不禁"]},
    }
    summary = build_guard_summary("林澈推开门走了进去。", checks)
    assert summary["overall_status"] == "WARN"
    assert "style" not in summary["blocked_by"]
    report = {"overall_pass": False, "guard_summary": summary, "checks": checks}
    assert quality_gate_blocks(report, "block_on_fail") is False
    assert quality_gate_blocks(report, "report_only") is False


def test_high_score_l1_warning_is_review_not_failure():
    report = {
        "guard_summary": {"overall_status": "WARN", "blocked_by": []},
        "checks": {"style": {"pass": False, "level": "fail", "details": ["句式重复"]}},
        "chapter_score": {"keep": True, "score": 9.1, "blocked_by": []},
        "incomplete": False,
    }
    decision = derive_quality_decision(report)
    assert decision["status"] == "review"
    assert decision["blocking"] is False
    assert decision["title"] == "可保留，建议优化"


def test_incomplete_audit_has_distinct_recovery_action():
    decision = derive_quality_decision(
        {
            "guard_summary": {"overall_status": "PASS", "blocked_by": []},
            "chapter_score": {"keep": True, "score": 9.5},
            "audit": {"status": "incomplete"},
        }
    )
    assert decision["status"] == "incomplete"
    assert decision["next_action"] == "resume_audit"


def test_partial_stored_decision_is_rederived_with_complete_contract():
    decision = derive_quality_decision(
        {
            "quality_decision": {"status": "pass"},
            "guard_summary": {"overall_status": "FAIL", "blocked_by": ["scene_delta"]},
            "chapter_score": {"keep": True, "score": 9.5},
        }
    )

    assert decision["status"] == "blocked"
    assert decision["blocking"] is True
    assert decision["hard_gate_pass"] is False
