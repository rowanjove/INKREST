"""Unit tests for Ed25519 offline license signature and verification."""

from novel_agent.licensing.crypto_signer import LicenseSigner, default_signer
from novel_agent.licensing.models import LicensePayload, LicenseTier


def test_sign_and_verify_license():
    payload = LicensePayload(
        license_id="LIC-TEST-001",
        tier=LicenseTier.PRO,
        holder_name="栖墨创作者",
        holder_email="author@inkrest.io",
    )
    signed = default_signer.sign_payload(payload)
    assert signed.signature_b64 is not None

    # Verification passes
    assert default_signer.verify_license(signed) is True

    # Tampering with payload fails verification
    tampered_payload = LicensePayload(
        license_id="LIC-TEST-001",
        tier=LicenseTier.STUDIO,  # Changed tier
        holder_name="栖墨创作者",
        holder_email="author@inkrest.io",
    )
    signed.payload = tampered_payload
    assert default_signer.verify_license(signed) is False


def test_independent_keypair_rejection():
    priv2, pub2 = LicenseSigner.generate_keypair()
    signer2 = LicenseSigner(public_key_bytes=pub2, private_key_bytes=priv2)

    payload = LicensePayload(
        license_id="LIC-TEST-002",
        tier=LicenseTier.PRO,
        holder_name="独立作者",
    )
    signed_by_2 = signer2.sign_payload(payload)

    # Valid under signer2
    assert signer2.verify_license(signed_by_2) is True

    # Invalid under default_signer (different public key)
    assert default_signer.verify_license(signed_by_2) is False
