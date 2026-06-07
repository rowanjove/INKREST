"""ZIP plugin install / manifest validation."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from novel_agent.plugins import PluginManager
from novel_agent.plugins.installer import install_plugin_zip
from novel_agent.plugins.manifest import ManifestError, load_manifest


def _make_plugin_zip(tmp: Path, plugin_id: str = "demo-hook") -> bytes:
    root = tmp / "pkg"
    root.mkdir()
    (root / "inkrest.plugin.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "version": "1.0.0",
                "display_name": "演示钩子",
                "description": "测试插件",
                "plugin_type": "pipeline_hook",
                "entry": "plugin:PLUGIN_CLASS",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "plugin.py").write_text(
        """
from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType

class DemoHook(PipelineHookPlugin):
    def get_meta(self):
        return PluginMeta(
            name="demo-hook",
            display_name="演示钩子",
            plugin_type=PluginType.PIPELINE_HOOK,
        )
    def after_outline(self, outline):
        outline["demo"] = True
        return outline

PLUGIN_CLASS = DemoHook
""".strip(),
        encoding="utf-8",
    )
    zpath = tmp / "plugin.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(root).as_posix())
    return zpath.read_bytes()


def test_install_plugin_zip_extracts_manifest(tmp_path: Path) -> None:
    data = _make_plugin_zip(tmp_path)
    result = install_plugin_zip(tmp_path, data)
    assert result["id"] == "demo-hook"
    plugin_dir = tmp_path / "plugins" / "demo-hook"
    assert plugin_dir.is_dir()
    assert (plugin_dir / "inkrest.plugin.json").is_file()
    manifest = load_manifest(plugin_dir)
    assert manifest["plugin_type"] == "pipeline_hook"


def test_install_rejects_path_traversal(tmp_path: Path) -> None:
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../evil.txt", "x")
    with pytest.raises(ManifestError):
        install_plugin_zip(tmp_path, zpath.read_bytes())


def test_install_rejects_extract_rule_escape_without_writing_sibling(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "inkrest.plugin.json").write_text(
        json.dumps(
            {
                "id": "abc",
                "version": "1.0.0",
                "display_name": "Bad Plugin",
                "description": "attempts sibling write",
                "plugin_type": "pipeline_hook",
                "entry": "plugin:PLUGIN_CLASS",
                "extract": [{"from": "payload.txt", "to": "../abc_evil/pwned.txt"}],
            }
        ),
        encoding="utf-8",
    )
    (root / "plugin.py").write_text("PLUGIN_CLASS = object\n", encoding="utf-8")
    (root / "payload.txt").write_text("owned", encoding="utf-8")
    zpath = tmp_path / "bad-extract.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(root).as_posix())

    with pytest.raises(ManifestError):
        install_plugin_zip(tmp_path, zpath.read_bytes())

    assert not (tmp_path / "plugins" / "abc_evil" / "pwned.txt").exists()


def test_plugin_manager_install_and_catalog(tmp_path: Path) -> None:
    import yaml

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.yaml").write_text(
        yaml.safe_dump({"runtime": {"interactive": False}, "llm": {"provider": "static"}}),
        encoding="utf-8",
    )
    data = _make_plugin_zip(tmp_path)
    pm = PluginManager(tmp_path)
    pm.install_from_zip(data)
    catalog = pm.list_plugin_catalog()
    names = [p["name"] for p in catalog]
    assert "demo-hook" in names
    row = next(p for p in catalog if p["name"] == "demo-hook")
    assert row["trusted"] is False
    assert row["loaded"] is False
