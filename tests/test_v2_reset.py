from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from novel_agent.domain.tasks import TaskType
from novel_agent.state.schema_version import SchemaState, inspect_schema_state
from novel_agent.state.sqlite_store import SQLiteStateStore


def _project(projects_root: Path, project_id: str = "book-1") -> Path:
    root = projects_root / project_id
    for relative in ("config", "assets", "prompts", "workspace/chapters", "state", "data", "logs"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "schema_version: 2\nllm:\n  api_key: top-secret\n",
        encoding="utf-8",
    )
    (root / "config" / "models.json").write_text(
        json.dumps({"api_key": "model-secret"}),
        encoding="utf-8",
    )
    (root / "assets" / "characters.md").write_text("角色资产", encoding="utf-8")
    (root / "workspace" / "outline.json").write_text("{}", encoding="utf-8")
    (root / "workspace" / "chapters" / "old.txt").write_text("旧章节", encoding="utf-8")
    (root / "state" / "old.yaml").write_text("old: true", encoding="utf-8")
    (root / "logs" / "novel_agent.log").write_text("private log", encoding="utf-8")
    (root / "plugins").mkdir()
    (root / "plugins" / "unsafe.py").write_text("raise RuntimeError()", encoding="utf-8")
    SQLiteStateStore(root)
    return root


def test_backup_excludes_secrets_logs_plugins_and_external_symlinks(
    tmp_path: Path,
) -> None:
    projects_root = tmp_path / "projects"
    root = _project(projects_root)
    outside = tmp_path / "outside.txt"
    outside.write_text("must-not-leak", encoding="utf-8")
    link = root / "workspace" / "outside-link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        link = None

    from novel_agent.services.v2_reset import create_v2_backup

    result = create_v2_backup(
        projects_root=projects_root,
        project_root=root,
        project_id="book-1",
    )

    with zipfile.ZipFile(result.path) as archive:
        names = set(archive.namelist())
        text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if not name.endswith(".sqlite")
        )
    assert "workspace/outline.json" in names
    assert "config/pipeline.yaml" not in names
    assert "config/models.json" not in names
    assert not any(name.startswith("logs/") for name in names)
    assert not any(name.startswith("plugins/") for name in names)
    if link is not None:
        assert "workspace/outside-link.txt" not in names
    assert "top-secret" not in text
    assert "model-secret" not in text
    assert "must-not-leak" not in text
    assert result.sha256


def test_reset_preserves_project_inputs_and_only_clears_target_runtime(
    tmp_path: Path,
) -> None:
    projects_root = tmp_path / "projects"
    root = _project(projects_root)
    other = _project(projects_root, "book-2")
    (other / "workspace" / "keep.txt").write_text("keep", encoding="utf-8")

    from novel_agent.services.v2_reset import reset_project_to_v2

    result = reset_project_to_v2(
        projects_root=projects_root,
        project_root=root,
        project_id="book-1",
    )

    assert Path(result.backup.path).is_file()
    assert (root / "config" / "pipeline.yaml").is_file()
    assert (root / "assets" / "characters.md").read_text(encoding="utf-8") == "角色资产"
    assert not (root / "workspace" / "outline.json").exists()
    assert not (root / "state" / "old.yaml").exists()
    assert (root / "workspace" / "chapters").is_dir()
    assert (other / "workspace" / "keep.txt").read_text(encoding="utf-8") == "keep"
    state, version = inspect_schema_state(root / "data" / "novel.sqlite")
    assert state is SchemaState.V2
    assert version == 2


def test_reset_rejects_project_outside_projects_root(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    from novel_agent.services.v2_reset import UnsafeProjectPathError, create_v2_backup

    with pytest.raises(UnsafeProjectPathError):
        create_v2_backup(
            projects_root=projects_root,
            project_root=outside,
            project_id="outside",
        )


def test_reset_rejects_persisted_active_tasks(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    root = _project(projects_root)
    SQLiteStateStore(root).task_repository.create_task(
        task_id="still-running",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "001"},
    )

    from novel_agent.services.v2_reset import ActiveProjectTasksError, reset_project_to_v2

    with pytest.raises(ActiveProjectTasksError):
        reset_project_to_v2(
            projects_root=projects_root,
            project_root=root,
            project_id="book-1",
        )


def test_reset_rolls_back_when_runtime_swap_fails(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    root = _project(projects_root)

    from novel_agent.services.v2_reset import reset_project_to_v2

    original_replace = os.replace

    def fail_on_state(source, destination):
        if Path(source) == root / "state":
            raise OSError("simulated swap failure")
        return original_replace(source, destination)

    with patch("novel_agent.services.v2_reset.os.replace", side_effect=fail_on_state):
        with pytest.raises(OSError, match="simulated"):
            reset_project_to_v2(
                projects_root=projects_root,
                project_root=root,
                project_id="book-1",
            )

    assert (root / "workspace" / "outline.json").is_file()
    assert (root / "state" / "old.yaml").is_file()
    assert (root / "data" / "novel.sqlite").is_file()
