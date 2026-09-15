"""Reproducible Build and Release Metadata (Milestone C).

Provides version disclosure for About pages and diagnostics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BuildMetadata:
    app_version: str = "2.3.0"
    git_commit: str = "dev"
    build_time: str = ""
    release_channel: str = "stable"
    schema_version: int = 2
    crypto_version: int = 1
    project_format_version: int = 1
    plugin_api_version: int = 2

    def __post_init__(self):
        if not self.build_time:
            self.build_time = now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_version": self.app_version,
            "git_commit": self.git_commit,
            "build_time": self.build_time,
            "release_channel": self.release_channel,
            "schema_version": self.schema_version,
            "crypto_version": self.crypto_version,
            "project_format_version": self.project_format_version,
            "plugin_api_version": self.plugin_api_version,
        }

    @classmethod
    def get_current(cls) -> BuildMetadata:
        commit = os.environ.get("INKREST_BUILD_COMMIT", "HEAD")
        channel = os.environ.get("INKREST_RELEASE_CHANNEL", "stable")
        return cls(
            git_commit=commit,
            release_channel=channel,
        )
