"""Data models for INKREST Licensing and Entitlements (Milestone D).

Separates Identity (who is the user), License (what license is held),
and Entitlements (what capabilities are allowed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LicenseTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    STUDIO = "studio"
    TRIAL = "trial"


@dataclass
class LicensePayload:
    license_id: str
    tier: LicenseTier
    holder_name: str
    holder_email: Optional[str] = None
    device_id: Optional[str] = None
    issued_at: str = field(default_factory=now_iso)
    expires_at: Optional[str] = None  # None for perpetual licenses
    features_override: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "license_id": self.license_id,
            "tier": self.tier.value,
            "holder_name": self.holder_name,
            "holder_email": self.holder_email,
            "device_id": self.device_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "features_override": self.features_override,
        }

    def canonical_bytes(self) -> bytes:
        """Deterministic canonical JSON bytes for signature calculation/verification."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LicensePayload:
        return cls(
            license_id=str(data["license_id"]),
            tier=LicenseTier(data.get("tier", "free")),
            holder_name=str(data.get("holder_name", "Anonymous")),
            holder_email=data.get("holder_email"),
            device_id=data.get("device_id"),
            issued_at=str(data.get("issued_at", now_iso())),
            expires_at=data.get("expires_at"),
            features_override=data.get("features_override"),
        )


@dataclass
class SignedLicense:
    payload: LicensePayload
    signature_b64: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payload": self.payload.to_dict(),
            "signature": self.signature_b64,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, json_str: str) -> SignedLicense:
        data = json.loads(json_str)
        payload = LicensePayload.from_dict(data["payload"])
        return cls(payload=payload, signature_b64=data["signature"])
