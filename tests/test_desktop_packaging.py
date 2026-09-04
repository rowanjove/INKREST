from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_bundle_manifest import check_tree


ROOT = Path(__file__).resolve().parents[1]


def test_backend_build_uses_supported_python_selector() -> None:
    package = json.loads(
        (ROOT / "web" / "frontend" / "package.json").read_text(encoding="utf-8")
    )

    assert package["scripts"]["build:backend"] == (
        "node ../../scripts/build_desktop_backend.mjs"
    )
    assert package["scripts"]["smoke:electron:packaged"] == (
        "node scripts/smoke-packaged-electron.mjs"
    )

    launcher = (ROOT / "scripts" / "build_desktop_backend.mjs").read_text(
        encoding="utf-8"
    )
    assert "assert (3, 11) <= sys.version_info[:2] < (3, 13)" in launcher
    assert "import novel_agent.exporters" in launcher
    assert "'reportlab'" in launcher
    assert "'docx'" in launcher
    assert "'novel_agent'" in launcher
    assert "'build/pyinstaller-work-v2'" in launcher


def test_pyinstaller_is_declared_as_a_build_dependency() -> None:
    requirements = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")

    assert "pyinstaller" in requirements.casefold()


def test_bundle_manifest_rejects_runtime_data_and_secrets(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    (bundle / "resources" / "data").mkdir(parents=True)
    (bundle / "resources" / "data" / "state.sqlite3").write_bytes(b"sqlite")
    (bundle / "resources" / ".env.local").write_text("TOKEN=secret", encoding="utf-8")

    issues = check_tree(bundle)

    assert "resources\\data" in issues or "resources/data" in issues
    assert "resources\\.env.local" in issues or "resources/.env.local" in issues


def test_bundle_manifest_allows_packaged_demo_workspace(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    demo = (
        bundle
        / "resources"
        / "templates"
        / "assets"
        / "demo_projects"
        / "demo"
        / "workspace"
    )
    demo.mkdir(parents=True)
    (demo / "outline.json").write_text("{}", encoding="utf-8")

    assert check_tree(bundle) == []


def test_bundle_manifest_allows_demo_pipeline_and_sqlite_fixtures(tmp_path: Path) -> None:
    demo = (
        tmp_path
        / "bundle"
        / "resources"
        / "templates"
        / "assets"
        / "demo_projects"
        / "demo"
    )
    (demo / "config").mkdir(parents=True)
    (demo / "data").mkdir(parents=True)
    (demo / "config" / "pipeline.yaml").write_text("runtime: {}\n", encoding="utf-8")
    (demo / "data" / "novel.sqlite").write_bytes(b"sqlite")
    (demo / "config" / "models.json").write_text("{}", encoding="utf-8")

    issues = check_tree(tmp_path / "bundle")
    assert not any(item.endswith("pipeline.yaml") for item in issues)
    assert not any(item.endswith("novel.sqlite") for item in issues)
    assert any(item.endswith("models.json") for item in issues)
