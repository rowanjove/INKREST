"""Fine-grained Entitlement system for INKREST (Milestone D).

Prevents scattered `if is_pro` checks across UI and business code.
All feature gating must query: `entitlement_service.has_entitlement('feature.xxx')`.
"""

from __future__ import annotations

from typing import Dict, List, Set

from novel_agent.licensing.models import LicensePayload, LicenseTier


# Standard feature identifiers
FEATURE_EDITING_BASIC = "feature.editing.basic"
FEATURE_AI_BASIC = "feature.ai.basic"
FEATURE_AI_BATCH = "feature.ai.batch"
FEATURE_AI_AGENT = "feature.ai.agent"
FEATURE_MEMORY_ADVANCED = "feature.memory.advanced"
FEATURE_QUALITY_ADVANCED = "feature.quality.advanced"
FEATURE_PLUGIN = "feature.plugin"
FEATURE_MULTI_VAULT = "feature.multi_vault"
FEATURE_EXPORT_ADVANCED = "feature.export.advanced"
FEATURE_WORKSHOP = "feature.workshop"
FEATURE_TEAM_COLLABORATION = "feature.team.collaboration"
FEATURE_CLOUD_SYNC = "feature.cloud_sync"


DEFAULT_TIER_ENTITLEMENTS: Dict[LicenseTier, Set[str]] = {
    LicenseTier.FREE: {
        FEATURE_EDITING_BASIC,
        FEATURE_AI_BASIC,
    },
    LicenseTier.TRIAL: {
        FEATURE_EDITING_BASIC,
        FEATURE_AI_BASIC,
        FEATURE_AI_BATCH,
        FEATURE_AI_AGENT,
        FEATURE_MEMORY_ADVANCED,
        FEATURE_QUALITY_ADVANCED,
        FEATURE_PLUGIN,
        FEATURE_MULTI_VAULT,
        FEATURE_EXPORT_ADVANCED,
        FEATURE_WORKSHOP,
    },
    LicenseTier.PRO: {
        FEATURE_EDITING_BASIC,
        FEATURE_AI_BASIC,
        FEATURE_AI_BATCH,
        FEATURE_AI_AGENT,
        FEATURE_MEMORY_ADVANCED,
        FEATURE_QUALITY_ADVANCED,
        FEATURE_PLUGIN,
        FEATURE_MULTI_VAULT,
        FEATURE_EXPORT_ADVANCED,
        FEATURE_WORKSHOP,
    },
    LicenseTier.STUDIO: {
        FEATURE_EDITING_BASIC,
        FEATURE_AI_BASIC,
        FEATURE_AI_BATCH,
        FEATURE_AI_AGENT,
        FEATURE_MEMORY_ADVANCED,
        FEATURE_QUALITY_ADVANCED,
        FEATURE_PLUGIN,
        FEATURE_MULTI_VAULT,
        FEATURE_EXPORT_ADVANCED,
        FEATURE_WORKSHOP,
        FEATURE_TEAM_COLLABORATION,
        FEATURE_CLOUD_SYNC,
    },
}


class EntitlementService:
    """Evaluates active capabilities based on the active license payload."""

    def __init__(self, license_payload: LicensePayload | None = None) -> None:
        self.payload = license_payload
        self.tier = license_payload.tier if license_payload else LicenseTier.FREE

    def get_active_tier(self) -> LicenseTier:
        return self.tier

    def list_entitlements(self) -> List[str]:
        base_set = set(DEFAULT_TIER_ENTITLEMENTS.get(self.tier, set()))
        if self.payload and self.payload.features_override:
            base_set.update(self.payload.features_override)
        return sorted(base_set)

    def has_entitlement(self, feature_id: str) -> bool:
        """Query whether a specific feature is unlocked."""
        if self.payload and self.payload.features_override:
            if feature_id in self.payload.features_override:
                return True
        allowed = DEFAULT_TIER_ENTITLEMENTS.get(self.tier, set())
        return feature_id in allowed
