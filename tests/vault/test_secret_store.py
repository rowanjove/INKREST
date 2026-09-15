"""Unit tests for SecretStore (Windows DPAPI & Software fallback)."""

import platform
from pathlib import Path
import pytest

from novel_agent.vault.secret_store import (
    DPAPISecretStore,
    SoftwareSecretStore,
    get_secret_store,
)


def test_software_secret_store(tmp_path: Path):
    store_file = tmp_path / "secrets.enc"
    store = SoftwareSecretStore(store_file)

    # Empty store
    assert store.get_secret("openai_key") is None
    assert store.list_secret_keys() == []

    # Save secrets
    store.save_secret("openai_key", "sk-live-123456", provider="openai")
    store.save_secret("anthropic_key", "sk-ant-7890", provider="anthropic")

    # Read secrets
    assert store.get_secret("openai_key") == "sk-live-123456"
    assert store.get_secret("anthropic_key") == "sk-ant-7890"
    assert store.list_secret_keys() == ["anthropic_key", "openai_key"]

    # Verify encrypted on disk (not plain text)
    raw = store_file.read_bytes()
    assert b"sk-live-123456" not in raw

    # Reload in a new instance
    reloaded = SoftwareSecretStore(store_file)
    assert reloaded.get_secret("openai_key") == "sk-live-123456"

    # Delete secret
    assert reloaded.delete_secret("openai_key") is True
    assert reloaded.get_secret("openai_key") is None
    assert reloaded.list_secret_keys() == ["anthropic_key"]


@pytest.mark.skipif(platform.system() != "Windows", reason="DPAPI is Windows-only")
def test_dpapi_secret_store(tmp_path: Path):
    store_file = tmp_path / "dpapi_secrets.enc"
    store = DPAPISecretStore(store_file)

    store.save_secret("deepseek_key", "sk-ds-abcdef", provider="deepseek")
    assert store.get_secret("deepseek_key") == "sk-ds-abcdef"

    # Verify not plain text
    raw = store_file.read_bytes()
    assert b"sk-ds-abcdef" not in raw

    # Reload
    reloaded = DPAPISecretStore(store_file)
    assert reloaded.get_secret("deepseek_key") == "sk-ds-abcdef"


def test_get_secret_store_factory(tmp_path: Path):
    store = get_secret_store(tmp_path)
    if platform.system() == "Windows":
        assert isinstance(store, DPAPISecretStore)
    else:
        assert isinstance(store, SoftwareSecretStore)
