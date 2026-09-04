import json
from pathlib import Path

from novel_agent.services.manuscript_documents import plain_text_to_tiptap
from novel_agent.services.manuscript_workspace import (
    ensure_manuscript_document,
    save_manuscript_document,
)
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection
from web.routes.chapters.snapshots import create_chapter_snapshot
from web.tasks import TaskManager


def _count_legacy_versions(store: SQLiteStateStore, chapter_id: str) -> int:
    with safe_connection(store.db_path) as conn:
        row = conn.execute(
            "select count(*) from chapter_versions where chapter_id = ?",
            (chapter_id,),
        ).fetchone()
    return int(row[0] if row else 0)


def _seed_chapter(root: Path, text: str = "") -> Path:
    chapter_dir = root / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "第一章"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "chapter_final.txt").write_text(text, encoding="utf-8")
    return chapter_dir


def test_save_exposes_one_revision_and_does_not_write_legacy_versions(tmp_path: Path):
    _seed_chapter(tmp_path)
    store = SQLiteStateStore(tmp_path)
    current = ensure_manuscript_document(tmp_path, "001")
    saved = save_manuscript_document(
        tmp_path,
        chapter_id="001",
        title="第一章",
        content_json=plain_text_to_tiptap("林澈把信塞进大衣。"),
        expected_revision=current["revision"],
        source="manual",
    )
    versions = store.list_chapter_versions("001")
    active = next(item for item in versions if item.get("is_active") in (1, True))
    assert saved["revision"] == active["revision"]
    assert active["id"]
    assert "塞进大衣" in active["content"]
    assert _count_legacy_versions(store, "001") == 0


def test_chapter_snapshot_stores_revision_pointer_not_body(tmp_path: Path):
    _seed_chapter(tmp_path, "旧正文")
    current = ensure_manuscript_document(tmp_path, "001")
    saved = save_manuscript_document(
        tmp_path,
        chapter_id="001",
        title="第一章",
        content_json=plain_text_to_tiptap("旧正文"),
        expected_revision=current["revision"],
        source="manual",
    )
    snapshot = create_chapter_snapshot(tmp_path, "001", "第一章", "旧正文", is_manual=False)
    assert "final_text" not in snapshot
    assert snapshot["revision"] == saved["revision"]
    assert snapshot["revision_id"]
    files = list((tmp_path / "workspace" / "chapters" / "chapter_001" / ".snapshots").glob("snapshot_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert "final_text" not in payload
    assert payload["revision"] == saved["revision"]


def test_task_sync_does_not_insert_legacy_chapter_versions(tmp_path: Path):
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    final_path = chapter_dir / "chapter_final.txt"
    final_path.write_text("生成稿", encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "第一章"}, ensure_ascii=False),
        encoding="utf-8",
    )
    store = SQLiteStateStore(tmp_path)
    manager = TaskManager(tmp_path)
    try:
        status = manager._sync_task_chapter_version("001", str(final_path), 0)
    finally:
        manager.shutdown()
    assert status == "synced"
    assert _count_legacy_versions(store, "001") == 0
    document = store.get_manuscript_document("001")
    versions = store.list_chapter_versions("001")
    active = next(item for item in versions if item.get("is_active") in (1, True))
    assert document["revision"] == active["revision"]
    assert document["plain_text"] == "生成稿"
