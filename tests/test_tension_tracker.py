import pytest
from novel_agent.quality.tension_tracker import (
    analyze_chapter_tension,
    evaluate_arc_tension_wave,
)


def test_analyze_chapter_tension_climax():
    action_text = """
    生死攸关的一瞬，杀机暴起！黑衣修者破空而来，一柄寒芒闪耀的飞剑呼啸斩落。
    剧痛传来，狂暴的劲力撕裂长空，绝境之中，主角惊怒咆哮，血光迸溅！
    """
    analysis = analyze_chapter_tension(action_text)
    assert analysis["tension_score"] >= 60
    assert analysis["pacing_type"] in {"climax", "build_up"}


def test_analyze_chapter_tension_payoff():
    reward_text = """
    大战落幕，主角从敌人的纳戒中清点战利品，赫然是一枚筑基灵果与上古至宝！
    刹那间神念微动，灵力暴涨，直接顿悟突破到炼气九层，四周同门无不倒吸凉气，震惊四座，敬畏仰望。
    """
    analysis = analyze_chapter_tension(reward_text)
    assert analysis["payoff_score"] >= 50
    assert analysis["pacing_type"] == "payoff"


def test_evaluate_arc_tension_wave_flat_and_payoff_delayed():
    # 1. Test flat tension (3+ consecutive transitional low tension)
    flat_series = [
        {"tension_score": 10, "payoff_score": 10, "pacing_type": "transitional"},
        {"tension_score": 15, "payoff_score": 10, "pacing_type": "transitional"},
        {"tension_score": 12, "payoff_score": 15, "pacing_type": "transitional"},
    ]
    flat_eval = evaluate_arc_tension_wave(flat_series)
    assert flat_eval["pacing_health"] == "warning"
    assert any("tension_flat" in w for w in flat_eval["warnings"])

    # 2. Test delayed payoff
    delayed_series = [
        {"tension_score": 85, "payoff_score": 10, "pacing_type": "climax"},
        {"tension_score": 20, "payoff_score": 10, "pacing_type": "transitional"},
        {"tension_score": 25, "payoff_score": 15, "pacing_type": "transitional"},
    ]
    delayed_eval = evaluate_arc_tension_wave(delayed_series)
    assert delayed_eval["pacing_health"] == "warning"
    assert any("payoff_delayed" in w for w in delayed_eval["warnings"])
