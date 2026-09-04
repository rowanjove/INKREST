import json
from pathlib import Path
import tempfile
import pytest

from novel_agent.plugins.manifest import validate_manifest, ManifestError
from novel_agent.plugins.permissions import (
    PluginCapability,
    effective_capabilities,
    validate_declared_capabilities,
    risk_summary,
)


def _base_manifest():
    return {
        "id": "test-plugin",
        "plugin_type": "web_extension",
        "entry": "plugin:TestPlugin",
        "version": "1.0.0",
        "capabilities": ["project_catalog_read", "project_read", "ui_embed"],
    }


def test_valid_dual_region_contributions(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "library-templates",
                "title": "故事模板库",
                "surface": "library_sidebar",
                "icon": "collection",
                "view": "template-view",
                "order": 100,
                "default_visibility": "visible",
                "requires": ["project_catalog_read"],
            },
            {
                "id": "project-radar",
                "title": "伏笔雷达",
                "surface": "project_sidebar",
                "icon": "radar",
                "view": "radar-view",
                "order": 150,
                "default_visibility": "visible",
                "requires": ["project_read"],
            },
        ],
        "commands": [
            {
                "id": "scan-foreshadow",
                "title": "扫描伏笔",
                "scope": "project",
            }
        ],
    }
    normalized = validate_manifest(data, tmp_path)
    assert len(normalized["contributes"]["navigation"]) == 2
    assert normalized["contributes"]["navigation"][0]["surface"] == "library_sidebar"
    assert normalized["contributes"]["navigation"][1]["surface"] == "project_sidebar"
    assert len(normalized["contributes"]["commands"]) == 1


def test_reject_surface_both(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "bad-entry",
                "title": "错误入口",
                "surface": "both",
                "icon": "collection",
                "view": "bad-view",
            }
        ]
    }
    with pytest.raises(ManifestError, match="禁止使用 surface: 'both'"):
        validate_manifest(data, tmp_path)


def test_navigation_html_must_stay_inside_plugin(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    views = tmp_path / "views"
    views.mkdir()
    (views / "radar.html").write_text("<h2>雷达</h2>", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "radar",
                "title": "伏笔雷达",
                "surface": "project_sidebar",
                "view": "radar-view",
                "html": "views/radar.html",
                "requires": ["project_read"],
            }
        ]
    }
    normalized = validate_manifest(data, tmp_path)
    assert normalized["contributes"]["navigation"][0]["html"] == "views/radar.html"

    data["contributes"]["navigation"][0]["html"] = "../secret.html"
    with pytest.raises(ManifestError, match="html"):
        validate_manifest(data, tmp_path)


def test_reject_unknown_surface(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "bad-entry",
                "title": "错误入口",
                "surface": "custom_sidebar",
                "icon": "collection",
                "view": "bad-view",
            }
        ]
    }
    with pytest.raises(ManifestError, match="只允许 'library_sidebar' 或 'project_sidebar'"):
        validate_manifest(data, tmp_path)


def test_reject_duplicate_navigation_id(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "same-id",
                "title": "入口1",
                "surface": "library_sidebar",
                "icon": "collection",
                "view": "view-1",
            },
            {
                "id": "same-id",
                "title": "入口2",
                "surface": "project_sidebar",
                "icon": "radar",
                "view": "view-2",
            },
        ]
    }
    with pytest.raises(ManifestError, match="导航贡献项 id 重复"):
        validate_manifest(data, tmp_path)


def test_reject_path_traversal_in_view(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {
                "id": "evil-view",
                "title": "恶意视图",
                "surface": "library_sidebar",
                "icon": "collection",
                "view": "../secret",
            }
        ]
    }
    with pytest.raises(ManifestError, match="view 无效"):
        validate_manifest(data, tmp_path)


def test_reject_exceeding_surface_capacity(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    data["contributes"] = {
        "navigation": [
            {"id": "entry-1", "title": "入口一", "surface": "library_sidebar", "icon": "collection", "view": "v1"},
            {"id": "entry-2", "title": "入口二", "surface": "library_sidebar", "icon": "collection", "view": "v2"},
            {"id": "entry-3", "title": "入口三", "surface": "library_sidebar", "icon": "collection", "view": "v3"},
        ]
    }
    with pytest.raises(ManifestError, match="不能超过 2 个"):
        validate_manifest(data, tmp_path)


def test_reject_undeclared_requires_capability(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    # capabilities only has project_read, ui_embed
    data["capabilities"] = ["project_read", "ui_embed"]
    data["contributes"] = {
        "navigation": [
            {
                "id": "req-undeclared",
                "title": "越权入口",
                "surface": "library_sidebar",
                "icon": "collection",
                "view": "v1",
                "requires": ["all_projects_read"],  # not declared!
            }
        ]
    }
    with pytest.raises(ManifestError, match="未在插件 capabilities 中声明的权限"):
        validate_manifest(data, tmp_path)


def test_backward_compatibility_no_contributes(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("# dummy", encoding="utf-8")
    data = _base_manifest()
    # No "contributes" key
    normalized = validate_manifest(data, tmp_path)
    assert normalized["contributes"] == {"navigation": [], "commands": []}


def test_new_capabilities_in_permissions():
    caps = [
        PluginCapability.PROJECT_CATALOG_READ.value,
        PluginCapability.ALL_PROJECTS_READ.value,
        PluginCapability.ALL_PROJECTS_WRITE.value,
        PluginCapability.UI_EMBED.value,
    ]
    validated = validate_declared_capabilities(caps)
    assert len(validated) == 4
    summary = risk_summary([PluginCapability.ALL_PROJECTS_READ.value])
    assert "跨项目读取" in summary


def test_starter_templates_manifests_valid():
    repo_root = Path(__file__).resolve().parent.parent
    starters_dir = repo_root / "templates" / "plugin-starters"
    for starter_path in starters_dir.iterdir():
        if starter_path.is_dir() and (starter_path / "inkrest.plugin.json").is_file():
            manifest = json.loads((starter_path / "inkrest.plugin.json").read_text(encoding="utf-8"))
            normalized = validate_manifest(manifest, starter_path)
            assert "contributes" in normalized
            assert len(normalized["contributes"]["navigation"]) >= 1
