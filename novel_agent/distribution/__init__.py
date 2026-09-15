"""INKREST Distribution and Update package (Milestone C)."""

from novel_agent.distribution.manifest import (
    UpdateChannel,
    UpdateManifest,
    verify_update_package,
)
from novel_agent.distribution.build_info import (
    BuildMetadata,
)

__all__ = [
    "UpdateChannel",
    "UpdateManifest",
    "verify_update_package",
    "BuildMetadata",
]
