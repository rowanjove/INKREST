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


def test_next_actions_does_not_navigate_readiness_issues_to_reviews() -> None:
    from novel_agent.services.project_snapshot import _next_actions

    readiness = {"ok": False}
    blocking_issues = [
        {"code": "engine", "source": "readiness", "label": "日常模型可用"},
        {"code": "outline", "source": "readiness", "label": "已生成并保存大纲"},
        {"code": "assets", "source": "readiness", "label": "核心写作资产齐全"},
    ]
    actions = _next_actions(readiness, blocking_issues, [], {"chosen_title": "测试作品"})
    targets = {a["id"]: a["target"] for a in actions}

    assert "resolve_blocking_issues" not in targets
    assert targets.get("configure_model") == "/config#models-providers"
    assert targets.get("complete_outline") == "/outline"
    assert targets.get("complete_assets") == "/assets"


def test_next_actions_cover_data_and_corrupt_outline_blockers() -> None:
    from novel_agent.services.project_snapshot import _next_actions

    actions = _next_actions(
        {"ok": False},
        [
            {"code": "legacy_schema", "source": "tasks", "label": "旧数据库"},
            {"code": "outline_invalid", "source": "outline", "label": "大纲损坏"},
        ],
        [],
        {"chosen_title": "测试作品"},
    )
    targets = {action["id"]: action["target"] for action in actions}

    assert targets["repair_project_data"] == "/config#system-data"
    assert targets["complete_outline"] == "/outline"
    assert "continue_writing" not in targets


def test_next_actions_give_unknown_blockers_a_diagnostic_path() -> None:
    from novel_agent.services.project_snapshot import _next_actions

    actions = _next_actions(
        {"ok": False},
        [{"code": "future_blocker", "source": "future", "label": "未来阻塞"}],
        [],
        {"chosen_title": "测试作品"},
    )

    assert actions == [
        {
            "id": "inspect_blocking_issue",
            "label": "检查阻塞详情",
            "kind": "navigate",
            "target": "/config#system-data",
            "enabled": True,
        }
    ]


def test_next_actions_routes_pipeline_alerts_to_reviews() -> None:
    from novel_agent.services.project_snapshot import _next_actions

    readiness = {"ok": False}
    blocking_issues = [
        {
            "code": "quality_blocked",
            "source": "pipeline",
            "chapter_id": "002",
            "label": "第2章门禁阻断",
        }
    ]
    actions = _next_actions(readiness, blocking_issues, [], {"chosen_title": "测试作品"})
    review_actions = [a for a in actions if a["id"] == "resolve_blocking_issues"]

    assert len(review_actions) == 1
    assert review_actions[0]["target"] == "/production?tab=reviews"


def test_demo_factory_novel_template_readiness() -> None:
    from novel_agent.services.project_snapshot import build_project_snapshot

    demo_root = Path(__file__).resolve().parents[1] / "assets" / "demo_projects" / "demo-factory-novel"
    snapshot = build_project_snapshot(demo_root, project_id="demo-factory-novel")

    # 示例书大纲与资产完备，不应报大纲或资产缺失
    codes = {issue["code"] for issue in snapshot.blocking_issues}
    assert "outline" not in codes
    assert "assets" not in codes
    assert "title" not in codes

