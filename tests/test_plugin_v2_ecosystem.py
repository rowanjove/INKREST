import pytest

from novel_agent.plugins.package.verifier import (
    compute_package_hash,
    compute_permission_diff,
    sign_package,
    verify_package,
)
from novel_agent.plugins.package.marketplace import (
    MarketplaceClient,
    MarketplaceItem,
)


def test_package_hash_and_signature():
    payload = b"test plugin package archive contents"
    secret_key = "inkrest_platform_secret_key"

    # 1. Test hash computation
    pkg_hash = compute_package_hash(payload)
    assert len(pkg_hash) == 64
    assert pkg_hash == compute_package_hash(payload)

    # 2. Test signing and verification
    signature = sign_package(payload, secret_key)
    assert signature.startswith("hmac-sha256:")
    assert verify_package(payload, signature, secret_key) is True

    # 3. Test tampered data fails verification
    tampered = payload + b"!"
    assert verify_package(tampered, signature, secret_key) is False

    # 4. Test wrong key fails verification
    assert verify_package(payload, signature, "wrong_secret_key") is False


def test_permission_diffing():
    # Scenario 1: Normal upgrade (safe permissions)
    old_caps = ["project_read"]
    new_caps = ["project_read", "project_catalog_read"]
    diff1 = compute_permission_diff(old_caps, new_caps)
    assert diff1.added == ["project_catalog_read"]
    assert diff1.removed == []
    assert diff1.unchanged == ["project_read"]
    assert diff1.has_escalation is False

    # Scenario 2: Privilege escalation (adding high risk permission)
    old_caps2 = ["project_read"]
    new_caps2 = ["project_read", "local_code", "project_write"]
    diff2 = compute_permission_diff(old_caps2, new_caps2)
    assert "local_code" in diff2.added
    assert "project_write" in diff2.added
    assert diff2.has_escalation is True
    assert set(diff2.escalated_permissions) == {"local_code", "project_write"}

    # Scenario 3: Permissions revoked
    old_caps3 = ["project_read", "project_write"]
    new_caps3 = ["project_read"]
    diff3 = compute_permission_diff(old_caps3, new_caps3)
    assert diff3.removed == ["project_write"]
    assert diff3.added == []
    assert diff3.has_escalation is False


def test_marketplace_client_search_and_verify():
    secret = "secret123"
    pkg1_data = b"pkg1_zip_data"
    pkg1_hash = compute_package_hash(pkg1_data)
    pkg1_sig = sign_package(pkg1_data, secret)

    sample_registry = {
        "registry_version": "2.0",
        "plugins": [
            {
                "id": "inkrest.foreshadow",
                "name": "foreshadow",
                "display_name": "伏笔追踪器",
                "description": "智能伏笔分析与回收提醒",
                "version": "1.2.0",
                "hash": pkg1_hash,
                "signature": pkg1_sig,
                "tags": ["analysis", "pipeline", "story"],
                "capabilities": ["project_read"],
            },
            {
                "id": "inkrest.grammar_checker",
                "name": "grammar_checker",
                "display_name": "错别字与语法检查器",
                "description": "深度语法纠错与文笔润色",
                "version": "0.9.0",
                "tags": ["quality", "polish"],
                "capabilities": ["project_read"],
            },
        ],
    }

    client = MarketplaceClient(sample_registry)
    assert len(client.list_items()) == 2

    # 1. Search by keyword
    res = client.search("伏笔")
    assert len(res) == 1
    assert res[0].id == "inkrest.foreshadow"

    # 2. Search by tag
    res_tag = client.search("", tag="polish")
    assert len(res_tag) == 1
    assert res_tag[0].id == "inkrest.grammar_checker"

    # 3. Verify package data integrity
    item = client.get_item("inkrest.foreshadow")
    assert item is not None
    assert client.verify_package_data(pkg1_data, item, secret) is True

    # Tampered package fails
    assert client.verify_package_data(b"bad_bytes", item, secret) is False
