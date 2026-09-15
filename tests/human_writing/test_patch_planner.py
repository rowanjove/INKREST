"""Tests for patch planner and runner."""

from novel_agent.human_writing.editor.patch_planner import create_patch_plan
from novel_agent.human_writing.editor.patch_runner import run_patch
from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.human_writing.protected_spans import extract_protected_spans


def test_patch_planner_groups_issues():
    engine = HumanWritingEngine()
    text = (
        "初秋的雨水打在旧式洋楼的窗棂上。\n\n"
        "这不是一次简单的重逢，而是一次注定改变命运的对决。"
        "林默紧攥着拳头。显然他非常紧张，内心的恐惧如潮水般涌来。\n\n"
        "小巷深处一片安静。"
    )
    report = engine.scan_text(text)
    assert len(report.issues) >= 2

    protected = extract_protected_spans(text, project_characters=["林默"])
    plan = create_patch_plan(report, text, protected)

    assert len(plan) >= 1
    p1 = plan[0]
    assert p1.patch_id.startswith("patch-")
    assert len(p1.rule_ids) >= 1
    assert "林默" in [s.value for s in p1.protected_spans]
    assert p1.original_text != ""


def test_patch_runner_generates_valid_candidate_and_diff():
    engine = HumanWritingEngine()
    text = (
        "林默停下脚步。\n\n"
        "这不是害怕，而是他终于明白了真相。"
        "林默紧攥着拳头。显然他非常紧张，内心的恐惧如潮水般涌来。\n\n"
        "周晴从身后走了过来。"
    )
    report = engine.scan_text(text)
    protected = extract_protected_spans(text, project_characters=["林默", "周晴"])
    plan = create_patch_plan(report, text, protected)
    assert len(plan) >= 1

    candidate = run_patch(plan[0], engine=engine)
    assert candidate.fidelity.passed is True
    assert "林默" in candidate.candidate_text
    assert candidate.utility > 0
    assert candidate.diff_unified != ""
