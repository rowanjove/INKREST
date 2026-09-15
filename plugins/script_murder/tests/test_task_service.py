import time
from pathlib import Path

from plugins.script_murder.package.agents.orchestrator import ScriptMurderOrchestrator
from plugins.script_murder.package.database import DatabaseManager
from plugins.script_murder.package.services import (
    CanonService,
    ModelService,
    PlaytestService,
    ProjectService,
    ScriptMurderTaskService,
)
from plugins.script_murder.package.schemas import CharacterProfile, TruthCanon, TruthFact


def _services(tmp_path: Path):
    db = DatabaseManager(tmp_path)
    projects = ProjectService(db)
    canon = CanonService(projects)
    model = ModelService(tmp_path)
    orchestrator = ScriptMurderOrchestrator(model)
    playtest = PlaytestService(model)
    tasks = ScriptMurderTaskService(projects, canon, orchestrator, playtest)
    return db, projects, tasks


def _wait(tasks: ScriptMurderTaskService, task_id: str):
    deadline = time.time() + 5
    while time.time() < deadline:
        task = tasks.get(task_id)
        if task and task.status in {"succeeded", "failed", "cancelled", "superseded"}:
            return task
        time.sleep(0.02)
    raise AssertionError("task did not finish")


def test_persisted_validation_task(tmp_path: Path):
    _db, projects, tasks = _services(tmp_path)
    projects.create_project({"title": "任务测试"})
    task = tasks.submit(projects.list_projects()[0]["id"], "validate")
    finished = _wait(tasks, task.id)
    assert finished.status == "succeeded"
    assert "issues" in finished.result
    tasks.shutdown()


def test_generation_task_applies_only_after_success(tmp_path: Path):
    _db, projects, tasks = _services(tmp_path)
    ws = projects.create_project({"title": "简报测试"})
    task = tasks.submit(ws.meta.id, "brief", {"inspiration": "暴雨港口密室案"})
    finished = _wait(tasks, task.id)
    assert finished.status == "succeeded"
    updated = projects.get_workspace(ws.meta.id)
    assert updated is not None
    assert updated.brief.get("title")
    assert updated.revision > ws.revision
    tasks.shutdown()


def test_parallel_script_tasks_do_not_lose_character_edits(tmp_path: Path):
    _db, projects, tasks = _services(tmp_path)
    ws = projects.create_project({"title": "并发剧本", "player_count": 2})
    canon = TruthCanon(
        victim="受害者",
        killer="CHAR_02",
        cause_of_death="钝器伤",
        crime_scene="仓库",
        crime_method="重击",
        true_motive="灭口",
        facts=[TruthFact(id="F001", title="案发事实", content="受害者在仓库内死亡")],
    )
    canon_svc = CanonService(projects)
    canon_svc.update_canon(ws.meta.id, canon.model_dump())
    canon_svc.replace_characters(
        ws.meta.id,
        [
            CharacterProfile(id="CHAR_01", name="甲", public_identity="记者"),
            CharacterProfile(id="CHAR_02", name="乙", public_identity="经理"),
        ],
    )
    ids = [
        tasks.submit(ws.meta.id, "script", {"character_id": cid, "act": 1}).id
        for cid in ("CHAR_01", "CHAR_02")
    ]
    finished = [_wait(tasks, task_id) for task_id in ids]
    assert all(task.status == "succeeded" for task in finished)
    updated = projects.get_workspace(ws.meta.id)
    assert updated is not None
    assert all("act_1" in character.script_acts for character in updated.characters)
    tasks.shutdown()


def test_preview_candidate_requires_explicit_accept(tmp_path: Path):
    _db, projects, tasks = _services(tmp_path)
    ws = projects.create_project({"title": "候选测试"})
    task = tasks.submit(ws.meta.id, "brief", {"inspiration": "港口案", "preview_only": True})
    finished = _wait(tasks, task.id)
    assert finished.status == "succeeded"
    assert finished.apply_state == "pending"
    assert projects.get_workspace(ws.meta.id).brief == {}
    accepted = tasks.accept(task.id)
    assert accepted is not None and accepted.apply_state == "applied"
    assert projects.get_workspace(ws.meta.id).brief.get("title")
    tasks.shutdown()
