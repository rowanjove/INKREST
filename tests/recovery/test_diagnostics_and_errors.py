"""Unit tests for DiagnosticManager desensitization and Error ID generation."""

import zipfile
from pathlib import Path
from novel_agent.recovery.diagnostics import DiagnosticManager, desensitize_text
from novel_agent.errors.error_id import generate_error_id, UserFacingError
from novel_agent.errors.codes import ErrorCode


def test_desensitization_rules():
    raw_text = "User ryan called api with key sk-live-1234567890abcdef and contact ryan@example.com, recovery IRK-ABCD-EFGH-JKLM-NPQR-STUV"
    cleaned = desensitize_text(raw_text)
    assert "sk-live-" not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned
    assert "ryan@example.com" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "IRK-ABCD" not in cleaned
    assert "[REDACTED_RECOVERY_KEY]" in cleaned


def test_diagnostic_package_generation(tmp_path: Path):
    mgr = DiagnosticManager(tmp_path)
    pkg = mgr.generate_diagnostic_package(
        vault_metadata={"name": "My Space"},
        health_summary={"status": "healthy"},
        recent_errors=[
            {
                "error_id": "INK-E-12345",
                "code": "LLM_AUTH",
                "message": "Auth failed with key sk-secret-abcdefghijk",
            }
        ],
    )
    assert pkg.is_file()
    assert pkg.name.startswith("INKREST-Diagnostic-")

    with zipfile.ZipFile(pkg, "r") as zf:
        names = set(zf.namelist())
        assert "system.json" in names
        assert "app.json" in names
        assert "recent_errors.json" in names

        # Check errors are desensitized
        err_content = zf.read("recent_errors.json").decode("utf-8")
        assert "sk-secret-" not in err_content
        assert "[REDACTED_API_KEY]" in err_content


def test_user_facing_error_formatting():
    err_id = generate_error_id()
    assert err_id.startswith("INK-E-")
    assert len(err_id) >= 9

    exc = ValueError("Invalid token sk-1234567890")
    user_err = UserFacingError.from_exception(exc, code=ErrorCode.LLM_AUTH)
    assert user_err.error_id.startswith("INK-E-")
    assert user_err.error_code == ErrorCode.LLM_AUTH
    assert user_err.user_action == "fix_model_auth"
    assert "ValueError" in (user_err.technical_details or "")
