"""Cryptographic utilities for INKREST Vault.

Implements two-layer key architecture:
1. 256-bit random Vault Key (used to encrypt vault data).
2. Key Encryption Key (KEK) derived from PIN + Salt via scrypt (or Argon2id if available).
3. The KEK wraps the Vault Key using AES-256-GCM.
4. An optional Recovery Key can also wrap the same Vault Key.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


RECOVERY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Base32 without ambiguous chars (0, 1, I, O)


def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64_decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def generate_vault_key() -> bytes:
    """Generate a random 256-bit Vault Key."""
    return secrets.token_bytes(32)


def generate_salt(length: int = 16) -> bytes:
    """Generate a random salt."""
    return os.urandom(length)


def derive_kek(pin: str, salt: bytes, kdf: str = "scrypt") -> bytes:
    """Derive a 256-bit Key Encryption Key (KEK) from PIN and salt."""
    pin_bytes = pin.encode("utf-8")
    if kdf == "scrypt":
        # standard interactive scrypt parameters
        return hashlib.scrypt(
            password=pin_bytes,
            salt=salt,
            n=16384,
            r=8,
            p=1,
            maxmem=32 * 1024 * 1024,
            dklen=32,
        )
    # fallback to PBKDF2 if scrypt not supported
    return hashlib.pbkdf2_hmac("sha256", pin_bytes, salt, 100000, 32)


def generate_recovery_key() -> str:
    """Generate a human-readable recovery key like IRK-XXXX-XXXX-XXXX-XXXX-XXXX."""
    groups = []
    for _ in range(5):
        group = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(4))
        groups.append(group)
    return f"IRK-{'-'.join(groups)}"


def normalize_recovery_key(key: str) -> str:
    """Clean and normalize a recovery key for derivation."""
    cleaned = key.strip().upper().replace("-", "").replace(" ", "")
    if cleaned.startswith("IRK"):
        cleaned = cleaned[3:]
    return cleaned


def derive_recovery_kek(recovery_key: str, salt: bytes) -> bytes:
    """Derive a KEK from a recovery key."""
    normalized = normalize_recovery_key(recovery_key).encode("utf-8")
    return hashlib.scrypt(
        password=normalized,
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
        dklen=32,
    )


def wrap_key(kek: bytes, raw_key: bytes) -> Tuple[bytes, bytes]:
    """Wrap raw_key using kek with AES-256-GCM. Returns (ciphertext_with_tag, nonce)."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(kek)
    ciphertext = aesgcm.encrypt(nonce, raw_key, None)
    return ciphertext, nonce


def unwrap_key(kek: bytes, wrapped_key: bytes, nonce: bytes) -> bytes:
    """Unwrap wrapped_key using kek with AES-256-GCM. Raises ValueError on failure."""
    aesgcm = AESGCM(kek)
    try:
        return aesgcm.decrypt(nonce, wrapped_key, None)
    except Exception as exc:
        raise ValueError("Invalid key or corrupted data (decryption failed)") from exc
