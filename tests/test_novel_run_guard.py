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


def test_readiness_ok_after_outline_without_arc_files(tmp_path: Path) -> None:
    """生成大纲后卷队列尚未落地时，清单应全绿，连写提交时再自动同步。"""
    from tests.helpers.seed_engine import seed_usable_daily_model

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: test-daily\n",
        encoding="utf-8",
    )
    seed_usable_daily_model(tmp_path, model_id="test-daily")
    (tmp_path / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.yaml", "sensitive_words.txt"):
        (tmp_path / "assets" / name).write_text("x" * 20, encoding="utf-8")
    outline = {
        "chosen_title": "已生成大纲的书",
        "target_chapters": 20,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-10", "goal": "开局"}],
    }
    (tmp_path / "workspace").mkdir(exist_ok=True)
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    from novel_agent.services.outline_sync import record_outline_saved

    record_outline_saved(tmp_path, outline)

    report = build_readiness_report(tmp_path)
    assert report["has_arcs"] is False
    assert report["ok"] is True
    assert report["pending"] == []
    assert any("卷级队列尚未建立" in item for item in report.get("warnings") or [])


def test_readiness_rejects_quick_create_placeholder_outline(tmp_path: Path) -> None:
    from tests.helpers.seed_engine import seed_usable_daily_model

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: test-daily\n", encoding="utf-8"
    )
    seed_usable_daily_model(tmp_path, model_id="test-daily")
    (tmp_path / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.yaml", "sensitive_words.txt"):
        (tmp_path / "assets" / name).write_text("x" * 20, encoding="utf-8")
    outline = {
        "chosen_title": "占位书",
        "planning_status": "draft",
        "target_chapters": 200,
        "protagonist": {"name": "待定"},
        "macro_outline": [{
            "arc_id": "A01",
            "name": "起始卷",
            "chapters": "1-80",
            "goal": "确立主线与读者抓手",
            "turning_point": "待定",
            "payoff": "待定",
        }],
    }
    (tmp_path / "workspace").mkdir(exist_ok=True)
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )

    report = build_readiness_report(tmp_path)
    assert report["ok"] is False
    assert any(item["id"] == "outline" for item in report["pending"])
    ok, detail = validate_novel_continue(tmp_path)
    assert ok is False
    assert "大纲" in detail


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


def test_engine_ready_rejects_remote_model_without_credentials(tmp_path: Path) -> None:
    """A provider name alone must not make a paid remote model look runnable."""
    _seed_project(tmp_path)
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: remote-daily\n",
        encoding="utf-8",
    )
    (cfg / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "remote-daily": {
                        "provider": "openai",
                        "model": "gpt-test",
                        "base_url": "https://api.deepseek.com/v1",
                    },
                },
                "slots": {"daily": "remote-daily", "reasoning": "", "backup": []},
            }
        ),
        encoding="utf-8",
    )

    assert not _engine_ready(tmp_path)
    report = build_readiness_report(tmp_path)
    assert any(p.get("id") == "engine" for p in report.get("pending") or [])


def test_engine_ready_accepts_loopback_model_without_api_key(tmp_path: Path) -> None:
    """Local OpenAI-compatible servers commonly do not require an API key."""
    _seed_project(tmp_path)
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: local-daily\n",
        encoding="utf-8",
    )
    (cfg / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "local-daily": {
                        "provider": "openai",
                        "model": "qwen-local",
                        "base_url": "http://127.0.0.1:11434/v1",
                    },
                },
                "slots": {"daily": "local-daily", "reasoning": "", "backup": []},
            }
        ),
        encoding="utf-8",
    )

    assert _engine_ready(tmp_path)


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
                    "real-daily": {
                        "provider": "openai",
                        "model": "gpt-test",
                        "api_key": "test-key",
                    },
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


def test_vector_scale_warning(tmp_path: Path) -> None:
    _seed_project(tmp_path)

    from novel_agent.state.sqlite_store import safe_connection
    db_dir = tmp_path / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "novel.sqlite"

    with safe_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_embeddings (
                id TEXT PRIMARY KEY,
                type TEXT,
                text TEXT,
                embedding BLOB,
                metadata TEXT,
                chapter_id TEXT
            )
            """
        )
        vals = []
        for i in range(2005):
            vals.append((f"chunk-{i}", "prose", f"text {i}", b"\x00" * 16, "{}", ""))
        conn.executemany(
            "INSERT INTO vector_embeddings VALUES (?, ?, ?, ?, ?, ?)",
            vals
        )
        conn.commit()

    report = build_readiness_report(tmp_path)
    warnings = report.get("warnings") or []
    assert any("已索引的向量块数量" in w and "NumPy" in w for w in warnings)
