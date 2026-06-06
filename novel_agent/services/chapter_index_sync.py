"""Sync workspace chapter directories into SQLite chapters index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from novel_agent.logging_config import get_logger
from novel_agent.scripts.count_chars import count_chinese_chars

if TYPE_CHECKING:
    from novel_agent.state.sqlite_store import SQLiteStateStore

logger = get_logger("services.chapter_index_sync")


def sync_chapters_from_disk(root_dir: Path, store: "SQLiteStateStore") -> int:
    """Index all chapter_* folders; returns number of chapters synced.
    Also removes chapters and their assets from the SQLite index if their folders no longer exist on disk.
    """
    chapters_dir = Path(root_dir) / "workspace" / "chapters"
    
    # 1. 搜集磁盘上实际存在的章节ID
    disk_chapter_ids = set()
    if chapters_dir.exists():
        for chapter_dir in chapters_dir.glob("chapter_*"):
            if chapter_dir.is_dir():
                ch_id = chapter_dir.name.replace("chapter_", "", 1)
                disk_chapter_ids.add(ch_id)

    # 2. 搜集数据库中现有的章节ID
    try:
        db_chapters = store.get_chapters()
        db_chapter_ids = {c["id"] for c in db_chapters}
    except Exception as exc:
        logger.error("Failed to fetch chapters from store during sync: %s", exc)
        db_chapter_ids = set()

    # 3. 找出已被物理删除的章节，并级联清除
    deleted_chapter_ids = db_chapter_ids - disk_chapter_ids
    if deleted_chapter_ids:
        logger.info("Found %d chapters deleted from disk: %s. Cleaning up assets...", len(deleted_chapter_ids), deleted_chapter_ids)
        try:
            store.delete_chapters_index(list(deleted_chapter_ids))
        except Exception as exc:
            logger.error("Failed to batch delete chapter indexes for %s: %s", deleted_chapter_ids, exc)

    # 4. 同步磁盘上的章节到数据库
    synced = 0
    if chapters_dir.exists():
        for chapter_dir in sorted(chapters_dir.glob("chapter_*")):
            if not chapter_dir.is_dir():
                continue
            chapter_id = chapter_dir.name.replace("chapter_", "", 1)
            plan_path = chapter_dir / "plan.json"
            title = ""
            if plan_path.exists():
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    title = str(plan.get("chapter_title") or "")
                except (json.JSONDecodeError, OSError) as exc:
                    logger.debug("Failed to read plan.json for chapter_%s: %s", chapter_id, exc)
            final_path = chapter_dir / "chapter_final.txt"
            final_text = ""
            if final_path.exists():
                try:
                    final_text = final_path.read_text(encoding="utf-8")
                except OSError as exc:
                    logger.debug("Failed to read chapter_final.txt for chapter_%s: %s", chapter_id, exc)
            word_count = 0
            wc_path = chapter_dir / "reports" / "wordcount.json"
            if wc_path.exists():
                try:
                    wc = json.loads(wc_path.read_text(encoding="utf-8"))
                    word_count = int(wc.get("count") or 0)
                except (json.JSONDecodeError, OSError, ValueError) as exc:
                    logger.debug("Failed to read wordcount.json for chapter_%s: %s", chapter_id, exc)
            if not word_count and final_text.strip():
                word_count = count_chinese_chars(final_text)
            risk_level = ""
            audit_path = chapter_dir / "reports" / "audit.json"
            if audit_path.exists():
                try:
                    audit = json.loads(audit_path.read_text(encoding="utf-8"))
                    risk_level = str(audit.get("risk_level") or "")
                except (json.JSONDecodeError, OSError) as exc:
                    logger.debug("Failed to read audit.json for chapter_%s: %s", chapter_id, exc)
            try:
                store.index_chapter(
                    chapter_id,
                    title,
                    final_path,
                    word_count,
                    risk_level,
                )
                synced += 1
            except Exception as exc:
                logger.error("Failed to index chapter %s: %s", chapter_id, exc)

    # 5. 如果有新增同步或已删除，触发高水位线同步
    if synced or deleted_chapter_ids:
        if synced:
            logger.info("Synced %d chapters into SQLite index", synced)
        try:
            from novel_agent.services.chapter_highwater import sync_highwater_from_store
            sync_highwater_from_store(root_dir)
        except Exception as exc:
            logger.error("Highwater sync after index skipped: %s", exc)

    return synced