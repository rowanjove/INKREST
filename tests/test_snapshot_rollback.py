"""Regression tests for chapter snapshot rollback."""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from novel_agent.state.sqlite_store import SQLiteStateStore
from web.deps import ProjectSession
from web.routes.chapters.snapshots import rollback_chapter_snapshot


def _write_snapshot(root: Path, chapter_id: str, timestamp: str, payload: dict) -> None:
    snapshots = root / "workspace" / "chapters" / f"chapter_{chapter_id}" / ".snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / f"snapshot_{timestamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_rollback_uses_authoritative_revision_store(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    store = SQLiteStateStore(tmp_path)
    first = store.create_manuscript_document(
        chapter_id="001",
        title="第一章",
        content_json={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "旧正文"}]}]},
        plain_text="旧正文",
        markdown_text="旧正文",
        source="import",
    )
    store.save_manuscript_document(
        chapter_id="001",
        title="第一章",
        content_json={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "新正文"}]}]},
        plain_text="新正文",
        markdown_text="新正文",
        expected_revision=first["revision"],
        source="manual",
    )
    revisions = store.list_manuscript_revisions("001", limit=10)
    old_revision = next(item for item in revisions if item["revision"] == 1)
    _write_snapshot(
        tmp_path,
        "001",
        "123",
        {"title": "第一章", "revision_id": old_revision["revision_id"]},
    )

    result = rollback_chapter_snapshot(
        "001", "123", ProjectSession("book", tmp_path)
    )

    assert result["status"] == "rolled_back"
    assert SQLiteStateStore(tmp_path).get_manuscript_document("001")["plain_text"] == "旧正文"


def test_rollback_does_not_replace_missing_snapshot_content_with_blank(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    _write_snapshot(tmp_path, "001", "456", {"title": "第一章", "revision_id": "gone"})

    with pytest.raises(HTTPException) as exc_info:
        rollback_chapter_snapshot("001", "456", ProjectSession("book", tmp_path))

    assert exc_info.value.status_code == 404
