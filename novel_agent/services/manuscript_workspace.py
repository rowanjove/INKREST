"""Application service for the authoritative manuscript workspace."""

from __future__ import annotations

import json
import time
import difflib
import hashlib
from datetime import datetime, timezone
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
from novel_agent.control.longform_flags import flag_enabled
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.manuscript_repository import DocumentConflictError


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


def _chapter_rows(
    store: SQLiteStateStore,
    *,
    offset: int = 0,
    limit: int = 100,
    query: str = "",
    status: str = "all",
) -> List[Dict[str, Any]]:
    return store.list_chapters_page(
        offset=offset,
        limit=limit,
        query=query,
        status=status,
    )


def _chapter_status(row: Dict[str, Any]) -> tuple[str, str]:
    gate = str(row.get("gate_status") or "").lower()
    risk = str(row.get("risk_level") or "").lower()
    if gate in {"failed", "blocked", "fail"} or risk in {"high", "critical", "高", "严重"}:
        return "attention", "需处理"
    if bool(row.get("has_final")) or gate in {"passed", "pass", "ready"}:
        return "ready", "已成稿"
    return "draft", "草稿"


def text_sha256(value: str) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_quality_rewrite_candidate(root: Path, chapter_id: str) -> Optional[Dict[str, Any]]:
    """Load the isolated quality-rewrite candidate and its metadata."""

    reports_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports"
    candidate_path = reports_dir / "quality_rewrite_candidate.txt"
    metadata_path = reports_dir / "quality_rewrite_candidate.json"
    if not candidate_path.is_file() and not metadata_path.is_file():
        return None

    metadata: Dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            parsed = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                metadata = parsed
        except (OSError, json.JSONDecodeError):
            metadata = {}
    candidate = ""
    if candidate_path.is_file():
        try:
            candidate = candidate_path.read_text(encoding="utf-8")
        except OSError:
            candidate = ""
    return {
        "available": bool(candidate.strip() or metadata),
        "candidate_text": candidate,
        "metadata": metadata,
        "artifact": "reports/quality_rewrite_candidate.txt",
    }


def mark_quality_rewrite_candidate_adopted(
    root: Path,
    chapter_id: str,
    *,
    revision: int,
    source: str = "manual",
) -> Dict[str, Any]:
    """Record that the isolated candidate was explicitly adopted."""

    reports_dir = Path(root) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports"
    metadata_path = reports_dir / "quality_rewrite_candidate.json"
    loaded = load_quality_rewrite_candidate(Path(root), chapter_id) or {}
    metadata = dict(loaded.get("metadata") or {})
    metadata.update(
        {
            "adopted": True,
            "adopted_revision": int(revision),
            "adopted_source": source,
            "adopted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _atomic_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


def build_quality_candidate_diff(
    original_text: str,
    candidate_text: str,
    *,
    max_chars: int = 24000,
) -> Dict[str, Any]:
    """Build a bounded line diff suitable for the manuscript inspector."""

    original_lines = str(original_text or "").splitlines(keepends=True)
    candidate_lines = str(candidate_text or "").splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, original_lines, candidate_lines, autojunk=False)
    segments: List[Dict[str, Any]] = []
    consumed = 0
    added_lines = 0
    removed_lines = 0
    changed_blocks = 0
    truncated = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            removed_lines += i2 - i1
            added_lines += j2 - j1
            changed_blocks += 1
            replacement_segments = [
                ("delete", "".join(original_lines[i1:i2])),
                ("insert", "".join(candidate_lines[j1:j2])),
            ]
        elif tag == "delete":
            removed_lines += i2 - i1
            changed_blocks += 1
            replacement_segments = [("delete", "".join(original_lines[i1:i2]))]
        elif tag == "insert":
            added_lines += j2 - j1
            changed_blocks += 1
            replacement_segments = [("insert", "".join(candidate_lines[j1:j2]))]
        else:
            replacement_segments = [("equal", "".join(original_lines[i1:i2]))]
        for operation, text in replacement_segments:
            if consumed + len(text) > max_chars:
                remaining = max(0, max_chars - consumed)
                if remaining:
                    segments.append({"op": operation, "text": text[:remaining]})
                truncated = True
                break
            segments.append({"op": operation, "text": text})
            consumed += len(text)
        if truncated:
            break
    return {
        "segments": segments,
        "stats": {
            "original_lines": len(original_lines),
            "candidate_lines": len(candidate_lines),
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "changed_blocks": changed_blocks,
        },
        "truncated": truncated,
    }


def _quality_rewrite_candidate(
    root: Path,
    chapter_id: str,
    *,
    current_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Read the latest isolated quality-rewrite candidate, if one exists.

    Only a bounded preview is included in the workspace payload.  The actual
    ``chapter_final.txt`` remains the authoritative manuscript until a human or
    an explicitly approved workflow adopts the candidate.
    """

    loaded = load_quality_rewrite_candidate(root, chapter_id)
    if loaded is None:
        return {"available": False}
    metadata = loaded["metadata"]
    candidate = loaded["candidate_text"]
    preview_limit = 1600
    result: Dict[str, Any] = {
        "available": bool(candidate.strip() or metadata),
        "preview": candidate[:preview_limit],
        "preview_truncated": len(candidate) > preview_limit,
        "metadata": metadata,
        "artifact": loaded["artifact"],
    }
    if current_text is not None:
        result["diff"] = build_quality_candidate_diff(current_text, candidate)
    return result


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
    offset: int = 0,
    limit: int = 100,
) -> ManuscriptWorkspace:
    root = Path(root_dir)
    store = SQLiteStateStore(root)
    if store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)
    page_offset = max(0, int(offset or 0))
    page_limit = max(1, min(int(limit or 100), 100))
    catalog_total = store.count_chapters_filtered(query=query, status=status)
    # The rollback switch intentionally restores the pre-pagination behavior
    # for operators diagnosing a deployment: one request receives the full
    # filtered catalog.  The default path remains bounded at 100 rows.
    if not flag_enabled("m1_catalog_pagination", root):
        page_offset = 0
        page_limit = max(1, catalog_total)
    rows = _chapter_rows(
        store,
        offset=page_offset,
        limit=page_limit,
        query=query,
        status=status,
    )
    chapters: List[ManuscriptChapter] = []
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
        chapters.append(item)

    selected = str(chapter_id or "")
    if selected:
        indexed = store.get_chapter_index(selected)
        if indexed is None:
            selected = chapters[0].chapter_id if chapters else ""
    else:
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
        row = store.get_chapter_index(selected) or {}
        context = {
            "chapter_goal": str(plan.get("chapter_goal") or ""),
            "synopsis": str(plan.get("detailed_synopsis") or ""),
            "target_chars": plan.get("target_chars") or [],
            "risk_level": str(row.get("risk_level") or ""),
            "gate_status": str(row.get("gate_status") or ""),
            "quality_candidate": _quality_rewrite_candidate(
                root,
                selected,
                current_text=document.plain_text if document else "",
            ),
        }
    return ManuscriptWorkspace(
        chapters=chapters,
        selected_chapter_id=selected,
        document=document,
        history=history,
        context=context,
        catalog_offset=page_offset,
        catalog_limit=page_limit,
        catalog_total=catalog_total,
        catalog_has_more=page_offset + len(chapters) < catalog_total,
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

    existing = store.get_chapter_index(chapter_id) or {}
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


def apply_plain_text_to_manuscript(
    root_dir: Path,
    *,
    chapter_id: str,
    plain_text: str,
    title: Optional[str] = None,
    expected_revision: Optional[int] = None,
    source: str = "manual",
) -> Dict[str, Any]:
    """Write plain text through the authoritative document + projection path."""
    store = SQLiteStateStore(root_dir)
    current = ensure_manuscript_document(root_dir, chapter_id, store=store)
    revision = int(current["revision"] if expected_revision is None else expected_revision)
    resolved_title = (
        (title or "").strip()
        or str(current.get("title") or "")
        or f"第 {chapter_id} 章"
    )
    return save_manuscript_document(
        root_dir,
        chapter_id=chapter_id,
        title=resolved_title,
        content_json=plain_text_to_tiptap(plain_text),
        expected_revision=revision,
        source=source,
    )


def sync_generated_manuscript_document(
    root_dir: Path,
    *,
    chapter_id: str,
    final_path: Path,
    expected_revision: Optional[int],
    source: str = "generation",
) -> Dict[str, Any]:
    """Commit generated text into the authoritative document and its projection."""
    root = Path(root_dir)
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    resolved_final = Path(final_path).resolve()
    expected_final = (chapter_dir / "chapter_final.txt").resolve()
    if resolved_final != expected_final:
        raise ValueError("Generated manuscript path does not match the requested chapter")
    plain_text = resolved_final.read_text(encoding="utf-8")
    plan = _safe_json(chapter_dir / "plan.json")
    title = str(plan.get("chapter_title") or f"第 {chapter_id} 章")
    content_json = plain_text_to_tiptap(plain_text)
    derived_plain, markdown_text = derive_document_text(content_json)
    store = SQLiteStateStore(root)

    current = store.get_manuscript_document(chapter_id)
    if current is None and expected_revision in (None, 0):
        created = store.create_manuscript_document(
            chapter_id=chapter_id,
            title=title,
            content_json=content_json,
            plain_text=derived_plain,
            markdown_text=markdown_text,
            source=source,
        )
        if (
            created["plain_text"] != derived_plain
            or created["title"] != title
        ):
            _project_document(root, created, store)
            raise DocumentConflictError(created)
        _project_document(root, created, store)
        return created

    if current is None:
        current = ensure_manuscript_document(root, chapter_id, store=store)
    revision = int(
        current["revision"] if expected_revision is None else expected_revision
    )
    try:
        document = store.save_manuscript_document(
            chapter_id=chapter_id,
            title=title,
            content_json=content_json,
            plain_text=derived_plain,
            markdown_text=markdown_text,
            expected_revision=revision,
            source=source,
        )
    except DocumentConflictError as exc:
        # SQLite is authoritative. Restore its latest text over the stale pipeline projection.
        _project_document(root, exc.current, store)
        raise
    _project_document(root, document, store)
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
