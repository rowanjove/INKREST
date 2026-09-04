import pytest
from pathlib import Path
from novel_agent.services.workspace_snapshot import (
    create_workspace_checkpoint,
    list_workspace_checkpoints,
    restore_workspace_checkpoint,
)


def test_workspace_snapshot_create_and_restore(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    assets = tmp_path / "assets"
    assets.mkdir(parents=True)

    (ws / "outline.json").write_text('{"title": "原版大纲"}', encoding="utf-8")
    (assets / "character_cards.yaml").write_text("主角: 剑修", encoding="utf-8")

    # 1. Create Checkpoint
    cp = create_workspace_checkpoint(tmp_path, label="before_run")
    assert cp["id"].startswith("cp_")
    assert "workspace/outline.json" in cp["copied_files"]
    assert "assets/character_cards.yaml" in cp["copied_files"]

    # 2. List Checkpoints
    cplist = list_workspace_checkpoints(tmp_path)
    assert len(cplist) == 1
    assert cplist[0]["id"] == cp["id"]

    # 3. Simulate accidental overwriting/corruption during generation
    (ws / "outline.json").write_text('{"title": "被损坏的大纲"}', encoding="utf-8")
    (assets / "character_cards.yaml").write_text("主角: 崩坏", encoding="utf-8")

    # 4. Restore Checkpoint
    success = restore_workspace_checkpoint(tmp_path, cp["id"])
    assert success is True

    # 5. Verify Restored Contents
    assert (ws / "outline.json").read_text(encoding="utf-8") == '{"title": "原版大纲"}'
    assert (assets / "character_cards.yaml").read_text(encoding="utf-8") == "主角: 剑修"

    # 6. Verify Path Traversal Defenses
    assert restore_workspace_checkpoint(tmp_path, "../../etc/passwd") is False
    assert restore_workspace_checkpoint(tmp_path, "../outside") is False
    assert restore_workspace_checkpoint(tmp_path, "cp_invalid/id") is False
    assert restore_workspace_checkpoint(tmp_path, "") is False
