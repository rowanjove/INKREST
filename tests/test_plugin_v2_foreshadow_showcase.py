"""Showcase test for Foreshadow Inspector on INKREST Plugin Platform 2.0."""

from __future__ import annotations

from pathlib import Path
import pytest

from novel_agent.plugins.contributions import ContributionRegistry
from novel_agent.plugins.manifest import load_manifest, validate_manifest
from novel_agent.plugins.testing import PluginTestHost
from plugins.foreshadow_inspector.plugin import ForeshadowInspector, ForeshadowService


def test_foreshadow_manifest_v2_validation() -> None:
    plugin_dir = Path("plugins/foreshadow_inspector")
    manifest = load_manifest(plugin_dir)

    assert manifest["id"] == "inkrest.foreshadow-inspector"
    assert manifest["schema_version"] == 2
    assert "project_read" in manifest["capabilities"]
    assert "model_access" in manifest["capabilities"]

    # Test static contribution extraction
    contributions = ContributionRegistry()
    contributions.load_from_manifest(manifest["id"], manifest.get("contributes", {}))

    assert "inkrest.foreshadow-inspector.foreshadow.scan" in contributions.commands
    assert "inkrest.foreshadow-inspector.foreshadow.consistency" in contributions.validators
    assert "inkrest.foreshadow-inspector.foreshadow.sidebar" in contributions.views


def test_foreshadow_inspector_execution_with_test_host(tmp_path: Path) -> None:
    host = PluginTestHost(root_dir=tmp_path)
    # Seed mock project data
    host.project.add_chapter("001", "第一章 初始", "林澈从怀中摸出一枚带裂纹的古旧玉佩。")

    plugin = ForeshadowInspector()
    ctx = host.activate_plugin(
        plugin,
        granted_capabilities=["project_read", "model_access"],
    )
    # Inject service registry onto ctx
    ctx.services = host.services
    plugin.on_activate(ctx)

    # 1. Execute command scan
    scan_result = plugin.scan_foreshadows("demo_novel")
    assert scan_result["total_found"] == 2
    assert len(scan_result["items"]) == 2

    # 2. Execute consistency check
    issues = plugin.check_consistency("林澈手中的玉佩忽然碎裂开来，散发出一缕青烟。")
    assert len(issues) == 1
    assert issues[0]["rule"] == "foreshadow_consistency"

    # 3. Verify service was published to ServiceRegistry
    assert host.services.has("foreshadow.service") is True
    service = host.services.get("foreshadow.service")
    assert isinstance(service, ForeshadowService)
    assert len(service.get_tracked_foreshadows()) == 2
