from __future__ import annotations

from typing import Any, Dict, List

from novel_agent.control.chapter_window import build_pacing_report


def build_calibration_report(
    outline: Dict[str, Any],
    chapters: List[Dict[str, Any]],
    debt: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Build a lightweight longform stability report."""
    issues: List[str] = []
    pacing = build_pacing_report(chapters[-10:])
    if not pacing["pass"]:
        issues.extend(pacing["issues"])

    overdue = []
    for items in debt.values():
        overdue.extend([item for item in items if item.get("debt_status") == "overdue"])
    if overdue:
        issues.append("存在过期叙事债务")

    return {
        "pass": not issues,
        "issues": issues,
        "pacing": pacing,
        "overdue_debt_count": len(overdue),
        "genre_genes": outline.get("genre_genes", {}),
        "scale_profile": outline.get("scale_profile", {}),
    }
