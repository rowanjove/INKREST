"""Project registry lifecycle regression tests."""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from web.project_manager import ProjectManager


def test_missing_active_project_is_cleared_without_rehydrating_directory(tmp_path: Path) -> None:
    project_id = "missing-book"
    (tmp_path / "projects.json").write_text(
        json.dumps(
            {
                "active_id": project_id,
                "projects": {project_id: {"name": "Missing book"}},
            }
        ),
        encoding="utf-8",
    )
    project_dir = tmp_path / "projects" / project_id
    assert not project_dir.exists()

    manager = ProjectManager(tmp_path)

    assert manager.get_active_id() is None
    assert not project_dir.exists()
    registry = json.loads((tmp_path / "projects.json").read_text(encoding="utf-8"))
    assert registry["active_id"] is None
    assert project_id in registry["projects"]


def test_switch_project_rejects_registered_but_missing_directory(tmp_path: Path) -> None:
    project_id = "missing-book"
    (tmp_path / "projects.json").write_text(
        json.dumps({"active_id": None, "projects": {project_id: {"name": "Missing book"}}}),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as exc_info:
        ProjectManager(tmp_path).switch_project(project_id)

    assert exc_info.value.status_code == 404


def test_activate_project_does_not_rehydrate_missing_directory(tmp_path: Path, monkeypatch) -> None:
    import web.context as context

    monkeypatch.setattr(context, "BASE_DIR", tmp_path)
    monkeypatch.setattr(context, "_active_project_id", None)

    with pytest.raises(HTTPException) as exc_info:
        context.activate_project("missing-book")

    assert exc_info.value.status_code == 404
    assert not (tmp_path / "projects" / "missing-book").exists()
