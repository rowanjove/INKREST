import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

from novel_agent.pipeline import PipelineConfig
from novel_agent.plugins import PluginManager
from novel_agent.plugins.base import (
    ExporterPlugin,
    PipelineHookPlugin,
    PluginBase,
    PluginContext,
    PluginMeta,
    PluginType,
    QualityGuardPlugin,
)
from web.routes.plugins import _reload_plugin_manager
from web.app import app as web_app
from web.app import _mounted_web_extensions, _require_enabled_web_extension, mount_plugin_web_extensions


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for project root
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plugins_dir = self.temp_dir / "plugins"
        self.plugins_dir.mkdir()
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()

        # Write default pipeline.yaml
        with open(self.config_dir / "pipeline.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump({"runtime": {"interactive": False}, "llm": {"provider": "static"}}, f)

        # Write dummy plugins
        self._write_test_guard_plugin()
        self._write_test_hook_plugin()
        (self.config_dir / "plugins.yaml").write_text(
            yaml.safe_dump({
                "plugins": {
                    "registry": {
                        "test_guard": {"enabled": True},
                        "test_hook": {"enabled": True},
                    }
                }
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_test_guard_plugin(self):
        code = """from novel_agent.plugins.base import QualityGuardPlugin, PluginMeta, PluginType

class TestGuard(QualityGuardPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="test-guard",
            display_name="测试守卫",
            description="如果文本中包含AI就报错",
            plugin_type=PluginType.QUALITY_GUARD
        )
        
    def check(self, text, context):
        if "AI" in text:
            return {"pass": False, "score": 20, "details": ["发现AI风味"]}
        return {"pass": True, "score": 100, "details": []}

PLUGIN_CLASS = TestGuard
"""
        with open(self.plugins_dir / "test_guard.py", "w", encoding="utf-8") as f:
            f.write(code)

    def _write_test_hook_plugin(self):
        code = """from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType

class TestHook(PipelineHookPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="test-hook",
            display_name="测试钩子",
            plugin_type=PluginType.PIPELINE_HOOK
        )
        
    def after_outline(self, outline):
        outline["hook_executed"] = True
        return outline

PLUGIN_CLASS = TestHook
"""
        with open(self.plugins_dir / "test_hook.py", "w", encoding="utf-8") as f:
            f.write(code)

    def test_discovery_and_initialization(self):
        # Initialize manager pointing to temp root
        pm = PluginManager(self.temp_dir)
        pm.initialize()

        # Check discovered
        self.assertIn("test_guard", pm.plugins)
        self.assertIn("test_hook", pm.plugins)

        # Active caches should be empty initially because enabled defaults to True in initialize (if not configured)
        # Wait, in our implementation we used: enabled = plugin_state.get("enabled", True)
        # So they should be enabled by default
        self.assertTrue(pm.plugins["test_guard"].enabled)
        self.assertTrue(pm.plugins["test_hook"].enabled)

        # Check if they are in active by type
        guards = pm.get_quality_guards()
        self.assertEqual(len(guards), 1)
        self.assertEqual(guards[0].get_meta().name, "test-guard")

        hooks = pm.get_hooks()
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].get_meta().name, "test-hook")

    def test_untrusted_local_plugin_is_not_imported(self):
        (self.config_dir / "plugins.yaml").unlink()
        marker = self.plugins_dir / "imported.txt"
        (self.plugins_dir / "untrusted.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).with_name('imported.txt').write_text('executed', encoding='utf-8')\n"
            "from novel_agent.plugins.base import PluginBase, PluginMeta\n"
            "class Untrusted(PluginBase):\n"
            "    def get_meta(self): return PluginMeta(name='untrusted')\n"
            "PLUGIN_CLASS = Untrusted\n",
            encoding="utf-8",
        )

        pm = PluginManager(self.temp_dir)
        pm.initialize()

        self.assertFalse(marker.exists())
        self.assertNotIn("untrusted", pm.plugins)

    def test_local_plugin_loads_only_after_explicit_trust(self):
        (self.config_dir / "plugins.yaml").unlink()
        marker = self.plugins_dir / "trusted.txt"
        (self.plugins_dir / "trusted.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).with_name('trusted.txt').write_text('executed', encoding='utf-8')\n"
            "from novel_agent.plugins.base import PluginBase, PluginMeta\n"
            "class Trusted(PluginBase):\n"
            "    def get_meta(self): return PluginMeta(name='trusted')\n"
            "PLUGIN_CLASS = Trusted\n",
            encoding="utf-8",
        )

        pm = PluginManager(self.temp_dir)
        pm.initialize()
        self.assertIn("trusted", pm.list_untrusted_local_plugins())
        self.assertFalse(marker.exists())

        self.assertTrue(pm.trust_local_plugin("trusted"))
        pm.initialize()
        self.assertTrue(marker.exists())
        self.assertTrue(pm.plugins["trusted"].enabled)

    def test_project_scoped_web_extension_is_not_loaded(self):
        (self.plugins_dir / "project_web.py").write_text(
            "from novel_agent.plugins.base import PluginMeta, PluginType, WebExtensionPlugin\n"
            "class ProjectWeb(WebExtensionPlugin):\n"
            "    def get_meta(self): return PluginMeta(name='project-web', plugin_type=PluginType.WEB_EXTENSION)\n"
            "    def get_router(self): return None\n"
            "PLUGIN_CLASS = ProjectWeb\n",
            encoding="utf-8",
        )
        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        state["plugins"]["registry"]["project_web"] = {"enabled": True}
        (self.config_dir / "plugins.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")

        pm = PluginManager(self.temp_dir)
        pm.initialize()

        self.assertNotIn("project_web", pm.plugins)

    def test_reload_preserves_enabled_plugin_state(self):
        pm = PluginManager(self.temp_dir)
        pm.initialize()

        _reload_plugin_manager(pm)

        self.assertTrue(pm.plugins["test_guard"].enabled)
        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        self.assertTrue(state["plugins"]["registry"]["test_guard"]["enabled"])

    def test_failed_activation_rolls_back_enabled_state(self):
        (self.plugins_dir / "broken.py").write_text(
            "from novel_agent.plugins.base import PluginBase, PluginMeta\n"
            "class Broken(PluginBase):\n"
            "    def get_meta(self): return PluginMeta(name='broken')\n"
            "    def on_activate(self, context): raise RuntimeError('activation failed')\n"
            "PLUGIN_CLASS = Broken\n",
            encoding="utf-8",
        )
        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        state["plugins"]["registry"]["broken"] = {"enabled": True}
        (self.config_dir / "plugins.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")

        pm = PluginManager(self.temp_dir)
        pm.initialize()

        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        self.assertFalse(state["plugins"]["registry"]["broken"]["enabled"])

    def test_shutdown_deactivates_plugins_without_changing_desired_state(self):
        marker = self.plugins_dir / "deactivated.txt"
        (self.plugins_dir / "shutdown_hook.py").write_text(
            "from pathlib import Path\n"
            "from novel_agent.plugins.base import PluginBase, PluginMeta\n"
            "class ShutdownHook(PluginBase):\n"
            "    def get_meta(self): return PluginMeta(name='shutdown-hook')\n"
            "    def on_deactivate(self): Path(__file__).with_name('deactivated.txt').write_text('done', encoding='utf-8')\n"
            "PLUGIN_CLASS = ShutdownHook\n",
            encoding="utf-8",
        )
        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        state["plugins"]["registry"]["shutdown_hook"] = {"enabled": True}
        (self.config_dir / "plugins.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")
        pm = PluginManager(self.temp_dir)
        pm.initialize()

        pm.shutdown()

        state = yaml.safe_load((self.config_dir / "plugins.yaml").read_text(encoding="utf-8"))
        self.assertTrue(marker.exists())
        self.assertTrue(state["plugins"]["registry"]["shutdown_hook"]["enabled"])

    def test_disabled_web_extension_route_is_rejected(self):
        loaded = type("Loaded", (), {"enabled": False})()

        with self.assertRaises(HTTPException) as ctx:
            _require_enabled_web_extension(loaded)

        self.assertEqual(ctx.exception.status_code, 404)

    def test_web_extension_route_can_be_mounted_after_reload(self):
        route_path = f"/api/test-web-extension-{uuid.uuid4().hex}"
        router = APIRouter()

        @router.get(route_path)
        def endpoint():
            return {"status": "ok"}

        class Extension:
            def get_router(self):
                return router

        loaded = type("Loaded", (), {"enabled": True, "instance": Extension()})()
        pm = type("Manager", (), {"allow_web_extensions": True, "plugins": {"test_dynamic": loaded}})()
        original_routes = list(web_app.router.routes)
        try:
            mount_plugin_web_extensions(pm)
            self.assertEqual(TestClient(web_app).get(route_path).status_code, 200)

            loaded.enabled = False
            self.assertEqual(TestClient(web_app).get(route_path).status_code, 404)
        finally:
            web_app.router.routes[:] = original_routes
            _mounted_web_extensions.pop("test_dynamic", None)

    def test_enable_disable_toggle(self):
        pm = PluginManager(self.temp_dir)
        pm.initialize()

        # Disable guard
        success = pm.disable_plugin("test_guard")
        self.assertTrue(success)
        self.assertFalse(pm.plugins["test_guard"].enabled)
        self.assertEqual(len(pm.get_quality_guards()), 0)

        # Check state saved to yaml
        yaml_path = self.temp_dir / "config" / "plugins.yaml"
        self.assertTrue(yaml_path.exists())
        with open(yaml_path, "r", encoding="utf-8") as f:
            state = yaml.safe_load(f)
        self.assertFalse(state["plugins"]["registry"]["test_guard"]["enabled"])

        # Enable guard back
        success = pm.enable_plugin("test_guard")
        self.assertTrue(success)
        self.assertTrue(pm.plugins["test_guard"].enabled)
        self.assertEqual(len(pm.get_quality_guards()), 1)

    def test_quality_guard_execution(self):
        pm = PluginManager(self.temp_dir)
        pm.initialize()

        guards = pm.get_quality_guards()
        guard = guards[0]

        # Test check PASS
        res = guard.check("这是一段正常的小说文字，非常有韵味。", None)
        self.assertTrue(res["pass"])
        self.assertEqual(res["score"], 100)

        # Test check FAIL
        res = guard.check("这是一段AI写出来的小说文字。", None)
        self.assertFalse(res["pass"])
        self.assertEqual(res["score"], 20)

    def test_pipeline_integration(self):
        # Load pipeline config pointing to temp root
        config = PipelineConfig.from_config(self.temp_dir)
        self.assertIsNotNone(config.plugin_manager)

        # Create orchestrator
        from novel_agent.orchestrator import NovelOrchestrator
        orchestrator = NovelOrchestrator(config)

        # Test outline hook execution
        outline = {"title_options": ["测试小说"], "macro_outline": []}
        import asyncio

        # Trigger run_novel or hook calls
        # Let's test the outline hook hook call directly
        theme_kwargs = {}
        for hook in config.plugin_manager.get_hooks():
            theme_kwargs = hook.before_outline("测试主题", "玄幻", **theme_kwargs)

        for hook in config.plugin_manager.get_hooks():
            outline = hook.after_outline(outline)

        self.assertTrue(outline.get("hook_executed"))
