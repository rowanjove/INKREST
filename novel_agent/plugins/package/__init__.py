"""Package verification, signing, and marketplace client for Inkrest Plugins."""

from novel_agent.plugins.package.verifier import (
    PermissionDiff,
    compute_package_hash,
    compute_permission_diff,
    sign_package,
    verify_package,
)
from novel_agent.plugins.package.marketplace import (
    MarketplaceClient,
    MarketplaceItem,
)

__all__ = [
    "PermissionDiff",
    "compute_package_hash",
    "compute_permission_diff",
    "sign_package",
    "verify_package",
    "MarketplaceClient",
    "MarketplaceItem",
]
