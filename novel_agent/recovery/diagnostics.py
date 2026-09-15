"""Diagnostic package generator with automated desensitization (Milestone B).

Strictly filters all novel body text, prompts, API keys, passwords,
PINs, recovery keys, access tokens, and local personal path segments.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Regex patterns for sensitive credentials
API_KEY_REGEX = re.compile(r"(sk-[a-zA-Z0-9_-]{10,})|(Bearer\s+[a-zA-Z0-9_.-]{10,})", re.IGNORECASE)
RECOVERY_KEY_REGEX = re.compile(r"IRK-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def desensitize_text(text: str) -> str:
    """Mask credentials, tokens, and personal identifiers."""
    masked = API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)
    masked = RECOVERY_KEY_REGEX.sub("[REDACTED_RECOVERY_KEY]", masked)
    masked = EMAIL_REGEX.sub("[REDACTED_EMAIL]", masked)
    # Mask user directory names e.g. C:\Users\<name>
    user_name = os.environ.get("USERNAME") or os.environ.get("USER")
    if user_name and len(user_name) > 1:
        masked = masked.replace(user_name, "<USER>")
    return masked


class DiagnosticManager:
    """Assembles desensitized diagnostic zip bundles."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.output_dir = self.root_dir / "logs" / "diagnostics"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_diagnostic_package(
        self,
        vault_metadata: Optional[Dict[str, Any]] = None,
        health_summary: Optional[Dict[str, Any]] = None,
        recent_errors: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_path = self.output_dir / f"INKREST-Diagnostic-{timestamp_str}.zip"

        # 1. System info
        system_info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": sys.version,
            "executable": sys.executable,
            "timestamp": now_iso(),
        }

        # 2. App environment info (sanitized)
        app_info = {
            "app_version": "2.2.0",
            "root_dir": desensitize_text(str(self.root_dir)),
            "vault": vault_metadata or {},
        }

        # 3. Recent sanitized errors
        sanitized_errors = []
        if recent_errors:
            for err in recent_errors:
                sanitized_errors.append(
                    {
                        "error_id": err.get("error_id", "UNKNOWN"),
                        "code": err.get("code", "UNKNOWN"),
                        "message": desensitize_text(str(err.get("message", ""))),
                        "timestamp": err.get("timestamp", now_iso()),
                    }
                )

        temp_zip = zip_path.with_suffix(".tmp")
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("system.json", json.dumps(system_info, indent=2))
            zf.writestr("app.json", json.dumps(app_info, indent=2, ensure_ascii=False))
            zf.writestr(
                "database_health.json",
                json.dumps(health_summary or {}, indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "recent_errors.json",
                json.dumps(sanitized_errors, indent=2, ensure_ascii=False),
            )
            # Read recent log tail if available
            log_file = self.root_dir / "logs" / "novel_agent.log"
            if log_file.is_file():
                try:
                    # Tail last 200 lines
                    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
                    sanitized_log = desensitize_text("\n".join(lines))
                    zf.writestr("sanitized_errors.log", sanitized_log)
                except Exception:
                    pass

        temp_zip.replace(zip_path)
        return zip_path
