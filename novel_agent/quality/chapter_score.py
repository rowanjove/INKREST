"""Deterministic 0–10 chapter score. L0 fail is always <6; L1 only subtracts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from novel_agent.quality.guard_registry import L0_HARD_CHECKS

KEEP_THRESHOLD = 6.0
L1_CHECK_NAMES = frozenset(
    {
        "style",
        "anti_ai_flavor",
        "expression_repetition",
        "event_consistency",
        "prose_identity",
        "reference_similarity",
        "burstiness",
        "fact_ledger",
    }
)


def _blocked_by(report: Mapping[str, Any], text: str) -> List[str]:
    guard = report.get("guard_summary") if isinstance(report.get("guard_summary"), dict) else {}
    blocked = [str(item).strip() for item in (guard.get("blocked_by") or []) if str(item).strip()]
    if not (text or "").strip() and "non_empty_final_text" not in blocked:
        blocked = ["non_empty_final_text", *blocked]
    return blocked


def compute_chapter_score(report: Mapping[str, Any], text: str = "") -> Dict[str, Any]:
    """Return a keep/discard card: score 0–10, keep flag, blocked_by, reasons."""
    blocked = _blocked_by(report, text)
    if not (text or "").strip():
        return {
            "score": 0.0,
            "keep": False,
            "band": "retry",
            "blocked_by": blocked,
            "reasons": ["L0:non_empty_final_text"],
        }
    if blocked:
        score = max(0.5, round(5.5 - 0.5 * max(0, len(blocked) - 1), 1))
        return {
            "score": score,
            "keep": False,
            "band": "retry",
            "blocked_by": blocked,
            "reasons": [f"L0:{name}" for name in blocked],
        }

    score = 9.5
    reasons: List[str] = []
    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    for name, check in checks.items():
        if not isinstance(check, dict) or str(name) in L0_HARD_CHECKS:
            continue
        level = str(check.get("level") or "none").lower()
        if check.get("pass") is False or level == "fail":
            score -= 0.4
            reasons.append(f"L1:{name}")
        elif level in {"warning", "review"} or (str(name) in L1_CHECK_NAMES and level not in {"none", ""}):
            score -= 0.15
            reasons.append(f"L1warn:{name}")
    score = max(0.0, min(10.0, round(score, 1)))
    keep = score >= KEEP_THRESHOLD
    return {
        "score": score,
        "keep": keep,
        "band": "keep" if keep else "retry",
        "blocked_by": [] if keep else ["chapter_score"],
        "reasons": reasons,
    }
