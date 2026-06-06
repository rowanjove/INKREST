"""Quality gate configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

VALID_QUALITY_MODES = frozenset({"report_only", "block_on_fail"})
VALID_PERSONA_MODES = frozenset({"off", "full", "on_fail_only", "auto"})

# When pipeline.yaml uses persona_evaluations: auto (or omits it)
_SCALE_PERSONA_DEFAULTS: Dict[str, str] = {
    "micro": "off",
    "short": "on_fail_only",
    "medium": "on_fail_only",
    "long": "off",
    "epic": "off",
    "infinite": "off",
}


def resolve_quality_mode(root_dir: Path) -> str:
    from novel_agent.pipeline import load_pipeline_settings

    raw = load_pipeline_settings(root_dir).get("chapter", {}).get("quality_mode", "report_only")
    mode = str(raw or "report_only").strip()
    return mode if mode in VALID_QUALITY_MODES else "report_only"


def quality_gate_blocks(report: Dict[str, Any], mode: str) -> bool:
    """Return True when the chapter should not proceed to post_audit persistence."""
    if mode != "block_on_fail":
        return False
    summary = report.get("guard_summary") or {}
    if summary.get("overall_status") == "FAIL":
        return True
    if not report.get("overall_pass", True):
        for check in (report.get("checks") or {}).values():
            if check.get("level") == "fail":
                return True
    return False


def resolve_quality_auto_rewrite(root_dir: Path) -> bool:
    from novel_agent.pipeline import load_pipeline_settings

    chapter = load_pipeline_settings(root_dir).get("chapter", {})
    if "quality_auto_rewrite" in chapter:
        return bool(chapter.get("quality_auto_rewrite"))
    # Default: try one rewrite when strict gate is on
    return resolve_quality_mode(root_dir) == "block_on_fail"


def default_persona_mode_for_scale(scale: str) -> str:
    return _SCALE_PERSONA_DEFAULTS.get(str(scale or "medium").strip(), "on_fail_only")


def resolve_persona_evaluations(root_dir: Path) -> str:
    """Resolved mode: off | full | on_fail_only (never returns auto)."""
    from novel_agent.pipeline import load_pipeline_settings

    raw_value = load_pipeline_settings(root_dir).get("chapter", {}).get(
        "persona_evaluations", "auto"
    )
    raw = str(raw_value).strip().lower()
    if raw in ("false", "0", "no"):
        return "off"
    if raw == "auto" or raw == "":
        from novel_agent.control.runtime_policy import resolve_runtime_policy

        policy = resolve_runtime_policy(root_dir)
        return default_persona_mode_for_scale(policy.scale)
    if raw in VALID_PERSONA_MODES:
        return raw
    return "on_fail_only"


def quality_report_warrants_persona_eval(report: Dict[str, Any]) -> bool:
    """True when reader persona LLM runs are worth the cost for this report."""
    if not report.get("overall_pass", True):
        return True
    summary = report.get("guard_summary") or {}
    status = str(summary.get("overall_status") or "").upper()
    if status in ("FAIL", "WARN"):
        return True
    for check in (report.get("checks") or {}).values():
        if not isinstance(check, dict):
            continue
        level = str(check.get("level") or "").lower()
        if level in ("fail", "warning", "review"):
            return True
    return False


def should_run_persona_evaluations(root_dir: Path, quality_report: Dict[str, Any]) -> bool:
    mode = resolve_persona_evaluations(root_dir)
    if mode == "off":
        return False
    if mode == "full":
        return True
    return quality_report_warrants_persona_eval(quality_report)


def format_quality_block_message(report: Dict[str, Any]) -> str:
    summary = report.get("guard_summary") or {}
    blocked = summary.get("blocked_by") or []
    if blocked:
        return f"质量门禁未通过（阻断项: {', '.join(blocked)}），已暂停落库，请修改正文后重试审校。"
    return "质量门禁未通过，已暂停落库，请修改正文后重试审校。"