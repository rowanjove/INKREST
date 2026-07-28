"""Chapter SQLite index stores gate_status and has_final metadata."""

import json
from pathlib import Path

from novel_agent.services.chapter_index_sync import derive_gate_status, sync_chapters_from_disk
from novel_agent.state.sqlite_store import SQLiteStateStore


def _chapter_dir(root: Path, chapter_id: str) -> Path:
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    return chapter_dir


def test_index_stores_gate_status_and_has_final(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path, "008")
    (chapter_dir / "chapter_final.txt").write_text("正文内容", encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "第八章"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "reports").mkdir(parents=True, exist_ok=True)
    (chapter_dir / "reports" / "audit.json").write_text(
        json.dumps({"risk_level": "低", "issues": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    store = SQLiteStateStore(tmp_path)
    assert sync_chapters_from_disk(tmp_path, store) == 1

    row = store.list_chapters_page(limit=10)[0]
    assert row["has_final"] is True
    assert row["gate_status"] == "ok"
    assert row["indexed_at"] > 0


def test_derive_gate_status_blocked_on_quality_checkpoint(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path, "009")
    (chapter_dir / "chapter_final.txt").write_text("blocked chapter", encoding="utf-8")
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps({"last_stage": "quality_blocked"}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert derive_gate_status(chapter_dir, "blocked chapter") == "blocked"


def test_index_treats_unified_gate_block_as_blocked(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path, "011")
    (chapter_dir / "chapter_final.txt").write_text("blocked by gate", encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        json.dumps({"chapter_title": "门禁阻断"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "reports").mkdir(parents=True, exist_ok=True)
    (chapter_dir / "reports" / "unified_gate.json").write_text(
        json.dumps({"blocked": True, "resumable_from": "audit"}, ensure_ascii=False),
        encoding="utf-8",
    )

    store = SQLiteStateStore(tmp_path)
    assert sync_chapters_from_disk(tmp_path, store) == 1

    row = store.list_chapters_page(limit=10)[0]
    assert row["has_final"] is True
    assert row["gate_status"] == "blocked"


def test_derive_gate_status_empty_without_final(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path, "010")
    assert derive_gate_status(chapter_dir, "") == "empty"
