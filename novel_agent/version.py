"""Unified version definitions for INKREST Novel Agent.

Single source of truth for:
- APP_VERSION: Core application version (read from root VERSION or fallback)
- PLUGIN_API_VERSION: Supported plugin API version (e.g., '2.0')
- PLUGIN_MANIFEST_SCHEMA_VERSION: Current plugin manifest schema version (e.g., 2)
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VERSION_FILE = _ROOT / "VERSION"


def get_app_version() -> str:
    """Read application version from root VERSION file."""
    if _VERSION_FILE.is_file():
        try:
            v = _VERSION_FILE.read_text(encoding="utf-8").strip()
            if v:
                return v
        except OSError:
            pass
    return "2.1.0"


APP_VERSION: str = get_app_version()
PLUGIN_API_VERSION: str = "2.0"
PLUGIN_MANIFEST_SCHEMA_VERSION: int = 2
