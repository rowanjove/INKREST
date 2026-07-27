"""Application service for the authoritative manuscript workspace."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.domain.manuscript import (
    ManuscriptChapter,
    ManuscriptDocument,
    ManuscriptRevision,
    ManuscriptWorkspace,
)
from novel_agent.scripts.count_chars import wordcount_report
from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.services.manuscript_documents import (
    derive_document_text,
    plain_text_to_tiptap,
    validate_tiptap_document,
)
from novel_agent.state.sqlite_store import SQLiteStateStore


def _safe_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _chapter_rows(store: SQLiteStateStore) -> List[Dict[str, Any]]:
    total = store.count_chapters_indexed()
    rows: List[Dict[str, Any]] = []
    for offset in range(0, total, 500):
        rows.extend(store.list_chapters_page(offset=offset, limit=500))
    return rows


def _chapter_status(row: Dict[str, Any]) -> tuple[str, str]:
    gate = str(row.get("gate_status") or "").lower()
    risk = str(row.get("risk_level") or "").lower()
    if gate in {"failed", "blocked", "fail"} or risk in {"high", "critical", "高", "严重"}:
        return "attention", "需处理"
    if bool(row.get("has_final")) or gate in {"passed", "pass", "ready"}:
        return "ready", "已成稿"
    return "draft", "草稿"


def ensure_manuscript_document(
    root_dir: Path,
    chapter_id: str,
    *,
    store: Optional[SQLiteStateStore] = None,
) -> Dict[str, Any]:
    root = Path(root_dir)
    state = store or SQLiteStateStore(root)
    document = state.get_manuscript_document(chapter_id)
    if document:
        return document

    chapter_dir = root / "workspace" / "chapters" / "chapter_{}".format(chapter_id)
    if not chapter_dir.is_dir():
        raise KeyError(chapter_id)
    plan = _safe_json(chapter_dir / "plan.json")
    title = str(plan.get("chapter_title") or "第 {} 章".format(chapter_id))
    final_path = chapter_dir / "chapter_final.txt"
    plain_text = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
    content_json = plain_text_to_tiptap(plain_text)
    derived_plain, markdown_text = derive_document_text(content_json)
    return state.create_manuscript_document(
        chapter_id=chapter_id,
        title=title,
        content_json=content_json,
        plain_text=derived_plain,
        markdown_text=markdown_text,
        source="import",
    )


def build_manuscript_workspace(
    root_dir: Path,
    *,
    chapter_id: str = "",
    query: str = "",
    status: str = "all",
) -> ManuscriptWorkspace:
    root = Path(root_dir)
    store = SQLiteStateStore(root)
    if store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)
    rows = _chapter_rows(store)
    chapters: List[ManuscriptChapter] = []
    normalized_query = query.strip().lower()
    for row in rows:
        item_status, status_label = _chapter_status(row)
        item = ManuscriptChapter(
            chapter_id=str(row["id"]),
            title=str(row.get("title") or "第 {} 章".format(row["id"])),
            word_count=int(row.get("word_count") or 0),
            status=item_status,
            status_label=status_label,
            has_content=bool(row.get("has_final")),
        )
        if normalized_query and normalized_query not in (
            item.chapter_id + " " + item.title
        ).lower():
            continue
        if status != "all" and item.status != status:
            continue
        chapters.append(item)

    selected = str(chapter_id or "")
    all_ids = {str(row["id"]) for row in rows}
    if selected not in all_ids:
        selected = chapters[0].chapter_id if chapters else ""

    document = None
    history: List[ManuscriptRevision] = []
    context: Dict[str, Any] = {}
    if selected:
        raw_document = ensure_manuscript_document(root, selected, store=store)
        document = ManuscriptDocument(**raw_document)
        history = [
            ManuscriptRevision(**revision)
            for revision in store.list_manuscript_revisions(selected, limit=100)
        ]
        plan = _safe_json(
            root / "workspace" / "chapters" / "chapter_{}".format(selected) / "plan.json"
        )
        row = next((item for item in rows if str(item["id"]) == selected), {})
        context = {
            "chapter_goal": str(plan.get("chapter_goal") or ""),
            "synopsis": str(plan.get("detailed_synopsis") or ""),
            "target_chars": plan.get("target_chars") or [],
            "risk_level": str(row.get("risk_level") or ""),
            "gate_status": str(row.get("gate_status") or ""),
        }
    return ManuscriptWorkspace(
        chapters=chapters,
        selected_chapter_id=selected,
        document=document,
        history=history,
        context=context,
    )


def _project_document(
    root_dir: Path,
    document: Dict[str, Any],
    store: SQLiteStateStore,
) -> None:
    chapter_id = str(document["chapter_id"])
    chapter_dir = (
        Path(root_dir) / "workspace" / "chapters" / "chapter_{}".format(chapter_id)
    )
    chapter_dir.mkdir(parents=True, exist_ok=True)
    final_path = chapter_dir / "chapter_final.txt"
    _atomic_text(final_path, str(document["plain_text"]))

    plan_path = chapter_dir / "plan.json"
    plan = _safe_json(plan_path)
    plan.setdefault("chapter_id", chapter_id)
    plan["chapter_title"] = str(document["title"])
    _atomic_text(plan_path, json.dumps(plan, ensure_ascii=False, indent=2))

    target_chars = plan.get("target_chars")
    target_chars = target_chars if isinstance(target_chars, list) else []
    target_min = int(target_chars[0]) if len(target_chars) > 0 and str(target_chars[0]).isdigit() else 0
    target_max = int(target_chars[1]) if len(target_chars) > 1 and str(target_chars[1]).isdigit() else 0
    report = wordcount_report(str(document["plain_text"]), target_min, target_max)
    _atomic_text(
        chapter_dir / "reports" / "wordcount.json",
        json.dumps(report, ensure_ascii=False, indent=2),
    )

    existing = next(
        (row for row in _chapter_rows(store) if str(row["id"]) == chapter_id),
        {},
    )
    store.index_chapter(
        chapter_id,
        str(document["title"]),
        final_path,
        int(report.get("count") or 0),
        str(existing.get("risk_level") or ""),
        has_final=1 if str(document["plain_text"]).strip() else 0,
        gate_status=str(existing.get("gate_status") or ""),
        indexed_at=time.time(),
    )


def save_manuscript_document(
    root_dir: Path,
    *,
    chapter_id: str,
    title: str,
    content_json: Dict[str, Any],
    expected_revision: int,
    source: str = "autosave",
) -> Dict[str, Any]:
    validate_tiptap_document(content_json)
    plain_text, markdown_text = derive_document_text(content_json)
    store = SQLiteStateStore(root_dir)
    ensure_manuscript_document(root_dir, chapter_id, store=store)
    document = store.save_manuscript_document(
        chapter_id=chapter_id,
        title=title.strip() or "第 {} 章".format(chapter_id),
        content_json=content_json,
        plain_text=plain_text,
        markdown_text=markdown_text,
        expected_revision=expected_revision,
        source=source,
    )
    _project_document(Path(root_dir), document, store)
    return document


def restore_manuscript_revision(
    root_dir: Path,
    *,
    chapter_id: str,
    revision_id: str,
    expected_revision: int,
) -> Dict[str, Any]:
    store = SQLiteStateStore(root_dir)
    document = store.restore_manuscript_revision(
        chapter_id=chapter_id,
        revision_id=revision_id,
        expected_revision=expected_revision,
    )
    _project_document(Path(root_dir), document, store)
    return document
