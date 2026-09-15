import pytest
from pathlib import Path
from plugins.script_murder.package.database import DatabaseManager
from plugins.script_murder.package.schemas import (
    CharacterProfile,
    ClueItem,
    ProjectMeta,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    return DatabaseManager(tmp_path)


def test_project_crud_and_isolation(temp_db: DatabaseManager):
    meta = ProjectMeta(
        id="proj_alpha",
        title="海妖之眼",
        player_count=5,
        genre=["变格推理"],
    )
    ws = temp_db.create_project(meta)
    assert ws.meta.id == "proj_alpha"

    # List projects
    projs = temp_db.list_projects()
    assert len(projs) == 1
    assert projs[0]["id"] == "proj_alpha"
    assert projs[0]["title"] == "海妖之眼"

    # Load workspace
    loaded = temp_db.load_workspace("proj_alpha")
    assert loaded is not None
    assert loaded.meta.title == "海妖之眼"

    # Delete project
    assert temp_db.delete_project("proj_alpha") is True
    assert temp_db.load_workspace("proj_alpha") is None
    assert len(temp_db.list_projects()) == 0


def test_snapshot_and_restore(temp_db: DatabaseManager):
    meta = ProjectMeta(id="proj_beta", title="暴风雪山庄")
    ws = temp_db.create_project(meta)

    # Add a fact
    ws.canon.victim = "李老先生"
    ws.canon.facts.append(
        TruthFact(
            id="F001",
            title="书房发现死者",
            content="死者被发现倒在书桌旁，壁炉依然在燃烧。",
        )
    )
    temp_db.save_workspace(ws)

    # Take snapshot
    snap_id = temp_db.create_snapshot("proj_beta", "发现死者版本")
    snaps = temp_db.list_snapshots("proj_beta")
    assert len(snaps) == 1
    assert snaps[0]["snapshot_id"] == snap_id

    # Modify workspace
    ws.canon.victim = "篡改后的受害人"
    temp_db.save_workspace(ws)
    modified = temp_db.load_workspace("proj_beta")
    assert modified.canon.victim == "篡改后的受害人"

    # Restore snapshot
    restored = temp_db.restore_snapshot("proj_beta", snap_id)
    assert restored.canon.victim == "李老先生"
    assert len(restored.canon.facts) == 1
