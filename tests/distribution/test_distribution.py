"""Unit tests for UpdateManifest and package SHA-256 verification."""

import hashlib
from novel_agent.distribution.manifest import (
    UpdateChannel,
    UpdateManifest,
    verify_update_package,
)
from novel_agent.distribution.build_info import BuildMetadata


def test_update_manifest_and_sha_verification():
    mock_installer = b"MOCK_INKREST_WINDOWS_INSTALLER_V2_3_0"
    actual_sha = hashlib.sha256(mock_installer).hexdigest()

    manifest = UpdateManifest(
        version="2.3.0",
        channel=UpdateChannel.STABLE,
        release_date="2026-09-15T18:00:00Z",
        download_url="https://github.com/rowanjove/inkrest/releases/download/v2.3.0/Inkrest-Setup.exe",
        sha256=actual_sha,
        signature="ed25519_sig_mock",
        release_notes="1. 新增安全恢复中心\n2. 新增离线商业授权",
    )

    data = manifest.to_dict()
    assert data["version"] == "2.3.0"
    assert data["channel"] == "stable"

    # Reconstruct
    reloaded = UpdateManifest.from_dict(data)
    assert reloaded.version == "2.3.0"

    # Verify package passes
    ok, msg = verify_update_package(mock_installer, actual_sha)
    assert ok is True

    # Verify tampered package fails
    tampered_bytes = b"CORRUPTED_INSTALLER_BYTES"
    ok2, msg2 = verify_update_package(tampered_bytes, actual_sha)
    assert ok2 is False
    assert "校验失败" in msg2


def test_build_metadata():
    info = BuildMetadata.get_current()
    assert info.app_version == "2.3.0"
    assert info.release_channel in ("stable", "beta")
    assert info.schema_version == 2
