"""Fact Ledger (事实账本) - Deterministic entity, item, and physical fact protection.

Guards against prose rewrite / style editor 'eating' key plot items, erasing characters,
or drifting crucial physical state changes during de-AI polishing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set


# 常见玄幻/网文核心道具后缀
ITEM_SUFFIXES = (
    "剑", "刀", "枪", "戟", "弓", "符", "丹", "鼎", "炉", "旗",
    "石", "珠", "令", "印", "镜", "钟", "戒", "扇", "鞭", "钩",
    "锁", "针", "甲", "衣", "图", "瓶", "袋", "玉", "莲", "草",
)

ITEM_PATTERN = re.compile(
    r"([\u4e00-\u9fa5]{1,6}(?:" + "|".join(ITEM_SUFFIXES) + r"))"
)

# 物理状态突变词
PHYSICAL_STATUS_WORDS = (
    "断臂", "断腿", "盲", "废", "重伤", "濒死", "自爆", "陨落", "身死",
    "突破", "走火入魔", "中毒", "昏迷", "苏醒",
)

PHYSICAL_STATUS_PATTERN = re.compile(
    r"(" + "|".join(PHYSICAL_STATUS_WORDS) + r")"
)


# 常见动量词前缀剥离
PREFIX_VERBS = (
    "手持", "紧握", "握紧", "握着", "取出", "拿出", "祭出", "挥动",
    "拔出", "按住", "怀揣", "吞服", "捏出", "捏着", "收起", "掷出",
    "佩戴", "唤出", "催动", "运转", "施展", "激发",
)

COMMON_STOPS = {
    "衣服", "石头", "石子", "草地", "树图", "地图", "图表", "口袋", "箭头",
    "这一剑", "那一剑", "第一剑", "长剑", "短剑", "长刀", "短刀",
}


def _clean_item_name(raw: str) -> str:
    name = raw.strip()
    # 如果内部包含常见操作动词，截取最后一个动词之后的部分
    for v in PREFIX_VERBS:
        if v in name:
            idx = name.rfind(v)
            name = name[idx + len(v):]
    # 剥离代词
    for p in ("他的", "她的", "它的", "自己", "其"):
        if name.startswith(p):
            name = name[len(p):]
            break
    # 剥离数词、量词与指代词（如“三张”、“一枚”、“这枚”、“那柄”）
    name = re.sub(r"^(?:这|那|[一二三四五六七八九十两几半0-9]+)?[枚张把柄口尊面座具副只套根块颗粒道条]", "", name)
    # 剥离残余的指示代词
    if name.startswith(("这", "那")):
        name = name[1:]
    return name.strip()


def _has_item_context(text: str, start: int, end: int, item: str) -> bool:
    """Return whether a suffix match is strong enough for a blocking fact check.

    The suffix list is intentionally broad, so a bare match such as “深刻烙印”
    is not sufficient.  Hard blocking is limited to explicit possession/use
    language, a nearby Chinese quantifier, or a name repeated in the source.
    """
    context = text[max(0, start - 8):min(len(text), end + 2)]
    if any(verb in context for verb in PREFIX_VERBS):
        return True
    if re.search(
        r"(?:这|那|[一二三四五六七八九十两几半0-9]+)?"
        r"[枚张把柄口尊面座具副只套根块颗粒道条]",
        context,
    ):
        return True
    return text.count(item) >= 2


def extract_physical_facts(text: str) -> Dict[str, Set[str]]:
    """Extract physical facts including props/items and major physical states."""
    if not text:
        return {"items": set(), "physical_states": set()}

    items: Set[str] = set()
    for match in ITEM_PATTERN.finditer(text):
        raw = match.group(1)
        cleaned = _clean_item_name(raw)
        if (
            len(cleaned) >= 2
            and cleaned not in COMMON_STOPS
            and _has_item_context(text, match.start(1), match.end(1), cleaned)
        ):
            items.add(cleaned)

    states = set(PHYSICAL_STATUS_PATTERN.findall(text))

    return {
        "items": items,
        "physical_states": states,
    }


def audit_fact_consistency(
    original_text: str,
    candidate_text: str,
    *,
    critical_items: List[str] | None = None,
) -> Dict[str, Any]:
    """Audit consistency between original draft and candidate edited text.
    
    Verifies that key items and physical changes present in the original draft
    have not been accidentally wiped out or corrupted by the style editor.
    """
    if not original_text or not candidate_text:
        return {
            "pass": True,
            "missing_items": [],
            "missing_states": [],
            "details": [],
        }

    orig_facts = extract_physical_facts(original_text)
    cand_facts = extract_physical_facts(candidate_text)

    # 1. 检查道具遗失
    # 原稿中出现至少 2 次的道具，或者显式指定的关键道具，在润色稿中完全消失（出现 0 次）
    missing_items = []
    items_to_check = set(orig_facts["items"])
    if critical_items:
        items_to_check.update(critical_items)

    for item in items_to_check:
        orig_count = original_text.count(item)
        cand_count = candidate_text.count(item)
        # 只要原稿出现 2 次以上，或者属于高价值道具（如“符”、“丹”、“珠”、“令”），润色稿为 0 则视为遗失
        is_high_value = any(item.endswith(s) for s in ("符", "丹", "珠", "令", "印", "镜", "鼎"))
        if (orig_count >= 2 or is_high_value) and cand_count == 0:
            missing_items.append(item)

    # 2. 检查致命伤势/状态突变遗失
    missing_states = []
    for state in orig_facts["physical_states"]:
        orig_count = original_text.count(state)
        cand_count = candidate_text.count(state)
        if orig_count > 0 and cand_count == 0:
            # 确认润色稿中是否完全遗失该状态
            missing_states.append(state)

    details = []
    if missing_items:
        details.append(f"关键道具遗失: {', '.join(missing_items)}")
    if missing_states:
        details.append(f"关键生理/战力状态遗失: {', '.join(missing_states)}")

    # 关键道具或致命状态遗失超过 2 个，判定契约违背
    is_pass = len(missing_items) == 0 and len(missing_states) <= 1

    return {
        "pass": is_pass,
        "missing_items": sorted(missing_items),
        "missing_states": sorted(missing_states),
        "details": details,
    }
