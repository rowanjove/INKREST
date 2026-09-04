import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from novel_agent.plugins.manager import PluginManager


@pytest.fixture
def mock_root_with_plugin(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    plugins_dir = root / "plugins"
    plugins_dir.mkdir()
    projects_dir = root / "projects" / "test_novel"
    projects_dir.mkdir(parents=True)
    (projects_dir / "config").mkdir()
    (projects_dir / "config" / "project_meta.json").write_text(
        json.dumps({"name": "测试作品", "id": "test_novel"}), encoding="utf-8"
    )

    pdir = plugins_dir / "test-tool"
    pdir.mkdir()
    (pdir / "plugin.py").write_text(
        """from novel_agent.plugins.base import WebExtensionPlugin, PluginMeta, PluginType
class TestPlugin(WebExtensionPlugin):
    def get_meta(self):
        return PluginMeta(name="test-tool", display_name="Test Tool", version="1.0.0", plugin_type=PluginType.WEB_EXTENSION)
PLUGIN_CLASS = TestPlugin
""",
        encoding="utf-8",
    )
    manifest_data = {
        "manifest_version": "0.2.0",
        "id": "test-tool",
        "name": "Test Tool",
        "plugin_type": "web_extension",
        "entry": "plugin:TestPlugin",
        "version": "1.0.0",
        "capabilities": ["project_read", "ui_embed"],
        "contributes": {
            "navigation": [
                {
                    "id": "radar",
                    "title": "伏笔雷达",
                    "surface": "project_sidebar",
                    "view": "radar-view",
                    "icon": "radar",
                    "requires": ["project_read"],
                }
            ]
        },
    }
    (pdir / "inkrest.plugin.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    (root / "config").mkdir()
    pm = PluginManager(root, allow_web_extensions=True)
    entry = pm.discovery.discover_all()["test-tool"]
    desc = pm._security_descriptor("test-tool", entry)
    import yaml
    (root / "config" / "plugins.yaml").write_text(
        yaml.safe_dump({
            "plugins": {
                "registry": {
                    "test-tool": {
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


def test_view_session_lifecycle(mock_root_with_plugin):
    pm = PluginManager(mock_root_with_plugin, allow_web_extensions=True)
    pm.initialize()

    # Success session allocation
    sess = pm.create_view_session("test-tool", "radar-view", project_id="test_novel")
    assert "session_id" in sess
    assert sess["surface"] == "project_sidebar"
    assert sess["project_id"] == "test_novel"
    assert "project_read" in sess["granted_capabilities"]

    # Close session
    assert pm.close_view_session(sess["session_id"]) is True
    assert pm.close_view_session(sess["session_id"]) is False


def test_execute_view_rpc(mock_root_with_plugin):
    pm = PluginManager(mock_root_with_plugin, allow_web_extensions=True)
    pm.initialize()

    sess = pm.create_view_session("test-tool", "radar-view", project_id="test_novel")
    sid = sess["session_id"]

    # host.ping
    res_ping = pm.execute_view_rpc("test-tool", "radar-view", sid, "host.ping")
    assert res_ping.get("result", {}).get("pong") is True

    # project.getInfo (allowed with project_read)
    res_info = pm.execute_view_rpc("test-tool", "radar-view", sid, "project.getInfo")
    assert res_info.get("result", {}).get("name") == "测试作品"

    # catalog.listProjects (fails because plugin does not have project_catalog_read)
    res_cat = pm.execute_view_rpc("test-tool", "radar-view", sid, "catalog.listProjects")
    assert "error" in res_cat
    assert res_cat["error"]["code"] == -32003

    # Unknown method
    res_unknown = pm.execute_view_rpc("test-tool", "radar-view", sid, "unknown.method")
    assert res_unknown["error"]["code"] == -32601


def test_plugin_view_routes(mock_root_with_plugin, monkeypatch):
    from web.app import app
    from web.context import get_plugin_manager

    pm = PluginManager(mock_root_with_plugin, allow_web_extensions=True)
    pm.initialize()
    monkeypatch.setattr("web.routes.plugins.get_plugin_manager", lambda: pm)

    client = TestClient(app)

    # 1. Create session
    resp = client.post("/api/plugins/test-tool/views/radar-view/session", json={"project_id": "test_novel"})
    assert resp.status_code == 200
    data = resp.json()
    sid = data["session_id"]

    # 2. Call RPC
    rpc_resp = client.post(
        "/api/plugins/test-tool/views/radar-view/rpc",
        json={"session_id": sid, "method": "project.getInfo"},
    )
    assert rpc_resp.status_code == 200
    assert rpc_resp.json()["result"]["id"] == "test_novel"

    # 3. Close session
    del_resp = client.delete(f"/api/plugins/test-tool/views/radar-view/session/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["closed"] is True

    # 4. Call RPC after close -> error
    rpc_after = client.post(
        "/api/plugins/test-tool/views/radar-view/rpc",
        json={"session_id": sid, "method": "project.getInfo"},
    )
    assert rpc_after.status_code == 200
    assert rpc_after.json()["error"]["code"] == -32001


def test_rpc_chapters_and_characters_reading(mock_root_with_plugin):
    proj_dir = mock_root_with_plugin / "projects" / "test_novel"
    # Write chapters
    ch1 = proj_dir / "workspace" / "chapters" / "001"
    ch1.mkdir(parents=True)
    (ch1 / "chapter_final.txt").write_text("第一章正文内容，共十五字。", encoding="utf-8")

    # Write character cards yaml
    (proj_dir / "assets").mkdir(parents=True)
    (proj_dir / "assets" / "character_cards.yaml").write_text(
        "林尘:\n  identity: 主角\n  personality: 坚毅\n", encoding="utf-8"
    )

    # Test when pm is created inside the project directory
    pm_in_project = PluginManager(proj_dir, allow_web_extensions=True)
    import time
    pm_in_project._view_sessions["sess_1"] = {
        "session_id": "sess_1",
        "plugin_id": "test-tool",
        "view_id": "radar-view",
        "project_id": "test_novel",
        "granted_capabilities": ["project_read"],
        "created_at": time.time(),
    }

    # 1. getChapters
    res_ch = pm_in_project.execute_view_rpc("test-tool", "radar-view", "sess_1", "project.getChapters")
    assert "result" in res_ch
    chapters = res_ch["result"]["chapters"]
    assert len(chapters) == 1
    assert chapters[0]["chapter_id"] == "001"
    assert chapters[0]["word_count"] > 0

    # 2. getCharacters
    res_chars = pm_in_project.execute_view_rpc("test-tool", "radar-view", "sess_1", "project.getCharacters")
    assert "result" in res_chars
    characters = res_chars["result"]["characters"]
    assert len(characters) == 1
    assert characters[0]["name"] == "林尘"
    assert characters[0]["identity"] == "主角"

