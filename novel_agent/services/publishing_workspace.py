"""Application service for publication preview, checks, and exports."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from novel_agent.control.platform_profiles import resolve_platform_profile
from novel_agent.control.longform_flags import flag_enabled
from novel_agent.domain.publishing import (
    ExportPreflight,
    PreflightItem,
    PublicationBookSummary,
    PublicationChapter,
    PublicationChapterSummary,
    PublishingWorkspace,
)
from novel_agent.exporters.chapter_export import chapter_heading, collect_publication_book
from novel_agent.services.project_snapshot import build_project_snapshot
from novel_agent.state.sqlite_store import SQLiteStateStore


def _read_project_meta(root: Path) -> dict[str, Any]:
    path = root / "config" / "project_meta.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _platform_contract(meta: dict[str, Any]) -> dict[str, Any]:
    profile = resolve_platform_profile(str(meta.get("platform") or "qidian"))
    return {
        "id": str(profile["name"]),
        "label": str(profile["label"]),
        "pacing_density": int(profile["pacing_density"]),
        "setting_detail_weight": int(profile["setting_detail_weight"]),
        "dialogue_ratio_range": list(profile["dialogue_ratio_range"]),
        "style_summary": str(profile["style_prompt"]),
        "golden_three_rules": str(profile["golden_three_rules"]),
        "avoid": [str(item) for item in profile.get("rules_blacklist", [])],
    }


def build_golden_check(chapters: list[PublicationChapterSummary]) -> dict[str, Any]:
    by_id = {
        f"{int(chapter.chapter_id):03d}": chapter
        for chapter in chapters
        if chapter.chapter_id.isdigit()
    }
    checks: list[dict[str, Any]] = []
    for chapter_id in ("001", "002", "003"):
        chapter = by_id.get(chapter_id)
        checks.append(
            {
                "chapter_id": chapter_id,
                "label": chapter_heading(chapter) if chapter else f"第 {int(chapter_id)} 章",
                "status": "ready" if chapter and chapter.has_content else "missing",
                "word_count": chapter.word_count if chapter else 0,
            }
        )
    ready = sum(item["status"] == "ready" for item in checks)
    return {
        "status": "ready" if ready == 3 else "incomplete",
        "ready_count": ready,
        "required_count": 3,
        "checks": checks,
    }


def build_platform_check(
    chapters: list[PublicationChapterSummary],
    platform: dict[str, Any],
    *,
    chapter_count: int | None = None,
    total_chars: int | None = None,
) -> dict[str, Any]:
    published = [chapter for chapter in chapters if chapter.has_content]
    effective_total_chars = (
        int(total_chars)
        if total_chars is not None
        else sum(chapter.word_count for chapter in published)
    )
    effective_chapter_count = (
        int(chapter_count) if chapter_count is not None else len(published)
    )
    average = (
        round(effective_total_chars / effective_chapter_count)
        if effective_chapter_count
        else 0
    )
    items = [
        {
            "code": "platform_selected",
            "status": "ready",
            "label": f"已选择 {platform['label']}",
            "detail": "导出预览将使用该平台的节奏与避坑提示。",
        },
        {
            "code": "chapter_length",
            "status": "ready" if average else "pending",
            "label": "章节体量",
            "detail": f"当前平均每章约 {average} 字。" if average else "尚无正文可检查。",
        },
        {
            "code": "manual_rules",
            "status": "review",
            "label": "内容规则需人工确认",
            "detail": "平台规则用于发布前复核，不会在打开页面时调用模型。",
        },
    ]
    return {
        "status": "ready" if effective_chapter_count else "pending",
        "items": items,
    }


def build_export_preflight(
    chapters: list[PublicationChapterSummary],
    *,
    snapshot_quality: dict[str, Any],
    empty_document_count: int,
    platform_explicit: bool,
    published_count: int | None = None,
    published_word_count: int | None = None,
) -> ExportPreflight:
    items: list[PreflightItem] = []
    published = [chapter for chapter in chapters if chapter.has_content]
    ready_count = (
        int(published_count) if published_count is not None else len(published)
    )
    ready_words = (
        int(published_word_count)
        if published_word_count is not None
        else sum(ch.word_count for ch in published)
    )
    if not ready_count:
        items.append(
            PreflightItem(
                code="no_manuscript",
                severity="blocking",
                label="没有可导出的正文",
                detail="请先在正文中心创建并保存至少一个非空章节。",
                route="/manuscript",
            )
        )
    else:
        items.append(
            PreflightItem(
                code="manuscript_ready",
                severity="ready",
                label=f"已收集 {ready_count} 个正文章节",
                detail=f"共 {ready_words} 字，来自 SQLite 文稿。",
            )
        )
    if empty_document_count:
        items.append(
            PreflightItem(
                code="empty_documents",
                severity="warning",
                label=f"{empty_document_count} 个空章节不会导出",
                detail="空章节保留在正文中心，但不进入成书文件。",
                route="/manuscript?status=draft",
            )
        )
    if str(snapshot_quality.get("status") or "") == "blocked":
        failed = int(snapshot_quality.get("failed") or 0)
        unreadable = int(snapshot_quality.get("unreadable") or 0)
        items.append(
            PreflightItem(
                code="quality_blocked",
                severity="blocking",
                label="审校仍有阻断项",
                detail=f"{failed} 个失败报告，{unreadable} 个损坏报告。",
                route="/production?tab=reviews",
            )
        )
    if ready_count < 3:
        items.append(
            PreflightItem(
                code="golden_chapters_incomplete",
                severity="warning",
                label="黄金三章尚不完整",
                detail="可以导出试读稿，但正式发布前建议补齐前三章。",
            )
        )
    if not platform_explicit:
        items.append(
            PreflightItem(
                code="platform_defaulted",
                severity="warning",
                label="平台使用默认值",
                detail="当前按起点中文网规则展示；建议发布前确认目标平台。",
            )
        )
    if not any(item.severity == "blocking" for item in items):
        items.append(
            PreflightItem(
                code="export_ready",
                severity="ready",
                label="导出服务已就绪",
                detail="文件将按当前数据库文稿快照生成。",
            )
        )
    blocking_count = sum(item.severity == "blocking" for item in items)
    warning_count = sum(item.severity == "warning" for item in items)
    return ExportPreflight(
        can_export=blocking_count == 0,
        blocking_count=blocking_count,
        warning_count=warning_count,
        items=items,
    )


def publication_formats() -> list[dict[str, Any]]:
    reportlab_available = importlib.util.find_spec("reportlab") is not None
    docx_available = importlib.util.find_spec("docx") is not None
    return [
        {"id": "txt", "label": "TXT", "available": True, "extension": ".txt"},
        {"id": "markdown", "label": "Markdown", "available": True, "extension": ".md"},
        {"id": "docx", "label": "DOCX", "available": docx_available, "extension": ".docx"},
        {"id": "epub", "label": "EPUB 3", "available": True, "extension": ".epub"},
        {"id": "pdf", "label": "PDF", "available": reportlab_available, "extension": ".pdf"},
    ]


def build_publishing_workspace(
    root_dir: Path,
    *,
    project_id: str,
    project_info: dict[str, Any] | None = None,
    selected_chapter_id: str = "",
    offset: int = 0,
    limit: int = 100,
    query: str = "",
) -> PublishingWorkspace:
    root = Path(root_dir)
    meta = _read_project_meta(root)
    snapshot = build_project_snapshot(
        root,
        project_id=project_id,
        project_info=project_info,
    )
    title = str(snapshot.project.get("name") or "未命名小说")
    store = SQLiteStateStore(root)
    page_offset = max(0, int(offset or 0))
    page_limit = max(1, min(int(limit or 100), 100))
    catalog_total = store.count_manuscript_document_summaries(
        query=query, has_content=True
    )
    if not flag_enabled("m1_catalog_pagination", root):
        page_offset = 0
        page_limit = max(1, catalog_total)
    selected_position = (
        store.get_manuscript_document_summary_position(
            selected_chapter_id,
            query=query,
            has_content=True,
        )
        if selected_chapter_id
        else None
    )
    # A direct deep link should open the page containing the selected chapter.
    # For subsequent page loads, the caller owns the offset and we must not
    # snap back to the selected chapter's page.
    if (
        selected_position is not None
        and page_offset == 0
        and not (page_offset <= selected_position < page_offset + page_limit)
    ):
        page_offset = (selected_position // page_limit) * page_limit
    chapters = [
        PublicationChapterSummary(**row)
        for row in store.list_manuscript_document_summaries_page(
            offset=page_offset,
            limit=page_limit,
            query=query,
            has_content=True,
        )
    ]
    published_count = store.count_manuscript_document_summaries(has_content=True)
    selected_summary = None
    if selected_chapter_id:
        raw = store.get_manuscript_document_summary(selected_chapter_id)
        if raw and raw.get("has_content"):
            selected_summary = PublicationChapterSummary(**raw)
    if selected_summary is None and chapters:
        selected_summary = chapters[0]
    if selected_summary is not None and selected_position is None:
        selected_position = store.get_manuscript_document_summary_position(
            selected_summary.chapter_id,
            query=query,
            has_content=True,
        )
    selected = None
    if selected_summary:
        document = store.get_manuscript_document(selected_summary.chapter_id)
        if document:
            selected = PublicationChapter(
                chapter_id=str(document["chapter_id"]),
                title=str(document["title"]),
                plain_text=str(document["plain_text"]),
                markdown_text=str(document["markdown_text"]),
                revision=int(document["revision"]),
                word_count=len(str(document["plain_text"]).strip()),
            )
    book = PublicationBookSummary(
        title=title,
        chapter_count=published_count,
        word_count=store.sum_manuscript_word_count(has_content=True),
    )
    empty_count = store.count_manuscript_document_summaries(has_content=False)
    platform = _platform_contract(meta)
    golden_summaries = []
    for chapter_id in ("001", "002", "003"):
        raw = store.get_manuscript_document_summary(chapter_id)
        if raw:
            golden_summaries.append(PublicationChapterSummary(**raw))
    preflight_source = golden_summaries + list(chapters)
    preflight = build_export_preflight(
        preflight_source,
        snapshot_quality=snapshot.quality_summary,
        empty_document_count=empty_count,
        platform_explicit=bool(str(meta.get("platform") or "").strip()),
        published_count=published_count,
        published_word_count=book.word_count,
    )
    return PublishingWorkspace(
        snapshot=snapshot,
        book=book,
        chapters=chapters,
        selected_chapter_id=selected.chapter_id if selected else "",
        selected_chapter=selected,
        catalog_offset=page_offset,
        catalog_limit=page_limit,
        catalog_total=catalog_total,
        catalog_has_more=page_offset + len(chapters) < catalog_total,
        selected_catalog_index=selected_position if selected_position is not None else -1,
        platform=platform,
        platform_check=build_platform_check(
            chapters,
            platform,
            chapter_count=published_count,
            total_chars=book.word_count,
        ),
        golden_check=build_golden_check(golden_summaries),
        feedback=store.get_recent_feedback(limit=100),
        preflight=preflight,
        formats=publication_formats(),
    )


def build_trial_bundle(
    root_dir: Path,
    *,
    chapter_ids: Optional[Iterable[str]] = None,
    include_titles: bool = True,
) -> dict[str, Any]:
    book = collect_publication_book(root_dir, chapter_ids=chapter_ids)
    if not book.chapters:
        raise ValueError("No chapters found to export")
    parts: list[str] = []
    for chapter in book.chapters[:50]:
        heading = chapter_heading(chapter) if include_titles else f"第 {chapter.chapter_id} 章"
        parts.append(f"=== {heading} ===\n\n{chapter.plain_text}")
    text = "\n\n---\n\n".join(parts)
    return {
        "chapter_ids": [chapter.chapter_id for chapter in book.chapters[:50]],
        "text": text,
        "char_count": len(text),
    }
