"""Comprehensive tests for INKREST Plugin Platform 2.0 Core.

Covers:
- ContributionRegistry (multi-capability declaration)
- HookRegistry & HookContracts (collect, first, reduce, failure policies)
- ServiceRegistry & DependencyResolver (DAG, cycles, services check)
- CapabilityBroker (permission gatekeeper, storage isolation, audit logs)
- LegacyPluginAdapter (100% backward compatibility for V1 plugins)
"""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from novel_agent.plugins.base import (
    PipelineHookPlugin,
    PluginMeta,
    PluginType,
    QualityGuardPlugin,
)
from novel_agent.plugins.capability_broker import (
    CapabilityBroker,
    PermissionDeniedError,
)
from novel_agent.plugins.contributions import (
    CommandContribution,
    ContributionRegistry,
    ValidatorContribution,
)
from novel_agent.plugins.hooks import (
    HookContract,
    HookExecutionError,
    HookRegistry,
    hookimpl,
    hookspec,
)
from novel_agent.plugins.legacy_adapter import LegacyPluginAdapter
from novel_agent.plugins.resolver import (
    CircularDependencyError,
    DependencyResolver,
    MissingDependencyError,
)
from novel_agent.plugins.services import (
    SERVICE_PROJECT_READER,
    SERVICE_STORAGE,
    ServiceNotFoundError,
    ServiceRegistry,
)


def test_contribution_registry_and_manifest_loading() -> None:
    reg = ContributionRegistry()
    manifest_data = {
        "commands": [
            {"id": "scan_plot", "title": "扫描剧情", "category": "Quality"},
        ],
        "views": [
            {"id": "inspector", "title": "伏笔面板", "surface": "project_sidebar", "view_id": "foreshadow_panel"},
        ],
        "validators": [
            {"id": "rule_check", "label": "规则检查", "scope": "chapter"},
        ],
        "exporters": [
            {"id": "mobi", "format": "mobi", "label": "MOBI 导出器"},
        ],
    }
    reg.load_from_manifest("my.plugin", manifest_data)

    serialized = reg.to_dict()
    assert len(serialized["commands"]) == 1
    assert serialized["commands"][0]["id"] == "my.plugin.scan_plot"

    assert len(serialized["views"]) == 1
    assert serialized["views"][0]["id"] == "my.plugin.inspector"

    assert len(serialized["validators"]) == 1
    assert serialized["validators"][0]["id"] == "my.plugin.rule_check"

    assert len(serialized["exporters"]) == 1
    assert serialized["exporters"][0]["format"] == "mobi"


def test_hook_registry_collect_mode() -> None:
    reg = HookRegistry()

    @hookspec(mode="collect")
    def quality_check(text: str) -> list[str]:
        pass

    reg.register_spec(quality_check)

    # Register two plugins implementing quality_check
    reg.register_impl("quality_check", "plugin_a", lambda text: f"issue_from_a_{len(text)}")
    reg.register_impl("quality_check", "plugin_b", lambda text: f"issue_from_b_{len(text)}")

    results = reg.call_hook("quality_check", "test chapter content")
    assert results == ["issue_from_a_20", "issue_from_b_20"]


def test_hook_registry_reduce_mode() -> None:
    reg = HookRegistry()

    @hookspec(mode="reduce")
    def transform_text(text: str) -> str:
        pass

    reg.register_spec(transform_text)

    # First add prefix, then add suffix
    reg.register_impl("transform_text", "plugin_prefix", lambda text: f"[START] {text}", priority=10)
    reg.register_impl("transform_text", "plugin_suffix", lambda text: f"{text} [END]", priority=5)

    transformed = reg.call_hook("transform_text", "hello world")
    assert transformed == "[START] hello world [END]"


def test_hook_failure_policies() -> None:
    reg = HookRegistry()

    @hookspec(mode="first", failure="skip", fallback_value="fallback_ok")
    def faulty_hook() -> str:
        pass

    reg.register_spec(faulty_hook)

    def failing_impl():
        raise RuntimeError("Something broke!")

    reg.register_impl("faulty_hook", "bad_plugin", failing_impl)
    # Under "skip" / "fallback", it should gracefully return fallback_value instead of crashing
    assert reg.call_hook("faulty_hook") == "fallback_ok"


def test_service_registry_and_dependency_injection() -> None:
    services = ServiceRegistry()
    services.register(SERVICE_PROJECT_READER, {"type": "mock_reader"}, owner="core")
    services.register(SERVICE_STORAGE, {"type": "mock_storage"}, owner="core")

    assert services.has(SERVICE_PROJECT_READER) is True
    assert services.get(SERVICE_PROJECT_READER)["type"] == "mock_reader"

    with pytest.raises(ServiceNotFoundError):
        services.get("nonexistent.service")


def test_dependency_resolver_dag_and_cycles() -> None:
    resolver = DependencyResolver()
    resolver.add_plugin("plugin_base", "1.0.0")
    resolver.add_plugin("plugin_middle", "1.0.0", dependencies=["plugin_base"])
    resolver.add_plugin("plugin_top", "1.0.0", dependencies=["plugin_middle"])

    order = resolver.resolve_order()
    assert order == ["plugin_base", "plugin_middle", "plugin_top"]

    # Test cycle detection
    cycler = DependencyResolver()
    cycler.add_plugin("A", dependencies=["B"])
    cycler.add_plugin("B", dependencies=["A"])
    with pytest.raises(CircularDependencyError):
        cycler.resolve_order()

    # Test missing dependency
    missing = DependencyResolver()
    missing.add_plugin("orphan", dependencies=["nonexistent_parent"])
    with pytest.raises(MissingDependencyError):
        missing.resolve_order()


def test_capability_broker_permission_enforcement(tmp_path: Path) -> None:
    # Granted only project_read
    broker_readonly = CapabilityBroker("readonly-plugin", ["project_read"], tmp_path)

    # Writing chapter without project_write should raise PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        broker_readonly.project.write_chapter("demo_proj", "001", {"content": "evil"})

    # Granted model_access and project_write
    broker_full = CapabilityBroker("full-plugin", ["project_write", "model_access"], tmp_path)
    assert broker_full.project.write_chapter("demo_proj", "001", {"content": "ok"}) is True

    # Path traversal protection tests
    with pytest.raises(PermissionDeniedError):
        broker_full.project.write_chapter("../../escaped", "001", {"content": "bad"})
    with pytest.raises(PermissionDeniedError):
        broker_full.project.write_chapter("demo_proj", "../evil", {"content": "bad"})

    # Storage is isolated per plugin
    broker_full.storage.set("token_key", "secret_val")
    assert broker_full.storage.get("token_key") == "secret_val"

    # Audit log records the actions
    assert len(broker_full.audit_log) >= 1
    assert broker_full.audit_log[0]["action"] == "project.write.chapter"


def test_legacy_plugin_adapter_backward_compatibility() -> None:
    class OldHookPlugin(PipelineHookPlugin):
        def get_meta(self):
            return PluginMeta(
                name="old-hook",
                display_name="老式钩子",
                plugin_type=PluginType.PIPELINE_HOOK,
            )
        def after_outline(self, outline):
            outline["adapted"] = True
            return outline

    class OldGuardPlugin(QualityGuardPlugin):
        def get_meta(self):
            return PluginMeta(
                name="old-guard",
                display_name="老式卫士",
                plugin_type=PluginType.QUALITY_GUARD,
            )
        def check(self, text: str, context: Any = None):
            return ["warning: test"]

    contributions = ContributionRegistry()
    hooks = HookRegistry()

    # Adapt hook plugin
    hook_plugin = OldHookPlugin()
    LegacyPluginAdapter(hook_plugin).adapt_into_registries(contributions, hooks)

    assert "after_outline" in hooks.impls
    res = hooks.call_hook("after_outline", {"title": "大纲"})
    assert res == [{"title": "大纲", "adapted": True}]

    # Adapt guard plugin
    guard_plugin = OldGuardPlugin()
    LegacyPluginAdapter(guard_plugin).adapt_into_registries(contributions, hooks)

    assert "old-guard.guard" in contributions.validators
    validator = contributions.validators["old-guard.guard"]
    assert validator.handler(None) == ["warning: test"]
