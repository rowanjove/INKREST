"""Synthetic 20-chapter state machine. No LLM calls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from novel_agent.agents.base import StaticLLM
from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.services.chapter_gate_rerun import run_gate_only_rerun
from novel_agent.services.hierarchical_summary import assemble_hierarchical_context
from novel_agent.services.longform_synth import seed_synthetic_project
from novel_agent.state.sqlite_store import SQLiteStateStore

ACTION_PROSE = (
    "林澈推开出租屋的门，雨水顺着袖口滴在地上。他走进屋里，看到桌上那封信。\n\n"
    "他伸手拿起信，转身走到窗边说：“今晚必须离开。”灯闪了两下，他拉开门走了出去。"
)


def _prepare_book(root: Path) -> SQLiteStateStore:
    seed_synthetic_project(root, chapters=20, seed=7, scale="long", title="二十章状态机")
    (root / "config" / "pipeline.yaml").write_text(
        "chapter:\n  quality_mode: report_only\n  persona_evaluations: off\n"
        "  default_target_chars: [20, 200]\n"
        "llm:\n  provider: static\n"
        "runtime:\n  interactive: false\n  auto_length_fix_on_gate: false\n",
        encoding="utf-8",
    )
    meta_path = root / "config" / "project_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["factory_mode"] = "newbie_auto"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return SQLiteStateStore(root)


def test_synthetic_20_task_lease_is_exclusive(tmp_path: Path):
    store = _prepare_book(tmp_path)
    created = store.task_repository.create_task(
        task_id="synth-20-lease",
        project_id="synth-20",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "012"},
    )
    first = store.task_repository.claim_task(created.id, lease_seconds=30)
    second = store.task_repository.claim_task(created.id, lease_seconds=30)
    assert first is not None
    assert first.status is TaskStatus.CLAIMED
    assert first.lease_expires_at
    assert second is None
    assert len(store.list_manuscript_documents()) == 20


def test_synthetic_20_supersede_does_not_leak_into_later_context(tmp_path: Path):
    store = _prepare_book(tmp_path)
    store.upsert_narrative_events(
        "005",
        [{"id": "E-OLD", "summary": "林澈把信烧掉了。", "characters": ["主角"]}],
        source_revision_id="rev-1",
    )
    store.upsert_narrative_events(
        "005",
        [{"id": "E-NEW", "summary": "林澈把信塞进大衣。", "characters": ["主角"]}],
        source_revision_id="rev-2",
    )
    current = store.list_narrative_events(chapter_id="005")
    assert {item["event_id"] for item in current} == {"E-NEW"}
    context = ContextBuilderAgent(tmp_path).build(
        "继续追查",
        {
            "scene_id": "010-01",
            "chapter_id": "010",
            "characters": ["主角"],
            "purpose": "带着信离开",
        },
        plan={"chapter_id": "010"},
    )
    assert "烧掉" not in context
    assert "塞进大衣" in context or "E-NEW" in context


def test_synthetic_20_gate_recovers_and_revisions_stay_unified(tmp_path: Path):
    store = _prepare_book(tmp_path)
    store.save_chapter_summary(
        "018",
        "铜钥匙已交沈砚。",
        tmp_path / "workspace" / "chapters" / "chapter_018" / "chapter_summary.md",
    )
    packed = assemble_hierarchical_context(tmp_path, "020")
    assert "铜钥匙已交沈砚" in packed["compiled_prompt_block"]

    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_012"
    reports = chapter_dir / "reports"
    reports.mkdir(parents=True)
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "第十二章", "chapter_goal": "取信离开"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (reports / "audit.json").write_text(
        json.dumps({"status": "ok", "risk_level": "低", "issues": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "chapter_final.txt").write_text("", encoding="utf-8")
    orch = NovelOrchestrator(PipelineConfig(root_dir=tmp_path, llm=StaticLLM(responses={})))
    empty = asyncio.run(orch.chapter_post.write_quality_report("012", "", reports))
    assert empty.blocked is True
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "012",
                "last_stage": "quality_blocked",
                "completed_stages": ["writer", "auditor"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chapter_dir / "chapter_final.txt").write_text(ACTION_PROSE, encoding="utf-8")
    recovered = asyncio.run(run_gate_only_rerun(orch, "012"))
    checkpoint = json.loads((chapter_dir / "checkpoint.json").read_text(encoding="utf-8"))
    gate = json.loads((reports / "unified_gate.json").read_text(encoding="utf-8"))
    assert recovered.chapter_id == "012"
    assert checkpoint["last_stage"] != "quality_blocked"
    assert gate["blocked"] is False

    document = store.get_manuscript_document("020")
    versions = store.list_chapter_versions("020")
    active = next(item for item in versions if item.get("is_active") in (1, True))
    assert document is not None
    assert active["revision"] == document["revision"]
