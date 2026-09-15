import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from novel_agent.plugins import PluginManager
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
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_api_routes_diagnostics_and_rollback(temp_novel_root: Path):
    # Setup a sample plugin
    p1 = temp_novel_root / "plugins" / "api_test_plugin"
    p1.mkdir()
    (p1 / "plugin.py").write_text(
        """from novel_agent.plugins.base import BasePlugin, PluginMeta, PluginType
class ApiTestPlugin(BasePlugin):
    def get_meta(self):
        return PluginMeta(name="api_test_plugin", display_name="API测试插件", version="1.0.0", plugin_type=PluginType.COMMAND)
PLUGIN_CLASS = ApiTestPlugin
""",
        encoding="utf-8",
    )
    (p1 / "inkrest.plugin.json").write_text(
        json.dumps({
            "id": "api_test_plugin",
            "display_name": "API测试插件",
            "plugin_type": "command",
            "entry": "plugin:ApiTestPlugin",
            "version": "1.0.0",
        }),
        encoding="utf-8",
    )

    pm = PluginManager(temp_novel_root)
    pm.initialize()

    old_base = web.context.BASE_DIR
    old_global = web.context._global_plugin_manager
    old_proj = web.context._plugin_manager
    web.context.BASE_DIR = temp_novel_root
    web.context._global_plugin_manager = pm
    web.context._plugin_manager = pm
    try:
        client = TestClient(web_app)

        # 1. Test get diagnostics
        resp = client.get("/api/plugins/api_test_plugin/diagnostics")
        assert resp.status_code == 200
        diag_data = resp.json()
        assert diag_data["name"] == "api_test_plugin"
        assert "diagnostics" in diag_data
        assert "state" in diag_data["diagnostics"]

        # 2. Test get all diagnostics
        resp_all = client.get("/api/plugins/diagnostics/all")
        assert resp_all.status_code == 200
        assert "api_test_plugin" in resp_all.json()["diagnostics"]

        # 3. Test list versions before rollback
        resp_ver = client.get("/api/plugins/api_test_plugin/versions")
        assert resp_ver.status_code == 200
        assert "archived_versions" in resp_ver.json()
        assert resp_ver.json()["archived_versions"] == []

        # 4. Create an archived version manually to test rollback endpoint
        archive_dir = temp_novel_root / "plugins" / ".versions" / "api_test_plugin" / "0.9.0"
        archive_dir.mkdir(parents=True)
        (archive_dir / "plugin.py").write_text("# v0.9.0", encoding="utf-8")
        (archive_dir / "inkrest.plugin.json").write_text(
            json.dumps({
                "id": "api_test_plugin",
                "name": "api_test_plugin",
                "version": "0.9.0",
                "entry": "plugin:ApiTestPlugin",
                "plugin_type": "command",
            }),
            encoding="utf-8",
        )

        resp_ver2 = client.get("/api/plugins/api_test_plugin/versions")
        assert resp_ver2.status_code == 200
        assert "0.9.0" in resp_ver2.json()["archived_versions"]

        # 5. Rollback to 0.9.0
        resp_rb = client.post("/api/plugins/api_test_plugin/rollback", json={"target_version": "0.9.0"})
        assert resp_rb.status_code == 200
        assert resp_rb.json()["status"] == "rolled_back"
        assert resp_rb.json()["target_version"] == "0.9.0"

        # Verify rollback replaced plugin contents
        manifest = json.loads((p1 / "inkrest.plugin.json").read_text(encoding="utf-8"))
        assert manifest["version"] == "0.9.0"
    finally:
        web.context.BASE_DIR = old_base
        web.context._global_plugin_manager = old_global
        web.context._plugin_manager = old_proj
