"""Sync workspace chapter directories into SQLite chapters index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict

from novel_agent.logging_config import get_logger
from novel_agent.scripts.count_chars import count_chinese_chars

if TYPE_CHECKING:
    from novel_agent.state.sqlite_store import SQLiteStateStore

logger = get_logger("services.chapter_index_sync")

_SYNC_MANIFEST_REL = Path("workspace/reports/chapter_index_sync.json")
_TRACKED_FILES = (
    "plan.json",
    "chapter_final.txt",
    "reports/wordcount.json",
    "reports/audit.json",
)


def _load_sync_manifest(root_dir: Path) -> Dict[str, float]:
    path = root_dir / _SYNC_MANIFEST_REL
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    sigs = data.get("signatures") if isinstance(data, dict) else None
    if not isinstance(sigs, dict):
        return {}
    out: Dict[str, float] = {}
    for key, value in sigs.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _save_sync_manifest(root_dir: Path, signatures: Dict[str, float]) -> None:
    path = root_dir / _SYNC_MANIFEST_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"signatures": signatures}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.debug("Failed to write chapter index sync manifest: %s", exc)


def chapter_dir_signature(chapter_dir: Path) -> float:
    """Max mtime of indexed chapter artifacts; 0 when folder is empty."""
    mtimes: list[float] = []
    for rel in _TRACKED_FILES:
        fp = chapter_dir / rel
        if fp.is_file():
            try:
                mtimes.append(fp.stat().st_mtime)
            except OSError:
                continue
    return max(mtimes) if mtimes else 0.0


def _index_one_chapter(
    chapter_dir: Path,
    chapter_id: str,
    store: "SQLiteStateStore",
) -> bool:
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
        return True
    except Exception as exc:
        logger.error("Failed to index chapter %s: %s", chapter_id, exc)
        return False


def sync_chapters_from_disk(
    root_dir: Path,
    store: "SQLiteStateStore",
    *,
    force_full: bool = False,
) -> int:
    """Index chapter_* folders; returns number of chapters re-indexed this run."""
    chapters_dir = Path(root_dir) / "workspace" / "chapters"

    disk_chapter_ids: set[str] = set()
    if chapters_dir.exists():
        for chapter_dir in chapters_dir.glob("chapter_*"):
            if chapter_dir.is_dir():
                disk_chapter_ids.add(chapter_dir.name.replace("chapter_", "", 1))

    try:
        db_chapters = store.get_chapters()
        db_chapter_ids = {c["id"] for c in db_chapters}
    except Exception as exc:
        logger.error("Failed to fetch chapters from store during sync: %s", exc)
        db_chapter_ids = set()

    deleted_chapter_ids = db_chapter_ids - disk_chapter_ids
    if deleted_chapter_ids:
        logger.info(
            "Found %d chapters deleted from disk: %s. Cleaning up assets...",
            len(deleted_chapter_ids),
            deleted_chapter_ids,
        )
        try:
            store.delete_chapters_index(list(deleted_chapter_ids))
        except Exception as exc:
            logger.error(
                "Failed to batch delete chapter indexes for %s: %s",
                deleted_chapter_ids,
                exc,
            )

    manifest = {} if force_full else _load_sync_manifest(root_dir)
    for removed_id in deleted_chapter_ids:
        manifest.pop(removed_id, None)

    synced = 0
    if chapters_dir.exists():
        for chapter_dir in sorted(chapters_dir.glob("chapter_*")):
            if not chapter_dir.is_dir():
                continue
            chapter_id = chapter_dir.name.replace("chapter_", "", 1)
            signature = chapter_dir_signature(chapter_dir)
            if (
                not force_full
                and manifest.get(chapter_id) == signature
                and chapter_id in db_chapter_ids
            ):
                continue
            if _index_one_chapter(chapter_dir, chapter_id, store):
                manifest[chapter_id] = signature
                synced += 1

    _save_sync_manifest(root_dir, manifest)

    if synced or deleted_chapter_ids:
        if synced:
            logger.info("Synced %d chapters into SQLite index", synced)
        try:
            from novel_agent.services.chapter_highwater import sync_highwater_from_store

            sync_highwater_from_store(root_dir)
        except Exception as exc:
            logger.error("Highwater sync after index skipped: %s", exc)

    return synced