"""Extraction and management of protected spans (names, numbers, facts, time)."""

from __future__ import annotations

import re
from typing import List, Optional, Set

from novel_agent.human_writing.schemas import ProtectedSpan

# Common Chinese surnames for heuristic character detection
_COMMON_SURNAMES = (
    "李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林",
    "何", "郭", "马", "罗", "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧", "程", "曹",
    "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕", "苏", "卢", "蒋", "蔡", "贾", "丁", "魏", "薛",
    "叶", "阎", "余", "潘", "杜", "戴", "夏", "钟", "汪", "田", "任", "姜", "范", "方", "石", "姚",
    "谭", "廖", "邹", "熊", "金", "陆", "郝", "孔", "白", "崔", "康", "毛", "邱", "秦", "江", "史",
    "顾", "侯", "邵", "孟", "龙", "万", "段", "钱", "汤", "尹", "黎", "易", "常", "武", "乔", "贺",
    "赖", "龚", "文", "诸葛", "欧阳", "司马", "上官", "慕容", "皇甫", "独孤", "南宫", "东方",
)

_MEASURE_UNITS = (
    "米", "厘米", "公里", "步", "秒", "分", "分钟", "小时", "岁", "斤", "两", "钱", "元", "文",
    "两银子", "铜板", "人", "道", "声", "把", "柄", "柄", "剑", "刀", "枪", "发", "招", "年", "月",
    "日", "天", "周", "次", "遍", "回", "度", "成", "分", "个", "只", "支", "匹", "条", "座", "盏",
)

_TIME_KEYWORDS = (
    "凌晨", "清晨", "早晨", "上午", "正午", "中午", "下午", "傍晚", "黄昏", "入夜", "深夜", "半夜",
    "昨晚", "今晨", "明晨", "翌日", "子时", "丑时", "寅时", "卯时", "辰时", "巳时", "午时",
    "未时", "申时", "酉时", "戌时", "亥时", "三更", "四更", "五更",
)


def extract_protected_spans(
    text: str,
    project_characters: Optional[List[str]] = None,
    known_facts: Optional[List[str]] = None,
) -> List[ProtectedSpan]:
    """Extract entities that must not be corrupted or omitted during rewrite."""
    if not text:
        return []

    spans: List[ProtectedSpan] = []
    seen_keys: Set[tuple[str, int, int]] = set()

    # 1. Project-defined characters
    characters_to_search = set(project_characters or [])
    # Always include common protagonists if mentioned frequently
    for ch in characters_to_search:
        if not ch or len(ch) < 2:
            continue
        for m in re.finditer(re.escape(ch), text):
            key = ("character", m.start(), m.end())
            if key not in seen_keys:
                seen_keys.add(key)
                spans.append(
                    ProtectedSpan(
                        kind="character",
                        value=ch,
                        policy="exact",
                        start=m.start(),
                        end=m.end(),
                    )
                )

    # Heuristic 2-3 char character names starting with common surnames
    if not characters_to_search:
        surname_pat = "|".join(re.escape(s) for s in sorted(_COMMON_SURNAMES, key=len, reverse=True))
        name_re = re.compile(rf"(?<![\u4e00-\u9fa5])({surname_pat})([\u4e00-\u9fa5]{{1,2}})(?![\u4e00-\u9fa5])")
        for m in name_re.finditer(text):
            val = m.group(0)
            # Filter common words that start with surname chars
            if val in ("林中", "金子", "白光", "白纸", "方才", "白费", "高处", "大门"):
                continue
            key = ("character", m.start(), m.end())
            if key not in seen_keys:
                seen_keys.add(key)
                spans.append(
                    ProtectedSpan(
                        kind="character",
                        value=val,
                        policy="exact",
                        start=m.start(),
                        end=m.end(),
                    )
                )

    # 2. Numbers and measurements (e.g. 15米, 三把剑, 500两银子)
    unit_pat = "|".join(re.escape(u) for u in sorted(_MEASURE_UNITS, key=len, reverse=True))
    num_re = re.compile(
        rf"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百千万两]+)\s*(?:{unit_pat})"
    )
    for m in num_re.finditer(text):
        key = ("number", m.start(), m.end())
        if key not in seen_keys:
            seen_keys.add(key)
            spans.append(
                ProtectedSpan(
                    kind="number",
                    value=m.group(0),
                    policy="exact",
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 3. Time expressions
    time_kw_pat = "|".join(re.escape(t) for t in sorted(_TIME_KEYWORDS, key=len, reverse=True))
    time_re = re.compile(rf"(?:{time_kw_pat})(?:[一二三四五六七八九十\d]+[点分刻时])?|\d{{1,2}}:\d{{2}}")
    for m in time_re.finditer(text):
        key = ("time", m.start(), m.end())
        if key not in seen_keys:
            seen_keys.add(key)
            spans.append(
                ProtectedSpan(
                    kind="time",
                    value=m.group(0),
                    policy="exact",
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 4. Known facts
    if known_facts:
        for fact in known_facts:
            if not fact or len(fact) < 4:
                continue
            for m in re.finditer(re.escape(fact), text):
                key = ("plot_fact", m.start(), m.end())
                if key not in seen_keys:
                    seen_keys.add(key)
                    spans.append(
                        ProtectedSpan(
                            kind="plot_fact",
                            value=fact,
                            policy="must_preserve",
                            start=m.start(),
                            end=m.end(),
                        )
                    )

    # Sort spans by starting offset
    return sorted(spans, key=lambda s: (s.start or 0, s.end or 0))
