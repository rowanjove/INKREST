"""Short-run quality gate: newbie_auto blocks L0, author_copilot does not."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from novel_agent.agents.base import StaticLLM
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.quality.settings import resolve_quality_mode

ACTION_PROSE = (
    "林澈推开出租屋的门，雨水顺着袖口滴在地上。他走进屋里，看到桌上那封信。\n\n"
    "他伸手拿起信，转身走到窗边说：“今晚必须离开。”灯闪了两下，他拉开门走了出去。"
)


def _write_project(root: Path, factory_mode: str) -> None:
    config = root / "config"
    config.mkdir(parents=True, exist_ok=True)
    (config / "project_meta.json").write_text(
        json.dumps({"factory_mode": factory_mode}, ensure_ascii=False),
        encoding="utf-8",
    )
    (config / "pipeline.yaml").write_text(
        "chapter:\n  quality_mode: report_only\n  persona_evaluations: off\n"
        "  default_target_chars: [20, 200]\n"
        "llm:\n  provider: static\n"
        "runtime:\n  interactive: false\n  auto_length_fix_on_gate: false\n",
        encoding="utf-8",
    )


def _orchestrator(root: Path) -> NovelOrchestrator:
    llm = StaticLLM(
        responses={
            "planner": json.dumps(
                {
                    "chapter_id": "001",
                    "chapter_title": "雨夜",
                    "target_chars": [20, 80],
                    "scenes": [
                        {
                            "scene_id": "001-01",
                            "target_chars": [10, 60],
                            "purpose": "开门取信离开",
                            "entry": "林澈回到出租屋",
                            "exit": "他离开",
                            "must_include": ["信", "离开"],
                            "must_not_include": [],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "chapter_planner": json.dumps(
                {
                    "chapter_id": "001",
                    "chapter_title": "雨夜",
                    "detailed_synopsis": "林澈取信后离开出租屋。",
                    "beats": [
                        {"beat_id": "B01", "function": "开场", "content": "推门进屋看到信"},
                        {"beat_id": "B02", "function": "钩子", "content": "必须连夜离开的悬念"},
                    ],
                    "handoff_to_scene_planner": {"must_include": ["信"], "must_not_include": []},
                },
                ensure_ascii=False,
            ),
            "writer": ACTION_PROSE,
            "stitch_editor": ACTION_PROSE,
            "style_editor": ACTION_PROSE,
            "continuity_checker": '{"pass":true,"issues":[]}',
            "auditor": json.dumps(
                {"risk_level": "低", "issues": [], "state_update": {"events": []}},
                ensure_ascii=False,
            ),
            "chapter_summary": "## 章节概述\n取信离开。\n\n## 人物发展\n- 林澈：警觉。",
        }
    )
    return NovelOrchestrator(PipelineConfig(root_dir=root, llm=llm))


def test_newbie_auto_short_run_blocks_empty_and_allows_action_prose(tmp_path: Path):
    _write_project(tmp_path, "newbie_auto")
    assert resolve_quality_mode(tmp_path) == "block_on_fail"
    orch = _orchestrator(tmp_path)
    reports = tmp_path / "workspace" / "chapters" / "chapter_001" / "reports"
    reports.mkdir(parents=True)

    empty = asyncio.run(orch.chapter_post.write_quality_report("001", "", reports))
    assert empty.blocked is True
    assert empty.report["mode"] == "block_on_fail"

    ok = asyncio.run(orch.chapter_post.write_quality_report("001", ACTION_PROSE, reports))
    assert ok.blocked is False
    assert ok.report["mode"] == "block_on_fail"


def test_author_copilot_short_run_never_blocks_empty_text(tmp_path: Path):
    _write_project(tmp_path, "author_copilot")
    assert resolve_quality_mode(tmp_path) == "report_only"
    orch = _orchestrator(tmp_path)
    reports = tmp_path / "workspace" / "chapters" / "chapter_001" / "reports"
    reports.mkdir(parents=True)
    empty = asyncio.run(orch.chapter_post.write_quality_report("001", "", reports))
    assert empty.blocked is False
    assert empty.report["overall_pass"] is False


def test_newbie_auto_run_chapter_records_unblocked_gate(tmp_path: Path):
    _write_project(tmp_path, "newbie_auto")
    orch = _orchestrator(tmp_path)
    result = orch.run_chapter("001", "林澈取信后离开。")
    gate_path = tmp_path / "workspace" / "chapters" / "chapter_001" / "reports" / "unified_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    assert result.chapter_id == "001"
    assert gate["quality"]["mode"] == "block_on_fail"
    assert gate["blocked"] is False
    assert gate["quality"]["chapter_score"]["keep"] is True
    assert gate["quality"]["chapter_score"]["score"] >= 6


def test_l0_block_checkpoint_then_rerun_gate_recovers(tmp_path: Path):
    _write_project(tmp_path, "newbie_auto")
    orch = _orchestrator(tmp_path)
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    reports = chapter_dir / "reports"
    reports.mkdir(parents=True)
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "雨夜", "chapter_goal": "取信离开"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (reports / "audit.json").write_text(
        json.dumps({"status": "ok", "risk_level": "低", "issues": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "chapter_final.txt").write_text("", encoding="utf-8")
    empty = asyncio.run(orch.chapter_post.write_quality_report("001", "", reports))
    assert empty.blocked is True
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "last_stage": "quality_blocked",
                "completed_stages": ["writer", "auditor"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (chapter_dir / "chapter_final.txt").write_text(ACTION_PROSE, encoding="utf-8")
    from novel_agent.services.chapter_gate_rerun import run_gate_only_rerun

    recovered = asyncio.run(run_gate_only_rerun(orch, "001"))
    checkpoint = json.loads((chapter_dir / "checkpoint.json").read_text(encoding="utf-8"))
    gate = json.loads((reports / "unified_gate.json").read_text(encoding="utf-8"))
    assert recovered.chapter_id == "001"
    assert checkpoint["last_stage"] != "quality_blocked"
    assert gate["blocked"] is False
    assert gate["quality"]["chapter_score"]["keep"] is True
