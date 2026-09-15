"""Package verification, cryptographic signing, and permission diffing."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
from typing import List, Set


HIGH_RISK_PERMISSIONS = {
    "local_code",
    "project_write",
    "web_routes",
    "model_access",
    "storage_write",
}


@dataclass
class PermissionDiff:
    """Represents differences between two versions of capability grants."""
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    has_escalation: bool = False
    escalated_permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "unchanged": self.unchanged,
            "has_escalation": self.has_escalation,
            "escalated_permissions": self.escalated_permissions,
        }


def compute_package_hash(data: bytes) -> str:
    """Compute SHA-256 hex digest of binary plugin package."""
    return hashlib.sha256(data).hexdigest()


def sign_package(data: bytes, secret_key: str) -> str:
    """Generate HMAC-SHA256 signature for binary plugin package."""
    key_bytes = secret_key.encode("utf-8")
    sig = hmac.new(key_bytes, data, hashlib.sha256).hexdigest()
    return f"hmac-sha256:{sig}"


def verify_package(data: bytes, signature: str, secret_key: str) -> bool:
    """Verify HMAC-SHA256 signature of binary plugin package."""
    if not signature or not secret_key:
        return False

    prefix = "hmac-sha256:"
    expected_sig = signature[len(prefix):] if signature.startswith(prefix) else signature
    key_bytes = secret_key.encode("utf-8")
    actual_sig = hmac.new(key_bytes, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(actual_sig, expected_sig)


def compute_permission_diff(
    old_capabilities: List[str],
    new_capabilities: List[str],
) -> PermissionDiff:
    """Compute permission diff between two versions of a plugin."""
    old_set: Set[str] = set(old_capabilities or [])
    new_set: Set[str] = set(new_capabilities or [])

    added = sorted(list(new_set - old_set))
    removed = sorted(list(old_set - new_set))
    unchanged = sorted(list(old_set & new_set))

    escalated = [cap for cap in added if cap in HIGH_RISK_PERMISSIONS]
    has_escalation = len(escalated) > 0

    return PermissionDiff(
        added=added,
        removed=removed,
        unchanged=unchanged,
        has_escalation=has_escalation,
        escalated_permissions=escalated,
    )
