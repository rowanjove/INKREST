"""Unit tests for LicenseService lifecycle, trial generation, and expiration."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from novel_agent.licensing.crypto_signer import default_signer
from novel_agent.licensing.entitlements import FEATURE_AI_BATCH
from novel_agent.licensing.license_service import LicenseService
from novel_agent.licensing.models import LicensePayload, LicenseTier


def test_license_service_flow(tmp_path: Path):
    svc = LicenseService(tmp_path)

    # 1. No license = Free tier
    assert svc.get_current_license() is None
    ent = svc.get_entitlement_service()
    assert ent.get_active_tier() == LicenseTier.FREE
    assert ent.has_entitlement(FEATURE_AI_BATCH) is False

    # 2. Start Trial
    trial_lic = svc.start_trial(holder_name="体验创作者", days=14)
    assert trial_lic.payload.tier == LicenseTier.TRIAL
    assert svc.get_current_license() is not None

    ent_trial = svc.get_entitlement_service()
    assert ent_trial.get_active_tier() == LicenseTier.TRIAL
    assert ent_trial.has_entitlement(FEATURE_AI_BATCH) is True

    # 3. Apply expired license
    expired_payload = LicensePayload(
        license_id="EXP-01",
        tier=LicenseTier.PRO,
        holder_name="过期用户",
        expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )
    signed_expired = default_signer.sign_payload(expired_payload)
    ok, msg = svc.apply_license(signed_expired.to_json())
    assert ok is False
    assert "已于" in msg and "过期" in msg

    # 4. Apply perpetual Pro license
    pro_payload = LicensePayload(
        license_id="PRO-PERPETUAL-01",
        tier=LicenseTier.PRO,
        holder_name="正式专业版作者",
        expires_at=None,
    )
    signed_pro = default_signer.sign_payload(pro_payload)
    ok2, msg2 = svc.apply_license(signed_pro.to_json())
    assert ok2 is True
    assert "PRO" in msg2

    ent_pro = svc.get_entitlement_service()
    assert ent_pro.get_active_tier() == LicenseTier.PRO
    assert ent_pro.has_entitlement(FEATURE_AI_BATCH) is True

    # 5. Revoke license
    assert svc.revoke_license() is True
    assert svc.get_current_license() is None
    assert svc.get_entitlement_service().get_active_tier() == LicenseTier.FREE
