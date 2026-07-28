from typing import Any, Dict

VALID_ISSUE_LAYERS = {"plan", "text", "state", "risk"}
VALID_SEVERITY_LEVELS = {"low", "medium", "high"}


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

