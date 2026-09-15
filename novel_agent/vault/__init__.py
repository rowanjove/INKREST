"""INKREST Vault & Identity package (Milestone A)."""

from novel_agent.vault.models import (
    VaultStatus,
    VaultMetadata,
    CryptoConfig,
    SessionState,
)
from novel_agent.vault.crypto import (
    generate_vault_key,
    generate_recovery_key,
)
from novel_agent.vault.secret_store import (
    BaseSecretStore,
    get_secret_store,
)
from novel_agent.vault.manager import VaultManager
from novel_agent.vault.migration import migrate_legacy_workspace

__all__ = [
    "VaultStatus",
    "VaultMetadata",
    "CryptoConfig",
    "SessionState",
    "generate_vault_key",
    "generate_recovery_key",
    "BaseSecretStore",
    "get_secret_store",
    "VaultManager",
    "migrate_legacy_workspace",
]
