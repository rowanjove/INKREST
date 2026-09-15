"""Secure storage for API Keys and Secrets (Milestone A).

Uses Windows DPAPI (CryptProtectData/CryptUnprotectData) when available on Windows,
with fallback to machine-keyed AES-256-GCM software encryption for cross-platform/dev.
"""

from __future__ import annotations

import abc
import base64
import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class BaseSecretStore(abc.ABC):
    """Abstract interface for storing sensitive credentials."""

    @abc.abstractmethod
    def save_secret(self, key: str, value: str, provider: str = "") -> None:
        """Store or update a secret."""
        pass

    @abc.abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key. Returns None if not found."""
        pass

    @abc.abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Delete a secret. Returns True if deleted, False if not found."""
        pass

    @abc.abstractmethod
    def list_secret_keys(self) -> List[str]:
        """List all known secret keys (without returning secrets)."""
        pass


if platform.system() == "Windows":
    import ctypes.wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    def _dpapi_protect(data: bytes, description: str = "INKREST Secret") -> bytes:
        blob_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_byte)),
        )
        blob_out = _DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), description, None, None, None, 0, ctypes.byref(blob_out)
        ):
            raise RuntimeError("Windows DPAPI CryptProtectData failed.")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def _dpapi_unprotect(data: bytes) -> bytes:
        blob_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_byte)),
        )
        blob_out = _DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            raise RuntimeError("Windows DPAPI CryptUnprotectData failed.")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)


class DPAPISecretStore(BaseSecretStore):
    """Stores secrets in an encrypted JSON file protected by Windows DPAPI."""

    def __init__(self, store_file: Path) -> None:
        self.store_file = Path(store_file)
        self.store_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Dict[str, str]]:
        if not self.store_file.is_file() or self.store_file.stat().st_size == 0:
            return {}
        raw_bytes = self.store_file.read_bytes()
        try:
            decrypted = _dpapi_unprotect(raw_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

    def _save(self, data: Dict[str, Dict[str, str]]) -> None:
        raw_json = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        protected = _dpapi_protect(raw_json)
        # Atomic write
        temp_file = self.store_file.with_suffix(".tmp")
        temp_file.write_bytes(protected)
        temp_file.replace(self.store_file)

    def save_secret(self, key: str, value: str, provider: str = "") -> None:
        data = self._load()
        data[key] = {
            "value": value,
            "provider": provider,
        }
        self._save(data)

    def get_secret(self, key: str) -> Optional[str]:
        data = self._load()
        entry = data.get(key)
        return entry.get("value") if entry else None

    def delete_secret(self, key: str) -> bool:
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

    def list_secret_keys(self) -> List[str]:
        data = self._load()
        return sorted(data.keys())


class SoftwareSecretStore(BaseSecretStore):
    """Fallback encrypted store using AES-256-GCM with machine-derived key."""

    def __init__(self, store_file: Path) -> None:
        self.store_file = Path(store_file)
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        # Machine-local seed (fallback)
        machine_seed = f"{platform.node()}-{platform.machine()}-{os.environ.get('USERNAME', 'inkrest')}"
        self._key = hashlib.sha256(machine_seed.encode("utf-8")).digest()

    def _load(self) -> Dict[str, Dict[str, str]]:
        if not self.store_file.is_file() or self.store_file.stat().st_size < 12:
            return {}
        blob = self.store_file.read_bytes()
        nonce, ciphertext = blob[:12], blob[12:]
        try:
            aesgcm = AESGCM(self._key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

    def _save(self, data: Dict[str, Dict[str, str]]) -> None:
        raw_json = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, raw_json, None)
        temp_file = self.store_file.with_suffix(".tmp")
        temp_file.write_bytes(nonce + ciphertext)
        temp_file.replace(self.store_file)

    def save_secret(self, key: str, value: str, provider: str = "") -> None:
        data = self._load()
        data[key] = {
            "value": value,
            "provider": provider,
        }
        self._save(data)

    def get_secret(self, key: str) -> Optional[str]:
        data = self._load()
        entry = data.get(key)
        return entry.get("value") if entry else None

    def delete_secret(self, key: str) -> bool:
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

    def list_secret_keys(self) -> List[str]:
        data = self._load()
        return sorted(data.keys())


def get_secret_store(store_dir: Path) -> BaseSecretStore:
    """Return DPAPISecretStore on Windows, otherwise SoftwareSecretStore."""
    store_file = Path(store_dir) / "secrets.enc"
    if platform.system() == "Windows":
        return DPAPISecretStore(store_file)
    return SoftwareSecretStore(store_file)
