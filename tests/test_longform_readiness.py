from pathlib import Path

from novel_agent.control.longform_readiness import build_longform_readiness
from novel_agent.retrieval.reranker import resolve_reranker_readiness


def test_longform_readiness_is_read_only_and_explains_degradation(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.yaml").write_text("llm:\n  provider: static\n", encoding="utf-8")
    result = build_longform_readiness(tmp_path)
    assert result["badges"]["design_supported"] is True
    assert "fts" in result["retrieval"]
    assert "required_fact_coverage" in result["retrieval"]
    assert "tasks" in result
    assert result["tasks"]["active"] == 0
    assert not (tmp_path / "workspace" / "outline.json").exists()


def test_reranker_readiness_distinguishes_disabled_and_declarative_config(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "pipeline.yaml").write_text("llm:\n  provider: static\n", encoding="utf-8")
    assert resolve_reranker_readiness(tmp_path)["status"] == "disabled"
    (config_dir / "pipeline.yaml").write_text(
        "llm:\n  provider: static\nruntime:\n  reranker:\n    provider: local\n    model: bge-reranker\n",
        encoding="utf-8",
    )
    result = resolve_reranker_readiness(tmp_path)
    assert result["status"] == "configured"
    assert result["mode"] == "local"


def test_readiness_reads_persisted_task_progress_without_manager_side_effects(tmp_path: Path):
    from novel_agent.state.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(tmp_path)
    store.task_repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type="export",
        payload={"format": "txt"},
    )
    result = build_longform_readiness(tmp_path)
    assert result["tasks"]["status"] == "ready"
    assert result["tasks"]["active"] == 1
    assert result["tasks"]["items"][0]["id"] == "task-1"


def test_readiness_reads_versioned_arc_contract_projection(tmp_path: Path):
    from novel_agent.control.arc_contract_store import create_arc_contract, seal_saved_arc_contract

    create_arc_contract(
        tmp_path,
        {"arc_id": "A01", "chapter_start": 1, "chapter_end": 10, "objective": "守住北门"},
    )
    seal_saved_arc_contract(tmp_path, "A01")

    result = build_longform_readiness(tmp_path)
    assert result["arc_contract"]["status"] == "sealed"
    assert result["arc_contract"]["version"] == 1
    assert result["arc_contract"]["arc_id"] == "A01"
