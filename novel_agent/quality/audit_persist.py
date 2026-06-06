"""Strip internal-only fields before persisting audit JSON."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def split_audit_for_persist(audit: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Return (persistable_audit, style_rule_checks)."""
    if not isinstance(audit, dict):
        return audit, None
    checks = audit.get("style_rule_checks")
    public = {k: v for k, v in audit.items() if k != "style_rule_checks"}
    return public, checks if isinstance(checks, dict) else None