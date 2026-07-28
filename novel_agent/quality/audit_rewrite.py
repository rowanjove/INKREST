"""Helpers for deciding when audit output should trigger rewrite loops."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def _issue_severity(issue: Dict[str, Any]) -> str:
    return str(issue.get("severity") or issue.get("level") or "").strip().lower()


def _ai_flavor_issue_requires_rewrite(issue: Dict[str, Any], *, strict_gate: bool) -> bool:
    if str(issue.get("type") or "") != "ai_flavor":
        return False
    sev = _issue_severity(issue)
    if sev in ("high", "高", "fail"):
        return True
    if strict_gate and sev in ("medium", "中", "review", "warning"):
        return True
    return False


def audit_requires_rewrite(
    audit: Dict[str, Any],
    *,
    root_dir: Optional[Path] = None,
    quality_mode: Optional[str] = None,
) -> bool:
    """True when chapter text should enter the adaptive rewrite loop."""
    if not isinstance(audit, dict):
        return False

    strict_gate = False
    if quality_mode:
        strict_gate = quality_mode == "block_on_fail"
    elif root_dir is not None:
        from novel_agent.quality.settings import resolve_quality_mode

        strict_gate = resolve_quality_mode(Path(root_dir)) == "block_on_fail"

    risk = str(audit.get("risk_level", "")).strip().lower()
    if risk in ("高", "high", "高风险"):
        return True

    classification = audit.get("audit_classification")
    if isinstance(classification, dict):
        critical = classification.get("CRITICAL") or []
        if isinstance(critical, list) and critical:
            return True

    for issue in audit.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        if issue.get("audit_class") == "CRITICAL":
            return True
        if _ai_flavor_issue_requires_rewrite(issue, strict_gate=strict_gate):
            return True

    if strict_gate:
        flavor = audit.get("ai_flavor") or {}
        if isinstance(flavor, dict):
            risk_level = str(flavor.get("risk_level") or "").strip()
            if risk_level in ("高", "中", "high", "medium"):
                return True
    return False