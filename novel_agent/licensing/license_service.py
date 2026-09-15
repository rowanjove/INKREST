"""License Management Service for INKREST (Milestone D).

Validates offline signed licenses, manages trial periods, and provisions EntitlementService.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple
import uuid

from novel_agent.licensing.crypto_signer import LicenseSigner, default_signer
from novel_agent.licensing.entitlements import EntitlementService
from novel_agent.licensing.models import (
    LicensePayload,
    LicenseTier,
    SignedLicense,
    now_iso,
)


class LicenseService:
    """Manages active license storage, offline signature verification, and trial generation."""

    def __init__(
        self,
        storage_dir: Path,
        signer: Optional[LicenseSigner] = None,
    ) -> None:
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.license_file = self.storage_dir / "license.json"
        self.signer = signer or default_signer

    def get_current_license(self) -> Optional[SignedLicense]:
        """Read and parse current license from disk."""
        if not self.license_file.is_file():
            return None
        try:
            content = self.license_file.read_text(encoding="utf-8")
            return SignedLicense.from_json(content)
        except Exception:
            return None

    def is_license_valid(self, signed_license: SignedLicense) -> Tuple[bool, str]:
        """Verify signature and expiration date."""
        # 1. Asymmetric digital signature verification
        if not self.signer.verify_license(signed_license):
            return False, "许可证数字签名无效或已被篡改"

        # 2. Expiration check
        if signed_license.payload.expires_at:
            try:
                expires_dt = datetime.fromisoformat(
                    signed_license.payload.expires_at.replace("Z", "+00:00")
                )
                now_dt = datetime.now(timezone.utc)
                if now_dt > expires_dt:
                    return False, f"许可证已于 {signed_license.payload.expires_at} 过期"
            except Exception as exc:
                return False, f"许可证过期时间解析失败: {exc}"

        return True, "许可证有效"

    def apply_license(self, license_json_str: str) -> Tuple[bool, str]:
        """Validate and apply a new license."""
        try:
            signed_license = SignedLicense.from_json(license_json_str)
        except Exception as exc:
            return False, f"许可证文件格式无效: {exc}"

        valid, msg = self.is_license_valid(signed_license)
        if not valid:
            return False, msg

        # Atomically write valid license
        temp_file = self.license_file.with_suffix(".tmp")
        temp_file.write_text(signed_license.to_json(), encoding="utf-8")
        temp_file.replace(self.license_file)

        return True, f"许可证激活成功：{signed_license.payload.tier.value.upper()} 权限"

    def start_trial(self, holder_name: str = "试用用户", days: int = 14) -> SignedLicense:
        """Start a local 14-day trial license."""
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        payload = LicensePayload(
            license_id=f"TRIAL-{uuid.uuid4().hex[:12].upper()}",
            tier=LicenseTier.TRIAL,
            holder_name=holder_name,
            issued_at=now_iso(),
            expires_at=expires_at,
        )
        signed = self.signer.sign_payload(payload)
        self.apply_license(signed.to_json())
        return signed

    def get_entitlement_service(self) -> EntitlementService:
        """Get the active EntitlementService for feature permission checks."""
        current = self.get_current_license()
        if not current:
            return EntitlementService(None)

        valid, _ = self.is_license_valid(current)
        if not valid:
            return EntitlementService(None)

        return EntitlementService(current.payload)

    def revoke_license(self) -> bool:
        """Remove active license."""
        if self.license_file.is_file():
            self.license_file.unlink()
            return True
        return False
