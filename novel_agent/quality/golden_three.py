"""Deterministic golden-three (chapters 1-3) checks. Report-only."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_CHAPTER_NUMBER_RE = re.compile(r"(\d+)")


def parse_chapter_number(chapter_id: Optional[str]) -> Optional[int]:
    if not chapter_id:
        return None
    match = _CHAPTER_NUMBER_RE.search(str(chapter_id))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def audit_golden_three(text: str, chapter_id: Optional[str] = None) -> Dict[str, Any]:
    chapter_number = parse_chapter_number(chapter_id)
    if chapter_number not in (1, 2, 3):
        return {
            "pass": True,
            "level": "none",
            "score": 100,
            "details": [],
            "metrics": {"skipped": True},
        }
    body = (text or "").strip()
    details = []
    if len(body) < 800:
        details.append(f"第 {chapter_number} 章篇幅过短（{len(body)} 字），黄金三章留存容易断")
    tail = body[-80:]
    if body and not any(mark in tail for mark in ("？", "!", "！", "…", "...", "吗", "呢")):
        details.append(f"第 {chapter_number} 章章末缺少追读钩子")
    if "“" not in body and "「" not in body and '"' not in body:
        details.append(f"第 {chapter_number} 章缺少对白，容易写成说明书")
    return {
        "pass": True,
        "level": "warning" if details else "none",
        "score": 80 if details else 100,
        "details": details,
        "metrics": {"chapter_number": chapter_number, "chars": len(body)},
    }
