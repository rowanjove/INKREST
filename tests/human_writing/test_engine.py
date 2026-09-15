"""Tests for HumanWritingEngine full scanning and scoring."""

import time
from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.quality.audit_schema import validate_audit_report


def test_engine_clean_prose():
    engine = HumanWritingEngine()
    clean_sample = (
        "傍晚时分，雨渐渐停了。\n\n"
        "林默踩着湿漉漉的石阶走上斜坡，巷口的小卖部亮着一盏昏黄的白炽灯。"
        "老板娘正低头擦拭玻璃柜台，收音机里断断续续放着评弹。"
        "他在屋檐下收起黑伞，水滴顺着伞尖渗进砖缝里。\n\n"
        "“买包烟。”他掏出零钱放在台面上。\n\n"
        "老板娘抬头打量了他一眼，从货架第二层抽出一盒递过来。"
    )
    report = engine.scan_text(clean_sample, chapter_id="001")
    assert report.char_count == len(clean_sample)
    assert report.scores.template_risk < 15
    assert report.scores.overall_score >= 85
    assert len(report.issues) == 0


def test_engine_slop_detection_and_scoring():
    engine = HumanWritingEngine()
    slop_sample = (
        "这不是一次简单的任务，而是一次关乎生死存亡的决战。\n\n"
        "林默紧攥着拳头。显然他非常紧张，内心的恐惧如潮水般涌来。"
        "空气仿佛凝固了一般。听到脚步声，他喉结滚动，倒吸一口凉气，瞳孔骤缩。\n\n"
        "真正的问题在于，命运的齿轮早就在暗中转动了。"
        "殊不知，在某种程度上说，他注定会改变整个格局。\n\n"
        "直到这一刻，他才真正明白，人生是一场没有回头路的深渊。"
    )
    report = engine.scan_text(slop_sample, chapter_id="002")
    assert report.scores.template_risk >= 40
    assert report.scores.overall_score <= 60
    assert len(report.issues) >= 4

    # Verify audit schema compatibility
    audit_issues = report.to_audit_issues()
    assert len(audit_issues) == len(report.issues)
    for ai in audit_issues:
        assert ai["issue_layer"] in ("plan", "text", "state", "risk")
        assert ai["severity"] in ("low", "medium", "high")
        assert "why" in ai
        assert "fix" in ai
        assert "hwe" in ai

    # Test integration into full audit report structure
    dummy_audit_report = {
        "risk_level": "中",
        "issues": audit_issues,
        "state_update": {},
    }
    validated = validate_audit_report(dummy_audit_report)
    assert validated is not None


def test_engine_performance_5000_chars():
    engine = HumanWritingEngine()
    # Construct a 5000-char realistic text sample
    base_paragraph = (
        "初秋的雨水打在旧式洋楼的窗棂上，发出沉闷的笃笃声。"
        "周晴把泡好的红茶端到茶几旁，热气在微凉的室内缓缓升腾。"
        "桌上散落着几张发黄的旧图纸，边角已被反复翻阅磨得起了毛边。"
        "林默靠在沙发背上，目光看着窗外灰蒙蒙的江面，手中的钢笔轻轻敲击着记事本。\n\n"
    )
    long_text = base_paragraph * 45  # ~5300 characters
    assert len(long_text) >= 5000

    start = time.perf_counter()
    report = engine.scan_text(long_text, chapter_id="perf_test")
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Must scan 5000 characters in < 300ms (PRD standard)
    assert elapsed_ms < 300.0, f"Expected < 300ms, took {elapsed_ms:.2f}ms"
    assert report.char_count == len(long_text)
