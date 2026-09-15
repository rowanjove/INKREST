"""Regression tests for runbook recovery: persist, resume, compliance, pause clear."""

from __future__ import annotations

import json
from pathlib import Path

from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.quality.quality_rewrite import build_issue_driven_patch_prompt
from novel_agent.services.arc_queue import load_arc_progress, record_novel_batch_paused
from novel_agent.services.production_workspace import _task_view
from novel_agent.services.quality_review import build_quality_review_queue
from novel_agent.services.unified_gate import persist_chapter_final_text
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.tasks import TaskManager


def test_persist_chapter_final_text_overwrites_disk(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    stale = chapter_dir / "chapter_final.txt"
    stale.write_text("旧稿", encoding="utf-8")

    path = persist_chapter_final_text(chapter_dir, "修订后的正文")

    assert path == stale
    assert stale.read_text(encoding="utf-8") == "修订后的正文"


def test_issue_driven_prompt_includes_sensitive_word_from_audit() -> None:
    report = {
        "checks": {},
        "audit": {
            "issues": [
                {
                    "type": "sensitive_word_hit",
                    "severity": "high",
                    "audit_class": "CRITICAL",
                    "target_text": "违禁词",
                    "text": "敏感词违规：'违禁词'",
                    "why": "命中发布词库",
                    "fix": "用合规词替换该片段",
                }
            ]
        },
    }
    prompt = build_issue_driven_patch_prompt(report, "正文含违禁词在这里。")
    assert "违禁词" in prompt
    assert "敏感词" in prompt or "合规" in prompt


def test_update_task_status_running_claims_paused_task(tmp_path: Path) -> None:
    manager = TaskManager(tmp_path)
    repo = manager.task_repository
    repo.create_task(
        task_id="pause-1",
        project_id=tmp_path.name,
        task_type=TaskType.NOVEL_CONTINUE,
        payload={"goal": "继续写书", "max_chapters": 3},
        max_attempts=3,
    )
    claimed = repo.claim_task("pause-1")
    assert claimed and claimed.claim_token
    repo.start_task("pause-1", claimed.claim_token)
    repo.finish_task(
        "pause-1",
        claimed.claim_token,
        status=TaskStatus.PAUSED,
        reason="quality_blocked",
    )
    manager._claim_tokens.pop("pause-1", None)

    updated = manager._update_task_status("pause-1", "running")

    row = repo.get_task("pause-1")
    assert row is not None
    assert row.status is TaskStatus.RUNNING
    assert row.claim_token
    assert manager._claim_tokens["pause-1"] == row.claim_token
    assert updated["status"] == "running"


def test_runner_for_paused_gate_only_and_batch(tmp_path: Path) -> None:
    manager = TaskManager(tmp_path)
    gate_runner = manager._runner_for_task(
        {
            "id": "gate-1",
            "task_type": TaskType.CHAPTER.value,
            "payload": {"chapter_id": "003", "mode": "gate_only", "goal": "gate_only:003"},
        }
    )
    batch_runner = manager._runner_for_task(
        {
            "id": "batch-1",
            "task_type": TaskType.CHAPTER_BATCH.value,
            "payload": {"chapters": [{"chapter_id": "001"}], "dry_run": True},
        }
    )
    assert gate_runner.func.__name__ == "_run_chapter_gate_only"
    assert batch_runner.func.__name__ == "_run_batch"


def test_paused_production_task_offers_resume_not_cancel(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    record = store.task_repository.create_task(
        task_id="cont-1",
        project_id=tmp_path.name,
        task_type=TaskType.NOVEL_CONTINUE,
        payload={"goal": "继续写书"},
    )
    claimed = store.task_repository.claim_task("cont-1")
    store.task_repository.start_task("cont-1", claimed.claim_token)
    paused = store.task_repository.finish_task(
        "cont-1",
        claimed.claim_token,
        status=TaskStatus.PAUSED,
        reason="user_paused",
    )
    view = _task_view(paused)
    assert view["status"] == "paused"
    assert view["recovery_action"] == "resume"


def test_paused_audit_task_resumes_same_durable_task(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    store.task_repository.create_task(
        task_id="audit-1",
        project_id=tmp_path.name,
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "003", "goal": "继续审校"},
    )
    claimed = store.task_repository.claim_task("audit-1")
    store.task_repository.start_task("audit-1", claimed.claim_token)
    store.task_repository.heartbeat(
        "audit-1",
        claimed.claim_token,
        checkpoint={"step": "auditor", "resumable_from": "audit"},
    )
    paused = store.task_repository.finish_task(
        "audit-1",
        claimed.claim_token,
        status=TaskStatus.PAUSED,
        reason="user_paused",
    )

    assert _task_view(paused)["recovery_action"] == "resume"


def test_quality_review_summary_splits_blocking_and_advisory(tmp_path: Path) -> None:
    chapters = tmp_path / "workspace" / "chapters"
    blocked = chapters / "chapter_001" / "reports"
    advisory = chapters / "chapter_002" / "reports"
    blocked.mkdir(parents=True)
    advisory.mkdir(parents=True)
    (chapters / "chapter_001" / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "last_stage": "quality_blocked",
                "completed_stages": ["generation"],
            }
        ),
        encoding="utf-8",
    )
    (blocked / "quality.json").write_text(
        json.dumps(
            {
                "guard_summary": {"overall_status": "FAIL", "blocked_by": ["layout"]},
                "chapter_score": {"keep": False, "score": 4.0},
            }
        ),
        encoding="utf-8",
    )
    (advisory / "quality.json").write_text(
        json.dumps(
            {
                "guard_summary": {"overall_status": "WARN", "blocked_by": []},
                "chapter_score": {"keep": True, "score": 9.1},
                "checks": {"style": {"pass": False, "level": "fail", "details": ["套话"]}},
            }
        ),
        encoding="utf-8",
    )

    queue = build_quality_review_queue(tmp_path)
    assert queue["summary"]["blocking_items"] == 1
    assert queue["summary"]["advisory_items"] == 1
    stages = {item["chapter_id"]: item["stage"] for item in queue["items"]}
    assert stages["001"] == "quality_blocked"
    assert stages["002"] == "quality_review"


def test_sensitive_word_patches_replace_hits() -> None:
    from novel_agent.scripts.sensitive_scan import apply_sensitive_word_patches

    text = apply_sensitive_word_patches(
        "他骂了一句禁词一，又说禁词一。",
        ["禁词一"],
        replacements={"禁词一": "某话"},
    )
    assert "禁词一" not in text
    assert "某话" in text


def test_refresh_audit_after_patch_drops_fixed_sensitive_issue(tmp_path: Path) -> None:
    import asyncio
    from types import SimpleNamespace

    from novel_agent.phases.base import ChapterContext
    from novel_agent.services.unified_gate import refresh_audit_after_patch

    class Auditor:
        def audit(self, text, **_kwargs):
            return {"status": "ok", "risk_level": "低", "issues": []}

    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    reports_dir = chapter_dir / "reports"
    reports_dir.mkdir(parents=True)
    (tmp_path / "assets").mkdir(parents=True)
    (tmp_path / "assets" / "sensitive_words.txt").write_text("禁词一\n", encoding="utf-8")
    orch = SimpleNamespace(
        root_dir=tmp_path,
        auditor=Auditor(),
        state_manager=SimpleNamespace(get_state=lambda: {}),
        _write_json=lambda path, data: path.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        ),
    )
    ctx = ChapterContext(
        chapter_id="001",
        chapter_goal="g",
        chapter_dir=chapter_dir,
        scenes_dir=chapter_dir / "scenes",
        reports_dir=reports_dir,
        plan={"target_chars": [2, 200]},
        final_text="林澈推开门走了进去。",
        audit={
            "status": "ok",
            "risk_level": "高",
            "issues": [
                {
                    "type": "sensitive_word_hit",
                    "audit_class": "CRITICAL",
                    "target_text": "禁词一",
                }
            ],
        },
    )
    audit, updated = asyncio.run(refresh_audit_after_patch(orch, ctx))
    assert not any(
        isinstance(item, dict) and item.get("type") == "sensitive_word_hit"
        for item in (audit.get("issues") or [])
    )
    assert updated.audit == audit


def test_prioritize_retry_briefs_puts_pending_first(tmp_path: Path) -> None:
    from novel_agent.services.batch_retry_queue import (
        prioritize_retry_briefs,
        record_batch_retry,
    )

    record_batch_retry(tmp_path, chapter_id="003", reason="quality_or_gate_failure")
    briefs = [
        {"chapter_id": "001", "chapter_goal": "a"},
        {"chapter_id": "003", "chapter_goal": "c"},
        {"chapter_id": "002", "chapter_goal": "b"},
    ]
    ordered = prioritize_retry_briefs(tmp_path, briefs)
    assert [row["chapter_id"] for row in ordered] == ["003", "001", "002"]


def test_should_retry_gate_only_for_blocked_chapter_with_text(tmp_path: Path) -> None:
    from novel_agent.services.chapter_gate_rerun import should_retry_gate_only

    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_004"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter_final.txt").write_text("有正文", encoding="utf-8")
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps({"chapter_id": "004", "last_stage": "quality_blocked"}),
        encoding="utf-8",
    )
    assert should_retry_gate_only(tmp_path, "004") is True
    assert should_retry_gate_only(tmp_path, "005") is False


def test_goal_change_does_not_reuse_old_generation(tmp_path: Path) -> None:
    import asyncio

    from novel_agent.agents.base import StaticLLM
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.pipeline import PipelineConfig

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "pipeline.yaml").write_text(
        "chapter:\n  quality_mode: report_only\n  persona_evaluations: off\n"
        "  default_target_chars: [20, 400]\n"
        "llm:\n  provider: static\n"
        "runtime:\n  interactive: false\n  auto_length_fix_on_gate: false\n",
        encoding="utf-8",
    )
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    scenes = chapter_dir / "scenes"
    scenes.mkdir(parents=True)
    (chapter_dir / "chapter_final.txt").write_text("旧稿必须被替换", encoding="utf-8")
    (scenes / "scene_001-01.txt").write_text("旧稿必须被替换", encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "chapter_title": "旧",
                "chapter_goal": "旧目标",
                "target_chars": [20, 80],
                "scenes": [
                    {
                        "scene_id": "001-01",
                        "target_chars": [10, 60],
                        "purpose": "旧",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "completed_stages": ["generation"],
                "last_stage": "generation",
                "goal_hash": "deadbeefdeadbeef",
            }
        ),
        encoding="utf-8",
    )
    new_prose = (
        "林澈推开出租屋的门，雨水顺着袖口滴在地上。他走进屋里，看到桌上那封信。\n\n"
        "他伸手拿起信，转身走到窗边说：“今晚必须离开。”灯闪了两下，他拉开门走了出去。"
    )
    llm = StaticLLM(
        responses={
            "planner": json.dumps(
                {
                    "chapter_id": "001",
                    "chapter_title": "雨夜",
                    "chapter_goal": "新目标",
                    "target_chars": [20, 80],
                    "scenes": [
                        {
                            "scene_id": "001-01",
                            "target_chars": [10, 60],
                            "purpose": "开门取信离开",
                            "must_include": ["信"],
                            "must_not_include": [],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "writer": new_prose,
            "stitch_editor": new_prose,
            "style_editor": new_prose,
            "continuity_checker": '{"pass":true,"issues":[]}',
            "auditor": json.dumps(
                {"risk_level": "低", "issues": [], "state_update": {"events": []}},
                ensure_ascii=False,
            ),
            "chapter_summary": "## 章节概述\n取信离开。",
        }
    )
    orch = NovelOrchestrator(PipelineConfig(root_dir=tmp_path, llm=llm))
    asyncio.run(orch.arun_chapter("001", "新目标：取信后离开"))
    text = (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8")
    assert "旧稿必须被替换" not in text
    assert "信" in text


def test_auto_resumable_task_includes_continue_and_gate_only() -> None:
    from web.tasks import _is_auto_resumable_task

    assert _is_auto_resumable_task(
        {
            "chapter_id": "001",
            "task_type": "chapter",
            "mode": "gate_only",
            "status": "pending",
        }
    )
    assert _is_auto_resumable_task(
        {"task_type": "novel_continue", "status": "pending", "chapter_id": ""}
    )
    assert not _is_auto_resumable_task(
        {"task_type": "novel_run", "status": "pending", "chapter_id": ""}
    )


def test_gate_success_clears_quality_batch_pause(tmp_path: Path) -> None:
    from novel_agent.services.chapter_gate_rerun import maybe_clear_quality_batch_pause

    record_novel_batch_paused(tmp_path, reason="quality_blocked", last_chapter="001")
    (tmp_path / "workspace" / "chapters" / "chapter_001").mkdir(parents=True)
    (tmp_path / "workspace" / "chapters" / "chapter_001" / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "last_stage": "unified_gate",
                "resolved_at": "2026-09-05T00:00:00",
                "completed_stages": ["generation", "audit", "unified_gate"],
            }
        ),
        encoding="utf-8",
    )

    maybe_clear_quality_batch_pause(tmp_path)
    progress = load_arc_progress(tmp_path)
    assert progress.get("status") != "paused"
    assert not progress.get("pause_reason")
