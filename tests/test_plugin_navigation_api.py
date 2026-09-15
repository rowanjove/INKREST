import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from novel_agent.plugins import PluginManager
from novel_agent.plugins.permissions import digest_plugin_path
from web.app import app as web_app
import web.context


@pytest.fixture
def temp_novel_root():
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "plugins").mkdir(parents=True)
    (temp_dir / "config").mkdir(parents=True)
    (temp_dir / "config" / "pipeline.yaml").write_text(
        yaml.safe_dump({"runtime": {"interactive": False}, "llm": {"provider": "static"}}),
        encoding="utf-8",
    )
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_navigation_contributions_filter_untrusted_and_disabled(temp_novel_root: Path):
    # Create plugin 1: dual-region
    p1 = temp_novel_root / "plugins" / "dual_plugin"
    p1.mkdir()
    (p1 / "plugin.py").write_text(
        """from novel_agent.plugins.base import WebExtensionPlugin, PluginMeta, PluginType
class DualPlugin(WebExtensionPlugin):
    def get_meta(self):
        return PluginMeta(name="dual_plugin", display_name="双区插件", version="1.0.0", plugin_type=PluginType.WEB_EXTENSION)
PLUGIN_CLASS = DualPlugin
""",
        encoding="utf-8",
    )
    (p1 / "inkrest.plugin.json").write_text(
        json.dumps({
            "id": "dual_plugin",
            "display_name": "双区插件",
            "plugin_type": "web_extension",
            "entry": "plugin:DualPlugin",
            "version": "1.0.0",
            "capabilities": ["project_catalog_read", "project_read"],
            "contributes": {
                "navigation": [
                    {
                        "id": "lib-view",
                        "title": "公共模板",
                        "surface": "library_sidebar",
                        "icon": "collection",
                        "view": "lib-view",
                        "order": 100,
                        "requires": ["project_catalog_read"],
                    },
                    {
                        "id": "proj-view",
                        "title": "项目伏笔",
                        "surface": "project_sidebar",
                        "icon": "radar",
                        "view": "proj-view",
                        "order": 150,
                        "requires": ["project_read"],
                    },
                ]
            },
        }),
        encoding="utf-8",
    )

    # Create plugin 2: library-only but will remain disabled
    p2 = temp_novel_root / "plugins" / "disabled_plugin"
    p2.mkdir()
    (p2 / "plugin.py").write_text(
        """from novel_agent.plugins.base import WebExtensionPlugin, PluginMeta, PluginType
class DisPlugin(WebExtensionPlugin):
    def get_meta(self):
        return PluginMeta(name="disabled_plugin", display_name="禁用插件", version="1.0.0", plugin_type=PluginType.WEB_EXTENSION)
PLUGIN_CLASS = DisPlugin
""",
        encoding="utf-8",
    )
    (p2 / "inkrest.plugin.json").write_text(
        json.dumps({
            "id": "disabled_plugin",
            "display_name": "禁用插件",
            "plugin_type": "web_extension",
            "entry": "plugin:DisPlugin",
            "version": "1.0.0",
            "capabilities": ["project_catalog_read"],
            "contributes": {
                "navigation": [
                    {
                        "id": "dis-view",
                        "title": "禁用入口",
                        "surface": "library_sidebar",
                        "icon": "collection",
                        "view": "dis-view",
                    }
                ]
            },
        }),
        encoding="utf-8",
    )

    # Trust and enable dual_plugin, but leave disabled_plugin disabled
    p1_digest = digest_plugin_path(p1)
    (temp_novel_root / "config" / "plugins.yaml").write_text(
        yaml.safe_dump({
            "plugins": {
                "registry": {
                    "dual_plugin": {
                        "enabled": True,
                        "trust_digest": p1_digest,
                        "granted_capabilities": ["project_catalog_read", "project_read", "local_code", "project_write", "web_routes"],
                    },
                    "disabled_plugin": {
                        "enabled": False,
                    },
                }
            }
        }),
        encoding="utf-8",
    )

    pm = PluginManager(temp_novel_root, allow_web_extensions=True)
    pm.initialize()

    nav = pm.get_navigation_contributions()
    assert len(nav["library_sidebar"]) == 1
    assert nav["library_sidebar"][0]["id"] == "dual_plugin:lib-view"
    assert nav["library_sidebar"][0]["path"] == "/extensions/library/dual_plugin/lib-view"
    assert nav["library_sidebar"][0]["title"] == "公共模板"

    assert len(nav["project_sidebar"]) == 1
    assert nav["project_sidebar"][0]["id"] == "dual_plugin:proj-view"
    assert nav["project_sidebar"][0]["path"] == "/extensions/project/dual_plugin/proj-view"
    assert nav["project_sidebar"][0]["title"] == "项目伏笔"

    # Now disable dual_plugin
    pm.disable_plugin("dual_plugin")
    nav_after_disable = pm.get_navigation_contributions()
    assert len(nav_after_disable["library_sidebar"]) == 0
    assert len(nav_after_disable["project_sidebar"]) == 0


def test_plugin_navigation_keeps_global_entries_after_opening_a_book(temp_novel_root, monkeypatch):
    import web.context as ctx
    from web.context import merged_plugin_navigation

    original_base = ctx.BASE_DIR
    original_active = ctx._active_project_id
    original_global = ctx._global_plugin_manager
    original_project = ctx._plugin_manager
    try:
        ctx.BASE_DIR = temp_novel_root
        ctx._active_project_id = None
        ctx._global_plugin_manager = None
        ctx._plugin_manager = None
        monkeypatch.setenv("NOVEL_AGENT_ROOT", str(temp_novel_root))
        nav = merged_plugin_navigation()
        ctx._active_project_id = "book-a"
        (temp_novel_root / "projects" / "book-a").mkdir(parents=True, exist_ok=True)
        opened = merged_plugin_navigation()
        assert "library_sidebar" in opened
        assert isinstance(opened["library_sidebar"], list)
        assert len(opened["library_sidebar"]) >= len(nav["library_sidebar"])
    finally:
        if ctx._plugin_manager is not None:
            ctx._plugin_manager.shutdown()
        if ctx._global_plugin_manager is not None:
            ctx._global_plugin_manager.shutdown()
        ctx.BASE_DIR = original_base
        ctx._active_project_id = original_active
        ctx._global_plugin_manager = original_global
        ctx._plugin_manager = original_project


def test_merged_catalog_keeps_global_web_extension_when_project_has_stale_copy(monkeypatch):
    global_pm = type(
        "GlobalManager",
        (),
        {
            "list_plugin_catalog": lambda self: [
                {
                    "name": "script_murder",
                    "plugin_type": "web_extension",
                    "enabled": True,
                    "scope": "global",
                }
            ]
        },
    )()
    project_pm = type(
        "ProjectManager",
        (),
        {
            "list_plugin_catalog": lambda self: [
                {
                    "name": "script_murder",
                    "plugin_type": "web_extension",
                    "enabled": False,
                    "scope": "project",
                }
            ]
        },
    )()
    monkeypatch.setattr(web.context, "_active_project_id", "book-a")
    monkeypatch.setattr(web.context, "get_global_plugin_manager", lambda: global_pm)
    monkeypatch.setattr(web.context, "get_plugin_manager", lambda: project_pm)

    catalog = web.context.merged_plugin_catalog()

    assert catalog == [
        {
            "name": "script_murder",
            "plugin_type": "web_extension",
            "enabled": True,
            "scope": "global",
        }
    ]


def test_navigation_api_endpoint(temp_novel_root: Path, monkeypatch):
    pm = PluginManager(temp_novel_root, allow_web_extensions=True)
    pm.initialize()
    monkeypatch.setattr(web.context, "get_plugin_manager", lambda: pm)

    client = TestClient(web_app)
    resp = client.get("/api/plugins/navigation")
    assert resp.status_code == 200
    data = resp.json()
    assert "library_sidebar" in data
    assert "project_sidebar" in data
    assert isinstance(data["library_sidebar"], list)
    assert isinstance(data["project_sidebar"], list)
