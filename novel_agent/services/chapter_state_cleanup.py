"""Cascade narrative state cleanup when a chapter is removed."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import yaml

logger = logging.getLogger("novel_agent.services.chapter_state_cleanup")


def _loads_json_field(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _collect_refs_from_event_rows(rows: Iterable[Any]) -> Dict[str, Set[str]]:
    characters: Set[str] = set()
    objects: Set[str] = set()
    threads: Set[str] = set()
    for row in rows:
        if hasattr(row, "keys"):
            chars_field, objs_field, threads_field = row["characters"], row["objects"], row["threads"]
        else:
            chars_field, objs_field, threads_field = row[0], row[1], row[2]
        for name in _loads_json_field(chars_field):
            s = str(name).strip()
            if s:
                characters.add(s)
        for oid in _loads_json_field(objs_field):
            s = str(oid).strip()
            if s:
                objects.add(s)
        for tid in _loads_json_field(threads_field):
            s = str(tid).strip()
            if s:
                threads.add(s)
    return {"characters": characters, "objects": objects, "threads": threads}


def protected_character_ids(root_dir: Path) -> Set[str]:
    """Never auto-remove protagonist / named cast from character_cards."""
    protected: Set[str] = set()
    cards_path = Path(root_dir) / "assets" / "character_cards.yaml"
    if not cards_path.is_file():
        return protected
    try:
        data = yaml.safe_load(cards_path.read_text(encoding="utf-8")) or {}
        for item in data.get("characters") or []:
            if not isinstance(item, dict):
                continue
            for key in ("id", "name"):
                val = str(item.get(key) or "").strip()
                if val:
                    protected.add(val)
    except Exception as exc:
        logger.debug("Could not read character_cards for protected ids: %s", exc)
    return protected


def prune_legacy_yaml_for_chapter(root_dir: Path, chapter_id: str) -> None:
    """Remove chapter-scoped rows from legacy YAML mirrors under state/."""
    state_dir = Path(root_dir) / "state"
    if not state_dir.is_dir():
        return

    def _prune_list_file(path: Path, list_key: str, *, chapter_field: str = "chapter_id") -> None:
        if not path.is_file():
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return
        items = data.get(list_key)
        if not isinstance(items, list):
            return
        kept = []
        for item in items:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            if str(item.get(chapter_field) or "") == chapter_id:
                continue
            item_id = str(item.get("id") or "")
            if item_id.startswith(f"E{chapter_id}") or item_id.startswith(f"H_{chapter_id}"):
                continue
            kept.append(item)
        if len(kept) != len(items):
            data[list_key] = kept
            from novel_agent.state.manager import _safe_write_yaml

            _safe_write_yaml(path, data)

    _prune_list_file(state_dir / "events.yaml", "events")
    _prune_list_file(state_dir / "foreshadows.yaml", "foreshadows")
    _prune_list_file(state_dir / "hooks.yaml", "hooks")
    _prune_list_file(state_dir / "objects.yaml", "objects", chapter_field="last_chapter_id")


def purge_chapter_narrative_state(conn: Any, root_dir: Path, chapter_id: str) -> None:
    """
    Delete SQLite narrative rows for one chapter and prune orphan globals.

    Expects an open sqlite3 connection; caller manages transaction (with conn:).
    """
    root_dir = Path(root_dir)

    deleted_rows = conn.execute(
        "select characters, objects, threads from events where chapter_id = ?",
        (chapter_id,),
    ).fetchall()
    deleted_refs = _collect_refs_from_event_rows(deleted_rows)

    remaining_rows = conn.execute(
        "select characters, objects, threads from events where chapter_id != ?",
        (chapter_id,),
    ).fetchall()
    remaining_refs = _collect_refs_from_event_rows(remaining_rows)

    # --- chapter-scoped tables ---
    conn.execute("delete from chapters where id = ?", (chapter_id,))
    conn.execute("delete from chapter_summaries where chapter_id = ?", (chapter_id,))
    conn.execute("delete from events where chapter_id = ?", (chapter_id,))
    conn.execute("delete from timeline_nodes where chapter_id = ?", (chapter_id,))
    conn.execute("delete from timeline_edges where chapter_id = ?", (chapter_id,))
    conn.execute("delete from foreshadows where chapter_id = ? or plan_chapter = ?", (chapter_id, chapter_id))
    conn.execute("delete from hooks where chapter_id = ? or plan_chapter = ?", (chapter_id, chapter_id))
    conn.execute("delete from reader_promises where chapter_id = ?", (chapter_id,))
    conn.execute("delete from secrets where chapter_id = ?", (chapter_id,))
    conn.execute("delete from state_change_candidates where chapter_id = ?", (chapter_id,))
    conn.execute("delete from chapter_rewrites where chapter_id = ?", (chapter_id,))
    conn.execute("delete from chapter_versions where chapter_id = ?", (chapter_id,))
    conn.execute("delete from reader_feedback where chapter_id = ?", (chapter_id,))

    conn.execute(
        "delete from task_logs where task_id in (select id from tasks where chapter_id = ?)",
        (chapter_id,),
    )
    conn.execute("delete from tasks where chapter_id = ?", (chapter_id,))

    # vector_embeddings (sqlite mirror)
    rows = conn.execute("select id, metadata from vector_embeddings").fetchall()
    ids_to_delete: List[str] = []
    for row in rows:
        id_val, meta_str = row[0], row[1]
        if id_val.startswith(f"chapter_{chapter_id}"):
            ids_to_delete.append(id_val)
            continue
        if meta_str:
            try:
                meta = json.loads(meta_str)
                ch = meta.get("chapter") or meta.get("chapter_id")
                if str(ch) == str(chapter_id):
                    ids_to_delete.append(id_val)
            except json.JSONDecodeError:
                pass
    if ids_to_delete:
        conn.executemany(
            "delete from vector_embeddings where id = ?",
            [(i,) for i in set(ids_to_delete)],
        )

    remaining_chapters = int(conn.execute("select count(*) from chapters").fetchone()[0])
    protected = protected_character_ids(root_dir)
    remaining_objects = remaining_refs["objects"]
    remaining_threads = remaining_refs["threads"]
    remaining_chars = remaining_refs["characters"]

    if remaining_chapters == 0:
        conn.execute("delete from objects")
        conn.execute("delete from threads")
        for row in conn.execute("select id from character_state").fetchall():
            cid = str(row[0]).strip()
            if cid not in protected:
                conn.execute("delete from character_state where id = ?", (cid,))
    else:
        for oid in deleted_refs["objects"] - remaining_objects:
            conn.execute("delete from objects where id = ?", (oid,))
        for tid in deleted_refs["threads"] - remaining_threads:
            conn.execute("delete from threads where id = ?", (tid,))
        for row in conn.execute("select id, payload from objects").fetchall():
            oid = str(row[0]).strip()
            if not oid or oid in remaining_objects:
                continue
            try:
                payload = json.loads(row[1] or "{}")
            except json.JSONDecodeError:
                payload = {}
            if str(payload.get("last_chapter_id") or "") == chapter_id:
                conn.execute("delete from objects where id = ?", (oid,))
        for row in conn.execute("select id, payload from threads").fetchall():
            tid = str(row[0]).strip()
            if not tid or tid in remaining_threads:
                continue
            try:
                payload = json.loads(row[1] or "{}")
            except json.JSONDecodeError:
                payload = {}
            if str(payload.get("last_chapter_id") or "") == chapter_id:
                conn.execute("delete from threads where id = ?", (tid,))
        for row in conn.execute("select id, name from character_state").fetchall():
            cid = str(row[0]).strip()
            cname = str(row[1] or "").strip()
            if cid in protected or cname in protected:
                continue
            if cid in remaining_chars or cname in remaining_chars:
                continue
            conn.execute("delete from character_state where id = ?", (cid,))

    prune_legacy_yaml_for_chapter(root_dir, chapter_id)
    logger.info("Purged narrative state for chapter %s", chapter_id)