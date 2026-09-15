"""Unit tests for tier capability resolution and EntitlementService."""

from novel_agent.licensing.entitlements import (
    EntitlementService,
    FEATURE_AI_BASIC,
    FEATURE_AI_BATCH,
    FEATURE_EDITING_BASIC,
    FEATURE_PLUGIN,
    FEATURE_TEAM_COLLABORATION,
)
from novel_agent.licensing.models import LicensePayload, LicenseTier


def test_free_tier_entitlements():
    svc = EntitlementService(None)  # None defaults to FREE
    assert svc.get_active_tier() == LicenseTier.FREE
    assert svc.has_entitlement(FEATURE_EDITING_BASIC) is True
    assert svc.has_entitlement(FEATURE_AI_BASIC) is True
    assert svc.has_entitlement(FEATURE_AI_BATCH) is False
    assert svc.has_entitlement(FEATURE_PLUGIN) is False


def test_pro_tier_entitlements():
    payload = LicensePayload(
        license_id="PRO-01",
        tier=LicenseTier.PRO,
        holder_name="Pro User",
    )
    svc = EntitlementService(payload)
    assert svc.get_active_tier() == LicenseTier.PRO
    assert svc.has_entitlement(FEATURE_AI_BATCH) is True
    assert svc.has_entitlement(FEATURE_PLUGIN) is True
    assert svc.has_entitlement(FEATURE_TEAM_COLLABORATION) is False


def test_studio_tier_entitlements():
    payload = LicensePayload(
        license_id="STD-01",
        tier=LicenseTier.STUDIO,
        holder_name="Studio User",
    )
    svc = EntitlementService(payload)
    assert svc.get_active_tier() == LicenseTier.STUDIO
    assert svc.has_entitlement(FEATURE_TEAM_COLLABORATION) is True


def test_feature_override():
    # Free tier user with special beta access to plugins
    payload = LicensePayload(
        license_id="FREE-SPECIAL-01",
        tier=LicenseTier.FREE,
        holder_name="Beta User",
        features_override=[FEATURE_PLUGIN],
    )
    svc = EntitlementService(payload)
    assert svc.has_entitlement(FEATURE_AI_BASIC) is True
    assert svc.has_entitlement(FEATURE_PLUGIN) is True
    assert svc.has_entitlement(FEATURE_AI_BATCH) is False
