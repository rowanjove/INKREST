from __future__ import annotations

from pathlib import Path

from novel_agent.services.manuscript_documents import plain_text_to_tiptap
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_story_fts_rebuild_recalls_chinese_proper_nouns_and_is_rebuildable(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    store.create_manuscript_document(
        chapter_id="001",
        title="雨夜的蓝鳞剑",
        content_json=plain_text_to_tiptap("蓝鳞剑在雨夜发出微光。"),
        plain_text="蓝鳞剑在雨夜发出微光。",
        markdown_text="蓝鳞剑在雨夜发出微光。",
        source="test",
    )
    store.sync_state_update(
        "001",
        {
            "events": [
                {
                    "id": "E-1",
                    "summary": "蓝鳞剑认主",
                    "characters": ["林澈"],
                    "objects": ["蓝鳞剑"],
                    "threads": ["剑的来历"],
                }
            ],
            "threads": [
                {"id": "T-1", "title": "剑的来历", "status": "open", "summary": "等待查明"}
            ],
        },
    )

    assert store.fts5_status()["available"] is True
    results = store.search_story("蓝鳞剑", limit=20)
    assert results
    assert any(item["kind"] == "chapter_summary" for item in results)
    assert any(item["route"] == "fts" for item in results)

    rebuilt = store.rebuild_story_search_index()
    assert rebuilt["indexed"] >= 3
    assert [item["memory_id"] for item in store.search_story("蓝鳞剑")] == [
        item["memory_id"] for item in store.search_story("蓝鳞剑")
    ]


def test_story_fts_before_chapter_filters_future_events(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    store.sync_state_update(
        "002",
        {"events": [{"id": "future", "summary": "未来的黑曜石门"}]},
    )
    store.sync_state_update(
        "001",
        {"events": [{"id": "past", "summary": "过去的黑曜石门"}]},
    )

    results = store.search_story("黑曜石门", before_chapter="001")
    assert results
    assert all(item["source_chapter"] in {"", "001"} for item in results)
    assert not any(item["memory_id"].startswith("event:future") for item in results)
