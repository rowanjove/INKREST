"""Tests for INKREST Plugin Platform 2.0 Phase 0 upgrades.

Covers:
- Version source unification (APP_VERSION, PLUGIN_API_VERSION, manifest schema)
- Plugin lifecycle state machine and diagnostics
- Transactional installation, error rollback, and version history/rollback API
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from novel_agent.plugins.installer import (
    install_plugin_zip,
    list_plugin_versions,
    rollback_plugin,
)
from novel_agent.plugins.lifecycle import (
    PluginDiagnostics,
    PluginState,
)
from novel_agent.plugins.manager import PluginManager
from novel_agent.plugins.manifest import (
    ManifestError,
    validate_manifest,
)
from novel_agent.version import (
    APP_VERSION,
    PLUGIN_API_VERSION,
    PLUGIN_MANIFEST_SCHEMA_VERSION,
)


def _make_plugin_zip(tmp: Path, plugin_id: str, version: str = "1.0.0", invalid_extract: bool = False) -> bytes:
    pkg_dir = tmp / f"pkg_{plugin_id}_{version.replace('.', '_')}"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "schema_version": PLUGIN_MANIFEST_SCHEMA_VERSION,
        "id": plugin_id,
        "version": version,
        "display_name": f"Plugin {plugin_id}",
        "description": "Phase 0 Test Plugin",
        "plugin_type": "pipeline_hook",
        "entry": "plugin:PLUGIN_CLASS",
        "engines": {
            "inkrest": f">={APP_VERSION}",
            "plugin_api": f">={PLUGIN_API_VERSION}",
        },
    }
    if invalid_extract:
        manifest_data["extract"] = [{"from": "does_not_exist.txt", "to": "../escape.txt"}]

    (pkg_dir / "inkrest.plugin.json").write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "plugin.py").write_text(
        f"""
from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType

class Hook(PipelineHookPlugin):
    def get_meta(self):
        return PluginMeta(
            name="{plugin_id}",
            version="{version}",
            plugin_type=PluginType.PIPELINE_HOOK,
        )

PLUGIN_CLASS = Hook
""".strip(),
        encoding="utf-8",
    )
    (pkg_dir / "marker.txt").write_text(f"version_{version}", encoding="utf-8")

    zpath = tmp / f"{plugin_id}_{version}.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in pkg_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(pkg_dir).as_posix())
    return zpath.read_bytes()


def test_version_unification_and_manifest_validation(tmp_path: Path) -> None:
    assert APP_VERSION
    assert PLUGIN_API_VERSION == "2.0"
    assert PLUGIN_MANIFEST_SCHEMA_VERSION == 2

    (tmp_path / "plugin.py").write_text("class P: pass\nPLUGIN_CLASS = P\n", encoding="utf-8")

    # Valid manifest specifying both inkrest and plugin_api engines
    valid_data = {
        "schema_version": 2,
        "id": "v2-plugin",
        "name": "V2 Plugin",
        "plugin_type": "command",
        "entry": "plugin:PLUGIN_CLASS",
        "version": "1.0.0",
        "engines": {
            "inkrest": f"^{APP_VERSION}",
            "plugin_api": "^2.0",
        },
    }
    normalized = validate_manifest(valid_data, tmp_path)
    assert normalized["schema_version"] == 2
    assert normalized["engines"]["plugin_api"] == "^2.0"

    # Incompatible plugin_api version rejected
    incompat_api = {
        "id": "v2-future-api",
        "name": "Future API Plugin",
        "plugin_type": "command",
        "entry": "plugin:PLUGIN_CLASS",
        "version": "1.0.0",
        "engines": {
            "plugin_api": "^9.0",
        },
    }
    with pytest.raises(ManifestError, match="插件 API 版本"):
        validate_manifest(incompat_api, tmp_path)


def test_lifecycle_state_machine_and_diagnostics() -> None:
    diag = PluginDiagnostics(plugin_id="test-plugin", status=PluginState.DISCOVERED)
    assert diag.status == PluginState.DISCOVERED
    assert diag.crash_count == 0

    # Transition to validated
    diag.transition(PluginState.VALIDATED, reason="Manifest checked")
    assert diag.status == PluginState.VALIDATED

    # Transition to active
    diag.transition(PluginState.ACTIVE, reason="Activation success")
    assert diag.status == PluginState.ACTIVE
    assert diag.active_since is not None

    # Record timeout
    diag.record_timeout("Timeout: Hook took too long")
    assert diag.timeout_count == 1
    assert "Timeout" in diag.last_error

    # Record crash
    diag.record_crash("Worker died with SIGSEGV")
    assert diag.crash_count == 1
    assert diag.status == PluginState.CRASHED

    # Serialize diagnostics
    d_dict = diag.to_dict()
    assert d_dict["status"] == "crashed"
    assert d_dict["crash_count"] == 1
    assert len(d_dict["history"]) >= 3


def test_transactional_install_and_atomic_rollback_on_failure(tmp_path: Path) -> None:
    # 1. Install version 1.0.0
    zip_v1 = _make_plugin_zip(tmp_path, "tx-plugin", version="1.0.0")
    res1 = install_plugin_zip(tmp_path, zip_v1)
    assert res1["version"] == "1.0.0"

    plugin_dir = tmp_path / "plugins" / "tx-plugin"
    assert (plugin_dir / "marker.txt").read_text(encoding="utf-8") == "version_1.0.0"

    # 2. Attempt to install version 2.0.0 which has an invalid extract path traversal
    zip_bad = _make_plugin_zip(tmp_path, "tx-plugin", version="2.0.0", invalid_extract=True)
    with pytest.raises(ManifestError):
        install_plugin_zip(tmp_path, zip_bad)

    # 3. Verify rollback: original version 1.0.0 is completely intact!
    assert plugin_dir.is_dir()
    assert (plugin_dir / "marker.txt").read_text(encoding="utf-8") == "version_1.0.0"


def test_version_archiving_and_manual_rollback(tmp_path: Path) -> None:
    # 1. Install v1.0.0
    zip_v1 = _make_plugin_zip(tmp_path, "rollback-plugin", version="1.0.0")
    install_plugin_zip(tmp_path, zip_v1)

    # 2. Upgrade to v1.1.0
    zip_v2 = _make_plugin_zip(tmp_path, "rollback-plugin", version="1.1.0")
    install_plugin_zip(tmp_path, zip_v2)

    plugin_dir = tmp_path / "plugins" / "rollback-plugin"
    assert (plugin_dir / "marker.txt").read_text(encoding="utf-8") == "version_1.1.0"

    # Check version history
    history = list_plugin_versions(tmp_path, "rollback-plugin")
    assert history["current_version"] == "1.1.0"
    assert "1.0.0" in history["archived_versions"]

    # 3. Perform rollback to v1.0.0
    rollback_res = rollback_plugin(tmp_path, "rollback-plugin", target_version="1.0.0")
    assert rollback_res["version"] == "1.0.0"
    assert (plugin_dir / "marker.txt").read_text(encoding="utf-8") == "version_1.0.0"

    # The rolled back 1.1.0 is now archived
    history_after = list_plugin_versions(tmp_path, "rollback-plugin")
    assert history_after["current_version"] == "1.0.0"
    assert "1.1.0" in history_after["archived_versions"]


def test_plugin_manager_catalog_diagnostics_and_rollback(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.yaml").write_text("llm: {provider: static}\n", encoding="utf-8")

    pm = PluginManager(tmp_path)
    zip_v1 = _make_plugin_zip(tmp_path, "catalog-diag-plugin", version="1.0.0")
    pm.install_from_zip(zip_v1)

    # Check catalog lifecycle_state and diagnostics
    catalog = pm.list_plugin_catalog()
    plugin_entry = next(p for p in catalog if p["name"] == "catalog-diag-plugin")
    assert "lifecycle_state" in plugin_entry
    assert plugin_entry["lifecycle_state"] == "trust_pending"
    assert "diagnostics" in plugin_entry

    # Upgrade via manager
    zip_v2 = _make_plugin_zip(tmp_path, "catalog-diag-plugin", version="1.2.0")
    pm.install_from_zip(zip_v2)

    versions = pm.list_plugin_versions_by_id("catalog-diag-plugin")
    assert versions["current_version"] == "1.2.0"
    assert "1.0.0" in versions["archived_versions"]

    # Rollback via manager
    roll_res = pm.rollback_plugin_by_id("catalog-diag-plugin", target_version="1.0.0")
    assert roll_res["version"] == "1.0.0"
    plugin_dir = tmp_path / "plugins" / "catalog-diag-plugin"
    assert (plugin_dir / "marker.txt").read_text(encoding="utf-8") == "version_1.0.0"
