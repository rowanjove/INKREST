"""Vault Manager for INKREST (Milestone A).

Handles lifecycle, physical account isolation, unlocking, locking, PIN management,
and secret store association.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from novel_agent.vault.crypto import (
    b64_decode,
    b64_encode,
    derive_kek,
    derive_recovery_kek,
    generate_recovery_key,
    generate_salt,
    generate_vault_key,
    unwrap_key,
    wrap_key,
)
from novel_agent.vault.models import (
    CryptoConfig,
    SessionState,
    VaultMetadata,
    VaultStatus,
    now_iso,
)
from novel_agent.vault.secret_store import BaseSecretStore, get_secret_store


class VaultManager:
    """Manages physical Vault directories and security boundaries."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.global_dir = self.root_dir / "global"
        self.accounts_dir = self.root_dir / "accounts"
        self._unlocked_keys: Dict[str, bytes] = {}
        self._session_states: Dict[str, SessionState] = {}
        self.ensure_layout()

    def ensure_layout(self) -> None:
        """Ensure standard INKREST directory layout exists."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        install_json = self.global_dir / "install.json"
        if not install_json.exists():
            install_json.write_text(
                json.dumps(
                    {
                        "installed_at": now_iso(),
                        "app_version": "2.1.0",
                        "schema_version": 1,
                        "crypto_version": 1,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _vault_dir(self, vault_id: str) -> Path:
        return self.accounts_dir / vault_id

    def list_vaults(self) -> List[VaultMetadata]:
        """List all available vaults."""
        results: List[VaultMetadata] = []
        if not self.accounts_dir.is_dir():
            return results
        for item in sorted(self.accounts_dir.iterdir()):
            if item.is_dir():
                account_file = item / "account.json"
                if account_file.is_file():
                    try:
                        data = json.loads(account_file.read_text(encoding="utf-8"))
                        results.append(VaultMetadata.from_dict(data))
                    except Exception:
                        pass
        return results

    def get_vault(self, vault_id: str) -> Optional[VaultMetadata]:
        """Get metadata for a specific vault."""
        account_file = self._vault_dir(vault_id) / "account.json"
        if not account_file.is_file():
            return None
        try:
            data = json.loads(account_file.read_text(encoding="utf-8"))
            return VaultMetadata.from_dict(data)
        except Exception:
            return None

    def get_default_vault(self) -> Optional[VaultMetadata]:
        """Get the default local vault if one exists."""
        for vault in self.list_vaults():
            if vault.is_default:
                return vault
        vaults = self.list_vaults()
        return vaults[0] if vaults else None

    def create_vault(
        self,
        name: str,
        pin: Optional[str] = None,
        is_default: bool = False,
        vault_id: Optional[str] = None,
    ) -> Tuple[VaultMetadata, Optional[str]]:
        """Create a new vault. Returns (metadata, recovery_key_if_pin_enabled)."""
        actual_id = vault_id or str(uuid.uuid4())
        vault_path = self._vault_dir(actual_id)
        vault_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (vault_path / "projects").mkdir(exist_ok=True)
        (vault_path / "attachments").mkdir(exist_ok=True)
        (vault_path / "indexes").mkdir(exist_ok=True)
        (vault_path / "cache").mkdir(exist_ok=True)
        (vault_path / "backups").mkdir(exist_ok=True)
        (vault_path / "journals").mkdir(exist_ok=True)

        # Initialize registry.db
        registry_db = vault_path / "registry.db"
        if not registry_db.exists():
            conn = sqlite3.connect(registry_db)
            try:
                conn.execute(
                    """
                    create table if not exists vault_info (
                        key text primary key,
                        value text not null
                    )
                    """
                )
                conn.execute(
                    "insert into vault_info (key, value) values ('vault_id', ?)",
                    (actual_id,),
                )
                conn.execute(
                    "insert into vault_info (key, value) values ('created_at', ?)",
                    (now_iso(),),
                )
                conn.commit()
            finally:
                conn.close()

        raw_vault_key = generate_vault_key()
        recovery_key_str: Optional[str] = None
        pin_enabled = bool(pin and pin.strip())

        if pin_enabled:
            salt = generate_salt()
            kek = derive_kek(pin.strip(), salt)
            wrapped_key, nonce = wrap_key(kek, raw_vault_key)

            rec_key = generate_recovery_key()
            recovery_key_str = rec_key
            rec_salt = generate_salt()
            rec_kek = derive_recovery_kek(rec_key, rec_salt)
            rec_wrapped_key, rec_nonce = wrap_key(rec_kek, raw_vault_key)

            crypto_cfg = CryptoConfig(
                kdf="scrypt",
                salt_b64=b64_encode(salt),
                wrapped_vault_key_b64=b64_encode(wrapped_key),
                key_wrap_nonce_b64=b64_encode(nonce),
                recovery_wrapped_key_b64=b64_encode(rec_wrapped_key),
                recovery_nonce_b64=b64_encode(rec_nonce),
                recovery_salt_b64=b64_encode(rec_salt),
            )
            (vault_path / "crypto.json").write_text(
                json.dumps(crypto_cfg.to_dict(), indent=2), encoding="utf-8"
            )
            self._session_states[actual_id] = SessionState(
                active_vault_id=actual_id, status=VaultStatus.LOCKED
            )
        else:
            # Without PIN: vault is instantly unlocked, store key in memory
            self._unlocked_keys[actual_id] = raw_vault_key
            self._session_states[actual_id] = SessionState(
                active_vault_id=actual_id,
                status=VaultStatus.UNLOCKED,
                unlocked_at=now_iso(),
            )

        metadata = VaultMetadata(
            vault_id=actual_id,
            name=name,
            is_default=is_default,
            pin_enabled=pin_enabled,
        )
        (vault_path / "account.json").write_text(
            json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return metadata, recovery_key_str

    def unlock_vault(self, vault_id: str, pin: str) -> bool:
        """Unlock a PIN-protected vault."""
        crypto_file = self._vault_dir(vault_id) / "crypto.json"
        if not crypto_file.is_file():
            # No crypto file means not PIN protected
            self._session_states[vault_id] = SessionState(
                active_vault_id=vault_id,
                status=VaultStatus.UNLOCKED,
                unlocked_at=now_iso(),
            )
            return True

        try:
            cfg_data = json.loads(crypto_file.read_text(encoding="utf-8"))
            cfg = CryptoConfig.from_dict(cfg_data)
            salt = b64_decode(cfg.salt_b64)
            wrapped_key = b64_decode(cfg.wrapped_vault_key_b64)
            nonce = b64_decode(cfg.key_wrap_nonce_b64)

            kek = derive_kek(pin.strip(), salt, kdf=cfg.kdf)
            vault_key = unwrap_key(kek, wrapped_key, nonce)
            self._unlocked_keys[vault_id] = vault_key
            self._session_states[vault_id] = SessionState(
                active_vault_id=vault_id,
                status=VaultStatus.UNLOCKED,
                unlocked_at=now_iso(),
            )
            return True
        except Exception:
            return False

    def unlock_with_recovery_key(self, vault_id: str, recovery_key: str) -> bool:
        """Unlock using the emergency Recovery Key."""
        crypto_file = self._vault_dir(vault_id) / "crypto.json"
        if not crypto_file.is_file():
            return False
        try:
            cfg_data = json.loads(crypto_file.read_text(encoding="utf-8"))
            cfg = CryptoConfig.from_dict(cfg_data)
            if not cfg.recovery_salt_b64 or not cfg.recovery_wrapped_key_b64 or not cfg.recovery_nonce_b64:
                return False

            rec_salt = b64_decode(cfg.recovery_salt_b64)
            rec_wrapped_key = b64_decode(cfg.recovery_wrapped_key_b64)
            rec_nonce = b64_decode(cfg.recovery_nonce_b64)

            rec_kek = derive_recovery_kek(recovery_key, rec_salt)
            vault_key = unwrap_key(rec_kek, rec_wrapped_key, rec_nonce)
            self._unlocked_keys[vault_id] = vault_key
            self._session_states[vault_id] = SessionState(
                active_vault_id=vault_id,
                status=VaultStatus.UNLOCKED,
                unlocked_at=now_iso(),
            )
            return True
        except Exception:
            return False

    def change_pin(self, vault_id: str, old_pin: str, new_pin: str) -> bool:
        """Change PIN without re-encrypting vault data (re-wrap vault key)."""
        crypto_file = self._vault_dir(vault_id) / "crypto.json"
        if not crypto_file.is_file():
            return False

        try:
            cfg_data = json.loads(crypto_file.read_text(encoding="utf-8"))
            cfg = CryptoConfig.from_dict(cfg_data)

            old_salt = b64_decode(cfg.salt_b64)
            wrapped_key = b64_decode(cfg.wrapped_vault_key_b64)
            nonce = b64_decode(cfg.key_wrap_nonce_b64)

            old_kek = derive_kek(old_pin.strip(), old_salt, kdf=cfg.kdf)
            vault_key = unwrap_key(old_kek, wrapped_key, nonce)

            # Re-wrap with new PIN
            new_salt = generate_salt()
            new_kek = derive_kek(new_pin.strip(), new_salt, kdf=cfg.kdf)
            new_wrapped_key, new_nonce = wrap_key(new_kek, vault_key)

            cfg.salt_b64 = b64_encode(new_salt)
            cfg.wrapped_vault_key_b64 = b64_encode(new_wrapped_key)
            cfg.key_wrap_nonce_b64 = b64_encode(new_nonce)

            crypto_file.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
            self._unlocked_keys[vault_id] = vault_key
            return True
        except Exception:
            return False

    def lock_vault(self, vault_id: str) -> None:
        """Lock a vault and clear key from memory."""
        self._unlocked_keys.pop(vault_id, None)
        self._session_states[vault_id] = SessionState(
            active_vault_id=vault_id, status=VaultStatus.LOCKED
        )

    def get_vault_status(self, vault_id: str) -> VaultStatus:
        """Get the current locked/unlocked state of a vault."""
        metadata = self.get_vault(vault_id)
        if not metadata or not metadata.pin_enabled:
            return VaultStatus.UNLOCKED
        state = self._session_states.get(vault_id)
        return state.status if state else VaultStatus.LOCKED

    def get_vault_key(self, vault_id: str) -> Optional[bytes]:
        """Get the raw 256-bit vault key if unlocked."""
        if self.get_vault_status(vault_id) != VaultStatus.UNLOCKED:
            return None
        return self._unlocked_keys.get(vault_id)

    def get_projects_dir(self, vault_id: str) -> Path:
        """Get isolated projects directory for a vault."""
        p = self._vault_dir(vault_id) / "projects"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_secret_store(self, vault_id: str) -> BaseSecretStore:
        """Get the secret store for a specific vault."""
        return get_secret_store(self._vault_dir(vault_id))
