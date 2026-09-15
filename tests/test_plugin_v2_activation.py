import pytest
from novel_agent.plugins.activation import ActivationManager
from novel_agent.plugins.lifecycle import PluginDiagnostics, PluginState


def test_activation_manager_eager_and_lazy():
    activated_order = []

    def mock_activator(plugin_id: str):
        activated_order.append(plugin_id)
        return True

    diagnostics_map = {
        "p_eager": PluginDiagnostics(plugin_id="p_eager", status=PluginState.READY),
        "p_cmd": PluginDiagnostics(plugin_id="p_cmd", status=PluginState.READY),
        "p_hook": PluginDiagnostics(plugin_id="p_hook", status=PluginState.READY),
    }

    mgr = ActivationManager(
        activator=mock_activator,
        diagnostics_provider=lambda pid: diagnostics_map.get(pid),
    )

    # 1. Register plugins
    is_eager = mgr.register_plugin("p_eager", ["*"])
    assert is_eager is True

    is_cmd_eager = mgr.register_plugin("p_cmd", ["onCommand:detect_clues"])
    assert is_cmd_eager is False

    is_hook_eager = mgr.register_plugin("p_hook", ["onHook:pre_generate"])
    assert is_hook_eager is False

    # 2. Activate eager plugins
    eager_activated = mgr.activate_eager_plugins()
    assert eager_activated == ["p_eager"]
    assert mgr.is_activated("p_eager") is True
    assert mgr.is_activated("p_cmd") is False
    assert mgr.is_activated("p_hook") is False
    assert diagnostics_map["p_eager"].status == PluginState.ACTIVE

    # 3. Trigger command
    cmd_activated = mgr.trigger_command("detect_clues")
    assert cmd_activated == ["p_cmd"]
    assert mgr.is_activated("p_cmd") is True
    assert diagnostics_map["p_cmd"].status == PluginState.ACTIVE

    # 4. Trigger hook
    hook_activated = mgr.trigger_hook("pre_generate")
    assert hook_activated == ["p_hook"]
    assert mgr.is_activated("p_hook") is True

    # 5. Repeated trigger should be idempotent
    repeat_activated = mgr.trigger_command("detect_clues")
    assert repeat_activated == []
    assert len(activated_order) == 3


def test_activation_failure_handling():
    def failing_activator(plugin_id: str):
        if plugin_id == "p_broken":
            raise ValueError("Plugin crashed on boot")
        return True

    diag = PluginDiagnostics(plugin_id="p_broken", status=PluginState.READY)
    mgr = ActivationManager(
        activator=failing_activator,
        diagnostics_provider=lambda pid: diag,
    )

    mgr.register_plugin("p_broken", ["onCommand:crash"])

    with pytest.raises(ValueError, match="Plugin crashed on boot"):
        mgr.activate_plugin("p_broken")

    assert mgr.is_activated("p_broken") is False
    assert diag.status == PluginState.FAILED
    assert "Plugin crashed on boot" in diag.last_error
