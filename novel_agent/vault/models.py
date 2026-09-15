"""Data models for INKREST Vault, Identity, and Security Context."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VaultStatus(str, enum.Enum):
    LOCKED = "locked"
    UNLOCKING = "unlocking"
    UNLOCKED = "unlocked"


@dataclass
class VaultMetadata:
    vault_id: str
    name: str
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    schema_version: int = 1
    crypto_version: int = 1
    is_default: bool = False
    pin_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
            "crypto_version": self.crypto_version,
            "is_default": self.is_default,
            "pin_enabled": self.pin_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VaultMetadata:
        return cls(
            vault_id=data["vault_id"],
            name=data.get("name", "Default Vault"),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
            schema_version=data.get("schema_version", 1),
            crypto_version=data.get("crypto_version", 1),
            is_default=bool(data.get("is_default", False)),
            pin_enabled=bool(data.get("pin_enabled", False)),
        )


@dataclass
class CryptoConfig:
    kdf: str  # "scrypt" or "argon2id"
    salt_b64: str
    wrapped_vault_key_b64: str
    key_wrap_nonce_b64: str
    recovery_wrapped_key_b64: Optional[str] = None
    recovery_nonce_b64: Optional[str] = None
    recovery_salt_b64: Optional[str] = None
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kdf": self.kdf,
            "salt_b64": self.salt_b64,
            "wrapped_vault_key_b64": self.wrapped_vault_key_b64,
            "key_wrap_nonce_b64": self.key_wrap_nonce_b64,
            "recovery_wrapped_key_b64": self.recovery_wrapped_key_b64,
            "recovery_nonce_b64": self.recovery_nonce_b64,
            "recovery_salt_b64": self.recovery_salt_b64,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CryptoConfig:
        return cls(
            kdf=data.get("kdf", "scrypt"),
            salt_b64=data["salt_b64"],
            wrapped_vault_key_b64=data["wrapped_vault_key_b64"],
            key_wrap_nonce_b64=data["key_wrap_nonce_b64"],
            recovery_wrapped_key_b64=data.get("recovery_wrapped_key_b64"),
            recovery_nonce_b64=data.get("recovery_nonce_b64"),
            recovery_salt_b64=data.get("recovery_salt_b64"),
            created_at=data.get("created_at", now_iso()),
        )


@dataclass
class SessionState:
    active_vault_id: Optional[str] = None
    status: VaultStatus = VaultStatus.LOCKED
    unlocked_at: Optional[str] = None
    last_active_at: Optional[str] = None
