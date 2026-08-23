"""Manuscript and publication catalogs paginate without loading full bodies."""

from __future__ import annotations

from pathlib import Path

from novel_agent.services.longform_synth import seed_synthetic_project
from novel_agent.services.manuscript_workspace import build_manuscript_workspace
from novel_agent.services.publishing_workspace import build_publishing_workspace
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_manuscript_workspace_returns_one_page_and_selected_body(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=25, seed=7)
    workspace = build_manuscript_workspace(
        tmp_path,
        chapter_id="024",
        offset=20,
        limit=5,
    )
    assert workspace.catalog_total == 25
    assert workspace.catalog_offset == 20
    assert workspace.catalog_limit == 5
    assert workspace.catalog_has_more is False
    assert [item.chapter_id for item in workspace.chapters] == [
        "021",
        "022",
        "023",
        "024",
        "025",
    ]
    assert workspace.selected_chapter_id == "024"
    assert workspace.document is not None
    assert "第24章" in workspace.document.plain_text
    assert all("plain_text" not in item.model_dump() for item in workspace.chapters)


def test_manuscript_search_is_server_side(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=30, seed=3)
    workspace = build_manuscript_workspace(tmp_path, query="第29章", limit=10)
    assert workspace.catalog_total == 1
    assert [item.chapter_id for item in workspace.chapters] == ["029"]


def test_publishing_first_page_does_not_return_all_summaries(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=40, seed=11)
    workspace = build_publishing_workspace(
        tmp_path,
        project_id="synth",
        project_info={"name": "合成书"},
        offset=0,
        limit=10,
        query="第39章",
    )
    assert workspace.book.chapter_count == 40
    assert workspace.catalog_total == 1
    assert len(workspace.chapters) == 1
    assert workspace.chapters[0].chapter_id == "039"
    dumped = workspace.model_dump()
    assert "plain_text" not in dumped["chapters"][0]
    assert dumped["selected_chapter"]["plain_text"]


def test_publishing_deep_link_opens_selected_catalog_page(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=5000, seed=11)
    workspace = build_publishing_workspace(
        tmp_path,
        project_id="synth",
        project_info={"name": "合成书"},
        selected_chapter_id="4999",
        offset=0,
        limit=100,
    )
    assert workspace.catalog_offset == 4900
    assert workspace.selected_catalog_index == 4998
    assert workspace.chapters[0].chapter_id == "4901"
    assert workspace.chapters[-1].chapter_id == "5000"
    assert workspace.selected_chapter_id == "4999"


def test_publishing_platform_check_uses_global_aggregates(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=5000, seed=11)
    workspace = build_publishing_workspace(
        tmp_path,
        project_id="synth",
        project_info={"name": "合成书"},
        offset=0,
        limit=100,
    )
    detail = workspace.platform_check["items"][1]["detail"]
    expected = round(workspace.book.word_count / workspace.book.chapter_count)
    assert f"{expected} 字" in detail


def test_document_summaries_reject_non_numeric_limit(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    page = store.list_manuscript_document_summaries(offset=0, limit=0)
    assert page == []
    assert store.count_manuscript_document_summaries() == 0
