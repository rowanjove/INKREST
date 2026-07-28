"""ZIP plugin install / manifest validation."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from novel_agent.plugins import PluginManager
from novel_agent.plugins.installer import (
    MIN_ZIP_RATIO_CHECK_BYTES,
    MAX_ZIP_FILES,
    install_plugin_zip,
)
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
    assert manifest["capability_mode"] == "inferred"
    assert {"local_code", "project_read", "project_write", "model_access"} <= set(
        manifest["capabilities"]
    )


def test_install_allows_small_highly_compressible_member(tmp_path: Path) -> None:
    _make_plugin_zip(tmp_path)
    source = tmp_path / "plugin.zip"
    with zipfile.ZipFile(source, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("small-template.txt", "x" * (64 * 1024))

    result = install_plugin_zip(tmp_path, source.read_bytes())
    assert result["id"] == "demo-hook"


def test_install_rejects_large_suspicious_compression_ratio(tmp_path: Path) -> None:
    _make_plugin_zip(tmp_path)
    source = tmp_path / "plugin.zip"
    with zipfile.ZipFile(source, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("oversized-template.txt", "x" * MIN_ZIP_RATIO_CHECK_BYTES)

    with pytest.raises(ManifestError, match="压缩率异常"):
        install_plugin_zip(tmp_path, source.read_bytes())


def test_extract_zip_safe_enforces_streamed_member_size(tmp_path: Path, monkeypatch) -> None:
    from novel_agent.plugins import installer as installer_mod

    monkeypatch.setattr(installer_mod, "MAX_ZIP_MEMBER_BYTES", 128)
    monkeypatch.setattr(installer_mod, "MAX_ZIP_UNCOMPRESSED_BYTES", 10_000)
    monkeypatch.setattr(installer_mod, "MAX_ZIP_FILES", 50)
    monkeypatch.setattr(installer_mod, "MIN_ZIP_RATIO_CHECK_BYTES", 10_000_000)

    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        # Declare a small size in the central directory while writing more bytes.
        info = zipfile.ZipInfo("big.bin")
        info.file_size = 64
        info.compress_size = 64
        info.CRC = 0
        # ZipFile will rewrite sizes for STORED; force post-validation by streaming
        # a large payload through a normal member and a lowered limit instead.
        archive.writestr("big.bin", b"x" * 512)

    with pytest.raises(ManifestError, match="单个文件过大|总大小超过"):
        installer_mod._extract_zip_safe(zip_path, tmp_path / "out")


@pytest.mark.parametrize(
    "capabilities, message",
    [
        (["unknown_permission"], "未知插件权限"),
        (["project_read", "project_read"], "重复插件权限"),
        ("project_read", "capabilities 必须是字符串数组"),
    ],
)
def test_manifest_rejects_invalid_capability_declarations(
    tmp_path: Path,
    capabilities: object,
    message: str,
) -> None:
    root = tmp_path / "invalid-capability"
    root.mkdir()
    (root / "plugin.py").write_text("PLUGIN_CLASS = object\n", encoding="utf-8")
    (root / "inkrest.plugin.json").write_text(
        json.dumps(
            {
                "id": "invalid-capability",
                "plugin_type": "quality_guard",
                "entry": "plugin:PLUGIN_CLASS",
                "capabilities": capabilities,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match=message):
        load_manifest(root)


def test_legacy_hooks_capability_uses_compatibility_inference(tmp_path: Path) -> None:
    root = tmp_path / "legacy-hooks"
    root.mkdir()
    (root / "plugin.py").write_text("PLUGIN_CLASS = object\n", encoding="utf-8")
    (root / "inkrest.plugin.json").write_text(
        json.dumps(
            {
                "id": "legacy-hooks",
                "plugin_type": "pipeline_hook",
                "entry": "plugin:PLUGIN_CLASS",
                "capabilities": ["hooks"],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_manifest(root)
    assert manifest["capability_mode"] == "compatibility"
    assert {"project_read", "project_write", "model_access"} <= set(
        manifest["capabilities"]
    )


def test_install_rejects_path_traversal(tmp_path: Path) -> None:
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../evil.txt", "x")
    with pytest.raises(ManifestError):
        install_plugin_zip(tmp_path, zpath.read_bytes())


def test_install_rejects_zip_with_too_many_members(tmp_path: Path) -> None:
    zpath = tmp_path / "many.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for index in range(MAX_ZIP_FILES + 1):
            zf.writestr(f"files/{index}.txt", "")
    with pytest.raises(ManifestError, match="文件数量"):
        install_plugin_zip(tmp_path, zpath.read_bytes())


def test_nested_bundle_uses_the_same_zip_limits(tmp_path: Path) -> None:
    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested, "w") as zf:
        for index in range(MAX_ZIP_FILES + 1):
            zf.writestr(f"files/{index}.txt", "")

    root = tmp_path / "bundle-pkg"
    root.mkdir()
    (root / "inkrest.plugin.json").write_text(
        json.dumps(
            {
                "id": "bundle-limit",
                "version": "1.0.0",
                "plugin_type": "pipeline_hook",
                "entry": "plugin:PLUGIN_CLASS",
                "bundles": ["payload.zip"],
            }
        ),
        encoding="utf-8",
    )
    (root / "plugin.py").write_text("PLUGIN_CLASS = object\n", encoding="utf-8")
    (root / "payload.zip").write_bytes(nested.read_bytes())
    outer = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer, "w") as zf:
        for path in root.iterdir():
            zf.write(path, path.name)

    with pytest.raises(ManifestError, match="文件数量"):
        install_plugin_zip(tmp_path, outer.read_bytes())


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
    assert row["digest"]
    assert row["risk_level"] == "high"
    assert row["origin"] == "plugins/demo-hook"
    assert row["capability_details"]
