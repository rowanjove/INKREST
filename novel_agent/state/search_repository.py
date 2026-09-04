"""Bounded, rebuildable SQLite FTS5 projection for story memory search."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Iterable, Mapping

from novel_agent.state.sqlite_schema import safe_connection


_WHITESPACE_RE = re.compile(r"\s+")


def _json_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    if isinstance(value, Mapping):
        return " ".join(
            f"{key} {_json_text(item)}" for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return " ".join(_json_text(item) for item in value)
    return str(value)


def _row_text(*values: Any) -> str:
    return _WHITESPACE_RE.sub(" ", " ".join(_json_text(value) for value in values)).strip()


class SearchRepositoryMixin:
    """Mixin added to ``SQLiteStateStore``; FTS is never a second truth source."""

    db_path: Any

    def fts5_status(self) -> dict[str, Any]:
        with safe_connection(self.db_path) as conn:
            row = conn.execute(
                "select value from app_metadata where key = 'fts5_status'"
            ).fetchone()
        raw = str(row[0] if row else "unavailable:not_initialized")
        return {
            "available": raw == "available",
            "status": raw,
            "index": "story_search_fts",
        }

    def mark_story_search_dirty(self) -> None:
        if not self.fts5_status()["available"]:
            return
        with safe_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into app_metadata(key, value) values ('fts5_dirty', '1')
                on conflict(key) do update set value = excluded.value
                """
            )
            conn.commit()

    def rebuild_story_search_index(self) -> dict[str, Any]:
        """Rebuild the projection from authoritative tables atomically."""

        status = self.fts5_status()
        if not status["available"]:
            return {**status, "indexed": 0, "degraded": True}

        rows: list[tuple[str, str, str, str, str, str, int]] = []
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(
                "select chapter_id, title from documents order by chapter_id"
            ):
                rows.append(
                    (
                        f"chapter:{row['chapter_id']}",
                        "chapter_summary",
                        _row_text(row["title"]),
                        str(row["chapter_id"]),
                        "",
                        "supporting",
                        0,
                    )
                )
            for row in conn.execute(
                "select chapter_id, summary from chapter_summaries order by chapter_id"
            ):
                rows.append(
                    (
                        f"chapter-summary:{row['chapter_id']}",
                        "chapter_summary",
                        _row_text(row["summary"]),
                        str(row["chapter_id"]),
                        "",
                        "supporting",
                        0,
                    )
                )
            narrative_chapters = {
                str(item["chapter_id"])
                for item in conn.execute("select distinct chapter_id from narrative_events")
            }
            for row in conn.execute(
                "select id, chapter_id, summary, characters, objects, threads from events order by chapter_id, id"
            ):
                if str(row["chapter_id"]) in narrative_chapters:
                    continue
                rows.append(
                    (
                        f"event:{row['id']}",
                        "canon_fact",
                        _row_text(
                            row["summary"], row["characters"], row["objects"], row["threads"]
                        ),
                        str(row["chapter_id"]),
                        "",
                        "required",
                        0,
                    )
                )
            for row in conn.execute(
                """
                select event_id, chapter_id, source_revision_id, actors, location,
                       action, outcome, objects, threads, superseded_by
                from narrative_events order by chapter_id, event_id
                """
            ):
                rows.append(
                    (
                        f"event:{row['event_id']}@{row['source_revision_id'] or 'current'}",
                        "canon_fact",
                        _row_text(
                            row["actors"], row["location"], row["action"],
                            row["outcome"], row["objects"], row["threads"],
                        ),
                        str(row["chapter_id"]),
                        str(row["source_revision_id"] or ""),
                        "required" if not row["superseded_by"] else "supporting",
                        1 if row["superseded_by"] else 0,
                    )
                )
            for table, kind, hardness in (
                ("threads", "open_thread", "required"),
                ("character_state", "character", "supporting"),
                ("objects", "object", "supporting"),
                ("foreshadows", "foreshadow", "supporting"),
                ("hooks", "hook", "supporting"),
                ("reader_promises", "reader_promise", "supporting"),
                ("secrets", "secret", "required"),
            ):
                columns = {
                    item[1]
                    for item in conn.execute(f"pragma table_info({table})").fetchall()
                }
                if not columns:
                    continue
                selected = [name for name in ("id", "name", "title", "holder", "location", "emotion", "status", "summary", "description", "chapter_id", "payload") if name in columns]
                for row in conn.execute(
                    f"select {', '.join(selected)} from {table} order by id"
                ):
                    values = {key: row[key] for key in selected}
                    memory_id = f"{kind}:{values.get('id') or values.get('name')}"
                    rows.append(
                        (
                            memory_id,
                            kind,
                            _row_text(*values.values()),
                            str(values.get("chapter_id") or ""),
                            "",
                            hardness,
                            0,
                        )
                    )

            with conn:
                conn.execute("delete from story_search_fts")
                conn.executemany(
                    """
                    insert into story_search_fts(
                      memory_id, kind, text, source_chapter, source_revision_id,
                      hardness, superseded
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.execute(
                    """
                    insert into app_metadata(key, value) values ('fts5_dirty', '0')
                    on conflict(key) do update set value = excluded.value
                    """
                )
        return {**status, "indexed": len(rows), "degraded": False}

    def search_story(
        self,
        query: str,
        *,
        limit: int = 20,
        before_chapter: str | None = None,
        include_superseded: bool = False,
    ) -> list[dict[str, Any]]:
        """Search a safe phrase query with deterministic BM25 ordering."""

        status = self.fts5_status()
        if not status["available"]:
            return []
        with safe_connection(self.db_path) as conn:
            dirty = conn.execute(
                "select value from app_metadata where key = 'fts5_dirty'"
            ).fetchone()
            fts_count = conn.execute("select count(*) from story_search_fts").fetchone()
            source_count = conn.execute("select count(*) from documents").fetchone()
        if (dirty and str(dirty[0]) == "1") or (
            int(fts_count[0] if fts_count else 0) == 0
            and int(source_count[0] if source_count else 0) > 0
        ):
            self.rebuild_story_search_index()
        needle = _WHITESPACE_RE.sub(" ", str(query or "")).strip()
        if not needle:
            return []
        # FTS MATCH is parameterized; quoting turns punctuation and Chinese
        # characters into a phrase while avoiding operator injection.
        match = '"' + needle.replace('"', '""') + '"'
        cap = max(1, min(int(limit), 200))
        clauses = ["story_search_fts match ?"]
        params: list[Any] = [match]
        if not include_superseded:
            clauses.append("superseded = 0")
        if before_chapter:
            clauses.append(
                "(source_chapter = '' or cast(source_chapter as integer) <= cast(? as integer))"
            )
            params.append(str(before_chapter))
        params.append(cap)
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                select memory_id, kind, text, source_chapter, source_revision_id,
                       hardness, superseded, bm25(story_search_fts) as rank
                from story_search_fts
                where {' and '.join(clauses)}
                order by rank asc, memory_id asc
                limit ?
                """,
                params,
            ).fetchall()
            # unicode61 does not segment Chinese text.  Merge a parameterized
            # substring pass so proper nouns/idioms are not lost when FTS
            # happens to match only one of the projected memory kinds.
            if any(ord(char) > 127 for char in needle):
                like_clauses = ["text like ?"]
                like_params: list[Any] = [f"%{needle}%"]
                if not include_superseded:
                    like_clauses.append("superseded = 0")
                if before_chapter:
                    like_clauses.append(
                        "(source_chapter = '' or cast(source_chapter as integer) <= cast(? as integer))"
                    )
                    like_params.append(str(before_chapter))
                like_params.append(cap)
                like_rows = conn.execute(
                    f"""
                    select memory_id, kind, text, source_chapter, source_revision_id,
                           hardness, superseded, 0.0 as rank
                    from story_search_fts
                    where {' and '.join(like_clauses)}
                    order by source_chapter, memory_id
                    limit ?
                    """,
                    like_params,
                ).fetchall()
                seen = {row["memory_id"] for row in rows}
                rows = list(rows) + [
                    row for row in like_rows if row["memory_id"] not in seen
                ]
                rows.sort(key=lambda row: (float(row["rank"]), row["memory_id"]))
        return [
            {
                "memory_id": row["memory_id"],
                "kind": row["kind"],
                "text": row["text"],
                "source_chapter": row["source_chapter"],
                "source_revision_id": row["source_revision_id"],
                "hardness": row["hardness"],
                "superseded": bool(row["superseded"]),
                "route": "fts",
                "route_score": float(-row["rank"]),
            }
            for row in rows
        ]
