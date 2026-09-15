"""Cryptographic signer and verifier for INKREST Offline Licenses (Milestone D).

Uses Ed25519 asymmetric cryptography.
Offline verification only requires the public key, ensuring users can use INKREST
completely disconnected from the internet.
"""

from __future__ import annotations

import base64
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

from novel_agent.licensing.models import LicensePayload, SignedLicense


# Default embedded public key for INKREST software license verification
# In production, the private key is held securely on the license issue server.
# This test pair is used for development, testing, and initial commercial readiness.
_DEFAULT_TEST_PRIVATE_KEY_BYTES = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
)
_DEFAULT_TEST_PUBLIC_KEY_BYTES = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)


class LicenseSigner:
    """Signs and verifies licenses using Ed25519."""

    def __init__(
        self,
        public_key_bytes: bytes = _DEFAULT_TEST_PUBLIC_KEY_BYTES,
        private_key_bytes: bytes | None = None,
    ) -> None:
        self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        self.private_key = (
            ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            if private_key_bytes
            else None
        )

    def sign_payload(self, payload: LicensePayload) -> SignedLicense:
        """Sign a license payload. Requires private key."""
        if not self.private_key:
            raise RuntimeError("Private key is required to sign a license.")
        canonical = payload.canonical_bytes()
        signature = self.private_key.sign(canonical)
        sig_b64 = base64.b64encode(signature).decode("ascii")
        return SignedLicense(payload=payload, signature_b64=sig_b64)

    def verify_license(self, signed_license: SignedLicense) -> bool:
        """Verify the signature of a signed license using the public key."""
        try:
            signature = base64.b64decode(signed_license.signature_b64.encode("ascii"))
            canonical = signed_license.payload.canonical_bytes()
            self.public_key.verify(signature, canonical)
            return True
        except Exception:
            return False

    @classmethod
    def generate_keypair(cls) -> Tuple[bytes, bytes]:
        """Generate a new Ed25519 (private_key_bytes, public_key_bytes) pair."""
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        from cryptography.hazmat.primitives import serialization

        priv_bytes = priv.private_bytes_raw()
        pub_bytes = pub.public_bytes_raw()
        return priv_bytes, pub_bytes


# Singleton verifier with default key
default_signer = LicenseSigner(
    public_key_bytes=_DEFAULT_TEST_PUBLIC_KEY_BYTES,
    private_key_bytes=_DEFAULT_TEST_PRIVATE_KEY_BYTES,
)
