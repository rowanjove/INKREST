"""Narrative Tension and Payoff Pacing Tracker.

Analyzes pacing rhythm and emotional wave dynamics across chapters:
- Detects flat storytelling (tension_flat: 3+ chapters without conflict or stakes)
- Detects missing rewards (payoff_delayed: climax with no progression/rewards)
"""

from __future__ import annotations

import re
from typing import Any

HIGH_TENSION_KEYWORDS = {
    "危机", "生死", "突变", "杀机", "暴起", "轰鸣", "绝境", "震骇",
    "破空", "锋芒", "斩", "撕裂", "咆哮", "惊怒", "剧痛", "死死",
    "重创", "血光", "杀意", "狂暴", "险象环生", "一触即发", "命悬一线",
}

PAYOFF_KEYWORDS = {
    "顿悟", "突破", "进阶", "暴涨", "纳戒", "战利品", "臣服", "狂喜",
    "名声", "震惊四座", "倒吸凉气", "收获", "造化", "脱胎换骨", "大喜",
    "至宝", "赏赐", "敬畏", "仰望", "叹为观止", "扬眉吐气",
}

TRANSITIONAL_KEYWORDS = {
    "盘膝", "闭目", "调息", "数日后", "清晨", "客栈", "闲聊", "饮茶",
    "沉吟", "缓缓", "次日", "转眼", "休憩", "端坐", "思索", "打坐",
}


def analyze_chapter_tension(chapter_text: str, chapter_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze tension and payoff characteristics of a chapter."""
    text = str(chapter_text or "")
    if not text:
        return {
            "tension_score": 50,
            "payoff_score": 50,
            "pacing_type": "transitional",
            "tension_keywords_count": 0,
            "payoff_keywords_count": 0,
        }

    # Count signals normalized per 1,000 characters
    total_len = max(len(text), 500)
    norm_factor = 1000.0 / total_len

    tension_hits = sum(text.count(kw) for kw in HIGH_TENSION_KEYWORDS)
    payoff_hits = sum(text.count(kw) for kw in PAYOFF_KEYWORDS)
    transitional_hits = sum(text.count(kw) for kw in TRANSITIONAL_KEYWORDS)

    norm_tension = tension_hits * norm_factor
    norm_payoff = payoff_hits * norm_factor

    tension_score = min(100, int(norm_tension * 15))
    payoff_score = min(100, int(norm_payoff * 20))

    # Pacing classification
    if tension_score >= 60 and tension_score >= payoff_score:
        pacing_type = "climax"
    elif payoff_score >= 50:
        pacing_type = "payoff"
    elif tension_score >= 35:
        pacing_type = "build_up"
    else:
        pacing_type = "transitional"

    return {
        "tension_score": tension_score,
        "payoff_score": payoff_score,
        "pacing_type": pacing_type,
        "tension_keywords_count": tension_hits,
        "payoff_keywords_count": payoff_hits,
        "transitional_keywords_count": transitional_hits,
    }


def evaluate_arc_tension_wave(tension_series: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate multi-chapter tension progression over an arc.
    
    Identifies rhythm anomalies:
    - tension_flat: 3+ chapters of low tension
    - payoff_delayed: climax with missing reward
    """
    if not tension_series:
        return {
            "pacing_health": "good",
            "warnings": [],
            "average_tension": 50.0,
            "wave_profile": [],
        }

    warnings: list[str] = []
    scores = [int(item.get("tension_score", 50)) for item in tension_series]
    avg_tension = sum(scores) / len(scores)

    # Check for flat tension (3+ consecutive low tension)
    low_tension_streak = 0
    for idx, item in enumerate(tension_series):
        if item.get("tension_score", 0) < 30 and item.get("pacing_type") == "transitional":
            low_tension_streak += 1
            if low_tension_streak >= 3:
                warnings.append(f"第 {idx + 1} 章起连续多章剧情节奏平缓缺乏矛盾冲突 (tension_flat)")
        else:
            low_tension_streak = 0

    # Check for payoff delayed (climax followed by no payoff in next 2 chapters)
    for idx in range(len(tension_series) - 2):
        curr = tension_series[idx]
        if curr.get("pacing_type") == "climax" or curr.get("tension_score", 0) >= 70:
            next_two = tension_series[idx + 1 : idx + 3]
            if all(n.get("payoff_score", 0) < 30 for n in next_two):
                warnings.append(f"第 {idx + 1} 章高潮大战后未及时获得战利品或境界成长反馈 (payoff_delayed)")

    return {
        "pacing_health": "warning" if warnings else "good",
        "warnings": warnings,
        "average_tension": round(avg_tension, 1),
        "total_chapters_evaluated": len(tension_series),
    }
