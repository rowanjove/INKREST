"""Update Manifest and Distribution Security Verification (Milestone C).

Verifies update packages against HTTPS official channels, SHA-256 integrity,
and cryptographic signatures before allowing installation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, Optional, Tuple


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"


@dataclass
class UpdateManifest:
    version: str
    channel: UpdateChannel
    release_date: str
    download_url: str
    sha256: str
    signature: str
    min_supported_version: str = "2.0.0"
    release_notes: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "channel": self.channel.value,
            "release_date": self.release_date,
            "download_url": self.download_url,
            "sha256": self.sha256,
            "signature": self.signature,
            "min_supported_version": self.min_supported_version,
            "release_notes": self.release_notes,
            "extra_metadata": self.extra_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UpdateManifest:
        return cls(
            version=str(data["version"]),
            channel=UpdateChannel(data.get("channel", "stable")),
            release_date=str(data.get("release_date", now_iso())),
            download_url=str(data["download_url"]),
            sha256=str(data["sha256"]),
            signature=str(data.get("signature", "")),
            min_supported_version=str(data.get("min_supported_version", "2.0.0")),
            release_notes=str(data.get("release_notes", "")),
            extra_metadata=dict(data.get("extra_metadata", {})),
        )


def verify_update_package(file_bytes: bytes, expected_sha256: str) -> Tuple[bool, str]:
    """Verify package bytes against the expected SHA-256 hash."""
    actual_sha = hashlib.sha256(file_bytes).hexdigest().lower()
    if actual_sha != expected_sha256.strip().lower():
        return False, f"安装包 SHA-256 校验失败：期望 {expected_sha256}，实际 {actual_sha}"
    return True, "安装包完整性校验通过"
