"""INKREST Commercial Core package (Milestone D).

Provides:
- Asymmetric offline license signature verification (Ed25519)
- License & Entitlement separation
- Fine-grained capability checks (`has_entitlement`)
- Trial license provisioning
"""

from novel_agent.licensing.models import (
    LicenseTier,
    LicensePayload,
    SignedLicense,
)
from novel_agent.licensing.crypto_signer import (
    LicenseSigner,
    default_signer,
)
from novel_agent.licensing.entitlements import (
    EntitlementService,
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
)
from novel_agent.licensing.license_service import (
    LicenseService,
)

__all__ = [
    "LicenseTier",
    "LicensePayload",
    "SignedLicense",
    "LicenseSigner",
    "default_signer",
    "EntitlementService",
    "LicenseService",
    "FEATURE_AI_BATCH",
    "FEATURE_AI_AGENT",
    "FEATURE_MEMORY_ADVANCED",
    "FEATURE_QUALITY_ADVANCED",
    "FEATURE_PLUGIN",
    "FEATURE_MULTI_VAULT",
    "FEATURE_EXPORT_ADVANCED",
    "FEATURE_WORKSHOP",
    "FEATURE_TEAM_COLLABORATION",
    "FEATURE_CLOUD_SYNC",
]
