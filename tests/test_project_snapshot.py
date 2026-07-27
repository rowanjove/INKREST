from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.state.sqlite_store import SQLiteStateStore


def _seed_project(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "workspace" / "chapters" / "chapter_001" / "reports").mkdir(
        parents=True
    )
    (root / "config" / "pipeline.yaml").write_text(
        "schema_version: 2\n"
        "runtime:\n  max_workers: 2\n"
        "chapter:\n  default_target_chars: [1200, 2200]\n"
        "llm:\n  provider: static\n"
        "embedding:\n  provider: stub\n",
        encoding="utf-8",
    )
    (root / "config" / "project_meta.json").write_text(
        json.dumps({"workflow_mode": "factory", "target_chapters": 20}),
        encoding="utf-8",
    )
    (root / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "chosen_title": "快照测试",
                "target_chapters": 20,
                "macro_outline": [
                    {"arc_id": "arc-1", "chapters": "1-10"},
                    {"arc_id": "arc-2", "chapters": "11-20"},
                ],
            }
        ),
        encoding="utf-8",
    )
    quality = root / "workspace" / "chapters" / "chapter_001" / "reports" / "quality.json"
    quality.write_text(
        json.dumps({"overall_pass": True, "guard_summary": {"overall_status": "PASS"}}),
        encoding="utf-8",
    )


def test_project_snapshot_aggregates_every_v2_source(tmp_path: Path) -> None:
    root = tmp_path / "projects" / "book-1"
    _seed_project(root)
    store = SQLiteStateStore(root)
    store.task_repository.create_task(
        task_id="active-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "002"},
    )
    finished = store.task_repository.create_task(
        task_id="done-1",
        project_id="book-1",
        task_type=TaskType.EXPORT,
        payload={},
    )
    claimed = store.task_repository.claim_task(finished.id)
    assert claimed and claimed.claim_token
    running = store.task_repository.start_task(finished.id, claimed.claim_token)
    store.task_repository.finish_task(
        running.id,
        claimed.claim_token,
        status=TaskStatus.SUCCEEDED,
    )

    from novel_agent.services.project_snapshot import build_project_snapshot

    snapshot = build_project_snapshot(
        root,
        project_id="book-1",
        project_info={"name": "快照测试", "description": "统一契约"},
    )
    payload = snapshot.model_dump(mode="json")

    assert set(payload) == {
        "project",
        "workflow_mode",
        "readiness",
        "outline_progress",
        "chapter_progress",
        "active_tasks",
        "blocking_issues",
        "quality_summary",
        "cost_summary",
        "next_actions",
        "updated_at",
    }
    assert payload["project"]["id"] == "book-1"
    assert payload["workflow_mode"] == "factory"
    assert payload["outline_progress"]["arc_count"] == 2
    assert [task["id"] for task in payload["active_tasks"]] == ["active-1"]
    assert payload["quality_summary"]["total_reports"] == 1
    assert payload["cost_summary"]["persisted"]["call_count"] == 0
    assert payload["next_actions"]
    assert payload["next_actions"][0]["target"] == "/production?tab=runs"
    assert datetime.fromisoformat(payload["updated_at"])


def test_invalid_config_is_a_blocking_issue_not_a_snapshot_crash(tmp_path: Path) -> None:
    root = tmp_path / "projects" / "broken"
    (root / "config").mkdir(parents=True)
    (root / "config" / "pipeline.yaml").write_text("runtime: [broken", encoding="utf-8")

    from novel_agent.services.project_snapshot import build_project_snapshot

    snapshot = build_project_snapshot(root, project_id="broken")

    assert snapshot.readiness["ok"] is False
    assert any(
        issue["code"] == "config_invalid" for issue in snapshot.blocking_issues
    )
    assert snapshot.active_tasks == []


def test_snapshot_tolerates_valid_json_with_malformed_optional_outline_fields(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects" / "malformed-fields"
    (root / "workspace").mkdir(parents=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps({"target_chapters": "many", "scale_profile": []}),
        encoding="utf-8",
    )
    (root / "config").mkdir(parents=True)
    (root / "config" / "project_meta.json").write_text(
        json.dumps({"scale_profile": "bad"}),
        encoding="utf-8",
    )

    from novel_agent.services.project_snapshot import build_project_snapshot

    snapshot = build_project_snapshot(root, project_id="malformed-fields")

    assert snapshot.outline_progress["target_chapters"] == 0
    assert snapshot.project["scale"] == ""
