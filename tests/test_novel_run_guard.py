"""Tests for novel_run_guard pre-flight checks."""

import json
from pathlib import Path

from novel_agent.services.arc_queue import record_novel_batch_paused
from novel_agent.services.novel_run_guard import (
    _engine_ready,
    build_readiness_report,
    validate_novel_continue,
)
from novel_agent.services.outline_sync import mark_arcs_synced_with_outline


def _seed_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 20, encoding="utf-8")
    outline = {
        "chosen_title": "测试书",
        "target_chapters": 10,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-5", "goal": "g"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps({"arc_id": "A01", "chapters": [{"chapter_id": "001", "goal": "a"}]}),
        encoding="utf-8",
    )
    mark_arcs_synced_with_outline(root)


def test_validate_ok(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    ok, detail = validate_novel_continue(tmp_path)
    assert ok or "模型" in detail or "Static" in detail


def test_validate_missing_title(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    outline = json.loads((tmp_path / "workspace" / "outline.json").read_text(encoding="utf-8"))
    outline.pop("chosen_title")
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    ok, detail = validate_novel_continue(tmp_path)
    assert not ok
    assert "书名" in detail


def test_build_report_pending(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    report = build_readiness_report(tmp_path)
    assert "pending" in report
    assert "arc_queue_stale" in report


def test_engine_ready_rejects_static_daily_model(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: stub-daily\n",
        encoding="utf-8",
    )
    (cfg / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "stub-daily": {"provider": "static", "model": "placeholder"},
                },
                "slots": {"daily": "stub-daily", "reasoning": "", "backup": []},
                "slots_version": 1,
            }
        ),
        encoding="utf-8",
    )
    assert not _engine_ready(tmp_path)
    report = build_readiness_report(tmp_path)
    assert any(p.get("id") == "engine" for p in report.get("pending") or [])


def test_core_assets_ready_with_yaml_and_txt(tmp_path: Path) -> None:
    """Production projects use rules.yaml + sensitive_words.txt, not legacy .md names."""
    _seed_project(tmp_path)
    (tmp_path / "assets" / "rules.md").unlink(missing_ok=True)
    (tmp_path / "assets" / "sensitive_words.md").unlink(missing_ok=True)
    (tmp_path / "assets" / "rules.yaml").write_text("rules:\n  version: 1\n", encoding="utf-8")
    (tmp_path / "assets" / "sensitive_words.txt").write_text("测试词\n", encoding="utf-8")
    report = build_readiness_report(tmp_path)
    assert not any(p.get("id") == "assets" for p in report.get("pending") or [])


def test_validate_circuit_breaker_requires_force_resume(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: real-daily\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    (cfg / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "real-daily": {"provider": "openai", "model": "gpt-test"},
                },
                "slots": {"daily": "real-daily", "reasoning": "", "backup": []},
                "slots_version": 1,
            }
        ),
        encoding="utf-8",
    )
    record_novel_batch_paused(
        tmp_path,
        reason="circuit_breaker",
        last_chapter="003",
        arc_id="A01",
        streak=2,
    )
    ok, detail = validate_novel_continue(tmp_path, force_resume=False)
    assert not ok
    assert "熔断" in detail

    record_novel_batch_paused(
        tmp_path,
        reason="quality_blocked",
        last_chapter="004",
        arc_id="A01",
        streak=1,
    )
    ok3, detail3 = validate_novel_continue(tmp_path, force_resume=False)
    assert not ok3
    assert "门禁阻断" in detail3
    ok2, detail2 = validate_novel_continue(tmp_path, force_resume=True)
    assert ok2 or "模型" in detail2 or "Static" in detail2