"""Common QualityReport shape and aggregation helpers."""

from typing import Any, Dict, Optional

from novel_agent.quality.hooks import extract_tail_hooks, check_head_continuity
from novel_agent.quality.style_rules import check_ai_style, check_anti_ai_flavor, check_paragraph_layout
from novel_agent.quality.scene_delta import check_scene_delta
from novel_agent.quality.guard_registry import build_guard_summary
from novel_agent.control.longform_flags import flag_enabled


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


def _layer_status(checks: Dict[str, Dict[str, Any]], names: list[str]) -> Dict[str, Any]:
    selected = {name: checks[name] for name in names if isinstance(checks.get(name), dict)}
    if any(str(item.get("status") or "").lower() in {"error", "incomplete"} for item in selected.values()):
        status = "error"
    elif any(item.get("pass") is False for item in selected.values()):
        status = "review"
    else:
        status = "pass"
    return {
        "status": status,
        "check_names": list(selected),
        "failed": [name for name, item in selected.items() if item.get("pass") is False],
        "finding_count": sum(len(item.get("findings") or []) for item in selected.values()),
    }


def _build_quality_layers(
    checks: Dict[str, Dict[str, Any]],
    *,
    audit: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Expose stable L0/L1/L2 buckets for the review center."""

    layers = {
        "L0": _layer_status(
            checks,
            ["continuity_physical", "layout", "scene_delta", "canon_visibility"],
        ),
        "L1": _layer_status(
            checks,
            [
                "style",
                "anti_ai_flavor",
                "expression_repetition",
                "event_consistency",
                "prose_identity",
                "reference_similarity",
            ],
        ),
        "L2": {
            "status": "unavailable",
            "check_names": [],
            "failed": [],
            "finding_count": 0,
        },
    }
    if isinstance(audit, dict):
        audit_status = str(audit.get("status") or "ok").lower()
        layers["L2"] = {
            "status": "error" if audit_status in {"error", "incomplete"} else ("review" if audit.get("issues") else "pass"),
            "check_names": ["audit"],
            "failed": ["audit"] if audit.get("issues") else [],
            "finding_count": len(audit.get("issues") or []),
        }
    return layers


def build_quality_report(
     final_text: str,
     previous_text: Optional[str] = None,
     plugin_guards: Optional[list] = None,
     root_dir: Optional[Any] = None,
     mode: str = "report_only",
     style_precheck: Optional[Dict[str, Dict[str, Any]]] = None,
     audit: Optional[Dict[str, Any]] = None,
     prose_profile: Optional[Dict[str, Any]] = None,
     chapter_id: Optional[str] = None,
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

     # Prose identity is an explicit, diagnostic-only input.  Do not silently
     # create a profile from arbitrary project files and never let this signal
     # block a chapter on its own.
     if isinstance(prose_profile, dict):
         try:
             from novel_agent.quality.prose_identity import compare_prose_identity

             raw_checks["prose_identity"] = compare_prose_identity(final_text, prose_profile)
         except Exception as exc:
             logger.warning("Prose identity check failed: %s", exc)
 
     if root_dir:
         try:
             from novel_agent.quality.style_rules import check_reference_similarity
             sim_res = check_reference_similarity(final_text, Path(root_dir))
             raw_checks["reference_similarity"] = sim_res
         except Exception as exc:
             logger.warning("Reference similarity check failed: %s", exc)
         try:
             from novel_agent.quality.expression_memory import check_expression_repetition

             raw_checks["expression_repetition"] = check_expression_repetition(
                 final_text,
                 Path(root_dir),
                 chapter_id=chapter_id,
             )
         except Exception as exc:
             logger.warning("Expression repetition check failed: %s", exc)
         try:
             from novel_agent.quality.event_consistency import check_event_consistency

             raw_checks["event_consistency"] = check_event_consistency(
                 final_text,
                 Path(root_dir),
                 chapter_id=chapter_id,
                 state_update=(audit or {}).get("state_update") if isinstance(audit, dict) else None,
             )
         except Exception as exc:
             logger.warning("Event consistency check failed: %s", exc)
         if chapter_id and flag_enabled("m3_canon_engine", Path(root_dir)):
             try:
                 from novel_agent.quality.canon_engine import filter_visible_canon
                 from novel_agent.state.sqlite_store import SQLiteStateStore

                 events = SQLiteStateStore(Path(root_dir)).list_narrative_events(limit=500)
                 _visible, violations = filter_visible_canon(
                     events,
                     current_chapter=str(chapter_id),
                     known_character_ids=set(),
                 )
                 raw_checks["canon_visibility"] = {
                     "pass": not violations,
                     "score": 1.0 if not violations else 0.0,
                     "level": "none" if not violations else "fail",
                     "findings": [
                         {
                             "issue_id": f"canon:{item.code}:{item.memory_id}",
                             "type": item.code,
                             "severity": "error",
                             "action": "block",
                             "memory_id": item.memory_id,
                             "source_chapter": item.chapter_id,
                             "source_revision_id": item.source_revision_id,
                             "message": item.message,
                         }
                         for item in violations
                     ],
                 }
             except Exception as exc:
                 raw_checks["canon_visibility"] = {
                     "pass": False,
                     "score": 0.0,
                     "level": "error",
                     "status": "error",
                     "findings": [{"type": "canon_check_error", "message": str(exc), "action": "block"}],
                 }
 
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
     report = {
         "mode": resolved_mode,
         "overall_score": round(overall_score, 1),
         "overall_pass": all_passed,
         "checks": checks,
         "guard_summary": guard_summary,
     }
     report["quality_layers"] = _build_quality_layers(checks, audit=audit)

     if isinstance(audit, dict):
         status = str(audit.get("status") or "ok").strip().lower()
         incomplete = status not in {"ok", "passed", "pass", "complete"}
         report["audit"] = {
             "status": status,
             "risk_level": audit.get("risk_level"),
             "issue_count": len(audit.get("issues") or []),
         }
         if audit.get("error"):
             report["audit"]["error"] = audit.get("error")
         report["incomplete"] = incomplete
         if incomplete:
             # Report-only still exposes the incomplete state to the UI and
             # downstream automation; the mode decides whether it blocks.
             report["overall_pass"] = False
     else:
         report["incomplete"] = False

     return report
