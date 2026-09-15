"""Unit tests for Vault Crypto, PIN KEK derivation, and Recovery Key."""

import pytest
from novel_agent.vault.crypto import (
    derive_kek,
    derive_recovery_kek,
    generate_recovery_key,
    generate_salt,
    generate_vault_key,
    normalize_recovery_key,
    unwrap_key,
    wrap_key,
)


def test_vault_key_wrapping_and_unwrapping():
    vault_key = generate_vault_key()
    assert len(vault_key) == 32

    salt = generate_salt()
    pin = "123456"

    kek = derive_kek(pin, salt)
    assert len(kek) == 32

    wrapped_key, nonce = wrap_key(kek, vault_key)
    assert wrapped_key != vault_key
    assert len(nonce) == 12

    # Correct unwrap
    recovered_key = unwrap_key(kek, wrapped_key, nonce)
    assert recovered_key == vault_key

    # Wrong PIN unwrap fails
    wrong_kek = derive_kek("654321", salt)
    with pytest.raises(ValueError, match="decryption failed"):
        unwrap_key(wrong_kek, wrapped_key, nonce)


def test_recovery_key_lifecycle():
    vault_key = generate_vault_key()
    rec_key = generate_recovery_key()
    assert rec_key.startswith("IRK-")
    assert len(rec_key.split("-")) == 6  # IRK + 5 groups

    rec_salt = generate_salt()
    rec_kek = derive_recovery_kek(rec_key, rec_salt)
    wrapped_key, nonce = wrap_key(rec_kek, vault_key)

    # Unwrap with normalized input (lowercase, spaces, etc.)
    user_input = rec_key.lower().replace("-", " ")
    user_kek = derive_recovery_kek(user_input, rec_salt)
    recovered = unwrap_key(user_kek, wrapped_key, nonce)
    assert recovered == vault_key

    # Wrong recovery key fails
    bad_kek = derive_recovery_kek("IRK-AAAA-BBBB-CCCC-DDDD-EEEE", rec_salt)
    with pytest.raises(ValueError):
        unwrap_key(bad_kek, wrapped_key, nonce)


def test_pin_change_rewraps_without_changing_vault_key():
    vault_key = generate_vault_key()

    old_pin = "1111"
    old_salt = generate_salt()
    old_kek = derive_kek(old_pin, old_salt)
    wrapped_key, nonce = wrap_key(old_kek, vault_key)

    # Change to new PIN: unwrap with old, wrap with new
    recovered_vault_key = unwrap_key(old_kek, wrapped_key, nonce)
    new_pin = "8888"
    new_salt = generate_salt()
    new_kek = derive_kek(new_pin, new_salt)
    new_wrapped_key, new_nonce = wrap_key(new_kek, recovered_vault_key)

    # Verify new PIN unlocks same vault key
    final_key = unwrap_key(new_kek, new_wrapped_key, new_nonce)
    assert final_key == vault_key
