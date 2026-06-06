"""Common QualityReport shape and aggregation helpers."""

from typing import Any, Dict, Optional

from novel_agent.quality.hooks import extract_tail_hooks, check_head_continuity
from novel_agent.quality.style_rules import check_ai_style, check_anti_ai_flavor, check_paragraph_layout
from novel_agent.quality.scene_delta import check_scene_delta
from novel_agent.quality.guard_registry import build_guard_summary


def _normalize_check(result: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(result)
    raw_score = normalized.get("score", 0)
    if isinstance(raw_score, float):
        score = int(round(raw_score * 100))
    else:
        score = int(raw_score or 0)
    normalized["score"] = max(0, min(100, score))
    level = normalized.get("level")
    if normalized.get("pass", False):
        normalized["level"] = level or "none"
    elif not level or level == "none":
        if normalized["score"] >= 60:
            normalized["level"] = "warning"
        elif normalized["score"] >= 40:
            normalized["level"] = "review"
        else:
            normalized["level"] = "fail"
    normalized.setdefault("details", [])
    return normalized


def build_quality_report(
     final_text: str,
     previous_text: Optional[str] = None,
     plugin_guards: Optional[list] = None,
     root_dir: Optional[Any] = None,
     mode: str = "report_only",
     style_precheck: Optional[Dict[str, Dict[str, Any]]] = None,
 ) -> Dict[str, Any]:
     """Build a comprehensive quality report for a chapter.
 
     Args:
         final_text: The final chapter text
         previous_text: The previous chapter's text (for continuity checking)
         plugin_guards: Active quality guard plugins
         root_dir: The project workspace root directory
 
     Returns:
         Quality report dict with mode, checks, and overall score
     """
     import logging
     from pathlib import Path
     logger = logging.getLogger("novel_agent.quality.report")
 
     # Extract hooks from previous chapter if available
     hooks = extract_tail_hooks(previous_text) if previous_text else {}
 
     config = {}
     if root_dir:
         try:
             from novel_agent.quality.style_rules import load_style_rules_config
             config = load_style_rules_config(Path(root_dir))
         except Exception as e:
             logger.warning("Failed to load style rules config: %s", e)
 
     cached = style_precheck if isinstance(style_precheck, dict) else {}
     style_result = (
         cached["style"]
         if isinstance(cached.get("style"), dict)
         else check_ai_style(final_text, config)
     )
     anti_ai_result = (
         cached["anti_ai_flavor"]
         if isinstance(cached.get("anti_ai_flavor"), dict)
         else check_anti_ai_flavor(final_text, config)
     )

     # Run all checks (style / anti_ai may reuse audit-phase cache)
     raw_checks = {
         "continuity_physical": (
             check_head_continuity(hooks, final_text)
             if hooks
             else {"pass": True, "score": 1.0, "missing_hooks": []}
         ),
         "style": style_result,
         "anti_ai_flavor": anti_ai_result,
         "layout": check_paragraph_layout(final_text, config),
         "scene_delta": check_scene_delta(final_text),
     }
 
     if root_dir:
         try:
             from novel_agent.quality.style_rules import check_reference_similarity
             sim_res = check_reference_similarity(final_text, Path(root_dir))
             raw_checks["reference_similarity"] = sim_res
         except Exception as exc:
             logger.warning("Reference similarity check failed: %s", exc)
 
     for guard in (plugin_guards or []):
         try:
             # Pass a mock GuardContext
             result = guard.check(final_text, {"previous_text": previous_text})
             raw_checks[f"plugin.{guard.get_meta().name}"] = result
         except Exception as exc:
             logger.warning("Plugin guard %s failed: %s", guard.get_meta().name, exc)
 
     checks = {name: _normalize_check(result) for name, result in raw_checks.items()}
 
     # Calculate overall score
     scores = []
     for check_result in checks.values():
         scores.append(check_result.get("score", 0))
 
     overall_score = sum(scores) / len(scores) if scores else 0
 
     guard_summary = build_guard_summary(final_text, checks)
 
     # Determine overall pass/fail. Hard guard failures always win.
     all_passed = (
         guard_summary["overall_status"] != "FAIL"
         and all(check.get("pass", False) for check in checks.values())
     )
 
     resolved_mode = mode if mode in ("report_only", "block_on_fail") else "report_only"
     return {
         "mode": resolved_mode,
         "overall_score": round(overall_score, 1),
         "overall_pass": all_passed,
         "checks": checks,
         "guard_summary": guard_summary,
     }
