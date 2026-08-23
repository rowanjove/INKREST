from typing import Any, Dict

VALID_ISSUE_LAYERS = {"plan", "text", "state", "risk"}
VALID_SEVERITY_LEVELS = {"low", "medium", "high"}


def build_audit_error(exc: BaseException, *, stage: str = "audit") -> Dict[str, Any]:
    """Return an explicit, non-passing audit result for failed validation/provider calls.

    Audit failures must never be represented as a low-risk empty report.  The shape
    intentionally keeps the legacy fields so downstream readers can render the
    report, while ``status=error`` gives the quality gate a fail-closed signal.
    Exception details are bounded and stored as a diagnostic string rather than
    copying arbitrary provider payloads into the report.
    """

    message = str(exc).strip().replace("\x00", " ")
    if len(message) > 240:
        message = message[:237] + "..."
    issue = {
        "type": "audit_error",
        "issue_layer": "risk",
        "audit_class": "CRITICAL",
        "severity": "high",
        "text": f"{stage} 未完成",
        "why": message or exc.__class__.__name__,
        "fix": "修复审校器或模型调用后重新运行审校。",
    }
    return {
        "status": "error",
        "risk_level": "unknown",
        "issues": [issue],
        "state_update": {},
        "narrative_hooks": [],
        "audit_classification": {"CRITICAL": [issue], "WARNING": [], "INFO": []},
        "error": {"stage": stage, "type": exc.__class__.__name__, "message": message},
    }


def validate_audit_report(report: Dict[str, Any]) -> Dict[str, Any]:
    required = {
        "risk_level": str,
        "issues": list,
        "state_update": dict,
    }
    for key, expected_type in required.items():
        if key not in report:
            raise ValueError(f"audit report missing required field: {key}")
        if not isinstance(report[key], expected_type):
            raise ValueError(
                f"audit report field {key} must be {expected_type.__name__}"
            )
    if report["risk_level"] not in {"低", "中", "高"}:
        raise ValueError("audit report risk_level must be one of: 低, 中, 高")

    # Validate issues structure
    for i, issue in enumerate(report["issues"]):
        if not isinstance(issue, dict):
            raise ValueError(f"issue[{i}] must be a dict, got {type(issue).__name__}")

        # Validate required issue fields
        if "type" not in issue:
            raise ValueError(f"issue[{i}] missing required field 'type'")
        if "severity" not in issue:
            raise ValueError(f"issue[{i}] missing required field 'severity'")

        # Validate severity
        severity = issue.get("severity")
        if severity not in VALID_SEVERITY_LEVELS:
            raise ValueError(
                f"issue[{i}].severity must be one of: {VALID_SEVERITY_LEVELS}, got: {severity}"
            )

        # Validate issue_layer
        layer = issue.get("issue_layer")
        if layer is not None and layer not in VALID_ISSUE_LAYERS:
            raise ValueError(
                f"issue[{i}].issue_layer must be one of: {VALID_ISSUE_LAYERS}, got: {layer}"
            )

    # Validate state_update structure
    state_update = report["state_update"]
    if "events" in state_update and not isinstance(state_update["events"], list):
        raise ValueError("state_update.events must be a list")

    return report
