"""Generation-phase policy: style mode, boundary recheck, length_fix, writer hints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_GENERATION_STYLE_MODES = frozenset({"full", "off", "gate_only", "balanced", "auto"})


def resolve_generation_style_mode(root_dir: Path) -> str:
    from novel_agent.pipeline import load_pipeline_settings

    raw = str(
        load_pipeline_settings(root_dir).get("chapter", {}).get("generation_style_mode", "full")
        or "full"
    ).strip().lower()
    if raw == "balanced":
        return "full"
    if raw in VALID_GENERATION_STYLE_MODES:
        return raw
    return "full"


def _effective_style_mode(root_dir: Path, explicit_mode: str) -> str:
    if explicit_mode != "auto":
        return explicit_mode
    from novel_agent.control.runtime_policy import resolve_runtime_policy

    tier = resolve_runtime_policy(root_dir).audit_profile
    if tier == "economy":
        return "gate_only"
    return "full"


def should_run_generation_style_edit(
    root_dir: Path,
    *,
    skip_style_edit: bool = False,
) -> bool:
    """True when generation phase should run full-chapter style_editor."""
    if skip_style_edit:
        return False
    mode = _effective_style_mode(root_dir, resolve_generation_style_mode(root_dir))
    return mode == "full"


def resolve_boundary_recheck_after_style(root_dir: Path) -> bool:
    from novel_agent.pipeline import load_pipeline_settings

    chapter = load_pipeline_settings(root_dir).get("chapter", {}) or {}
    if "boundary_recheck_after_style" in chapter:
        return bool(chapter.get("boundary_recheck_after_style"))
    return True


def resolve_boundary_recheck_only_after_style(root_dir: Path) -> bool:
    from novel_agent.pipeline import load_pipeline_settings

    chapter = load_pipeline_settings(root_dir).get("chapter", {}) or {}
    if "boundary_recheck_only_after_style" in chapter:
        return bool(chapter.get("boundary_recheck_only_after_style"))
    return True


def should_run_boundary_recheck(
    root_dir: Path,
    *,
    style_ran: bool,
    scene_count: int,
) -> bool:
    """Whether to run post-generation boundary stitch pass."""
    if scene_count <= 1:
        return False
    if not resolve_boundary_recheck_after_style(root_dir):
        return False
    if resolve_boundary_recheck_only_after_style(root_dir) and not style_ran:
        return False
    return True


def should_length_fix_after_audit_rewrite(
    issues: Optional[List[Any]] = None,
    wordcount: Optional[Dict[str, Any]] = None,
) -> bool:
    """Only adjust chapter length after audit rewrite when wordcount is the problem."""
    wc = wordcount or {}
    if str(wc.get("status") or "") in ("under", "over"):
        return True
    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        if str(issue.get("type") or "") == "word_count_out_of_bounds":
            return True
        if str(issue.get("audit_class") or "") == "CRITICAL" and "word" in str(
            issue.get("type") or ""
        ).lower():
            return True
    return False


def build_writer_anti_ai_block(root_dir: Path) -> str:
    """Compact writing constraints injected into scene writer context."""
    try:
        from novel_agent.quality.style_rules import load_style_rules_config

        cfg = load_style_rules_config(Path(root_dir))
    except Exception:
        cfg = {}
    rules = (cfg or {}).get("rules", {}) or {}
    lines = [
        "避免 AI 腔：不禁/竟然/仿佛…一般/心中暗道/眼中闪过一丝等模板句。",
        "用动作与感官代替情绪直写；对话口语化；章末留动作悬念勿感慨总结。",
    ]
    disabled = [
        name
        for name, spec in rules.items()
        if isinstance(spec, dict) and not spec.get("enabled", True)
    ]
    if disabled:
        lines.append(f"（项目已关闭部分规则检测：{', '.join(disabled[:6])}）")
    return "\n".join(lines)


BOUNDARY_RECHECK_INSTRUCTION = (
    "\n\n【边界复检任务】上文为全章正文。请仅修正场景/段落切换处的突兀、重复或时空断裂，"
    "保持其余段落措辞基本不变，不删减剧情。输出完整修订版正文。"
)