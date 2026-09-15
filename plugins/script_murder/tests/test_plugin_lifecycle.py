import json
import shutil
from pathlib import Path
import pytest
import yaml

from novel_agent.plugins.manager import PluginManager


@pytest.fixture
def isolated_app_root(tmp_path: Path):
    root = tmp_path / "app"
    root.mkdir()
    plugins_dir = root / "plugins"
    plugins_dir.mkdir()
    config_dir = root / "config"
    config_dir.mkdir()

    # Link or copy script_murder into mock plugins directory
    real_plugin_dir = Path(__file__).resolve().parent.parent
    target_plugin_dir = plugins_dir / "script_murder"
    shutil.copytree(
        real_plugin_dir,
        target_plugin_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # Initialize manager to discover plugin and compute its digest
    pm = PluginManager(root, allow_web_extensions=True)
    entry = pm.discovery.discover_all().get("script_murder")
    assert entry is not None
    desc = pm._security_descriptor("script_murder", entry)

    # Configure trust and enable script_murder
    (config_dir / "plugins.yaml").write_text(
        yaml.safe_dump({
            "plugins": {
                "registry": {
                    "script_murder": {
                        "enabled": True,
                        "trust_digest": desc["digest"],
                        "granted_capabilities": desc["effective_capabilities"],
                    }
                }
            }
        }),
        encoding="utf-8",
    )

    return root


def test_script_murder_plugin_integration(isolated_app_root: Path):
    pm = PluginManager(isolated_app_root, allow_web_extensions=True)
    pm.initialize()

    assert "script_murder" in pm.plugins
    loaded = pm.plugins["script_murder"]
    assert loaded.enabled is True

    # 1. Navigation Contributions
    nav = pm.get_navigation_contributions()
    lib_items = nav.get("library_sidebar", [])
    assert any(item["id"] == "script_murder:studio" for item in lib_items)
    studio_item = next(item for item in lib_items if item["id"] == "script_murder:studio")
    assert studio_item["title"] == "剧本工坊"
    assert studio_item["path"] == "/extensions/library/script_murder/studio"
    assert studio_item["view"] == "studio"

    # 2. View Session Lifecycle & Document Loading
    sess = pm.create_view_session("script_murder", "studio")
    assert "session_id" in sess
    assert sess["surface"] == "library_sidebar"
    sid = sess["session_id"]

    doc = pm.load_view_document("script_murder", "studio", sid)
    assert doc["has_document"] is True
    assert "墨局 · 剧本杀工坊" in doc["html"]
    assert "Truth Canon" in doc["html"]

    # 3. Router Binding
    router = loaded.instance.get_router()
    assert router is not None
    assert router.prefix == "/api/ext/script-murder"

    # 4. Session Close
    assert pm.close_view_session(sid) is True
    pm.shutdown()
