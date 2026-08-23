"""SQLite repository for authoritative manuscript documents and revisions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from novel_agent.state.sqlite_schema import db_write_lock, safe_connection


class DocumentConflictError(RuntimeError):
    """Raised when a caller saves against a stale document revision."""

    def __init__(self, current: Dict[str, Any]):
        super().__init__("Document revision is stale")
        self.current = current


class ManuscriptRepositoryMixin:
    db_path: Path

    @staticmethod
    def _document_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "document_id": row["document_id"],
            "chapter_id": row["chapter_id"],
            "title": row["title"],
            "content_json": json.loads(row["content_json"]),
            "plain_text": row["plain_text"],
            "markdown_text": row["markdown_text"],
            "revision": int(row["revision"]),
            "source": row["source"] if "source" in row.keys() else "autosave",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _revision_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "revision_id": row["revision_id"],
            "document_id": row["document_id"],
            "chapter_id": row["chapter_id"],
            "revision": int(row["revision"]),
            "title": row["title"],
            "content_json": json.loads(row["content_json"]),
            "plain_text": row["plain_text"],
            "markdown_text": row["markdown_text"],
            "source": row["source"],
            "created_at": row["created_at"],
        }

    def get_manuscript_document(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select document_id, chapter_id, title, content_json, plain_text,
                       markdown_text, revision, source, created_at, updated_at
                from documents where chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
        return self._document_row(row) if row else None

    def list_manuscript_documents(self) -> List[Dict[str, Any]]:
        """Return authoritative documents in stable chapter order."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select document_id, chapter_id, title, content_json, plain_text,
                       markdown_text, revision, source, created_at, updated_at
                from documents
                order by
                  case when chapter_id GLOB '[0-9]*' then 0 else 1 end,
                  cast(chapter_id as integer),
                  chapter_id
                """
            ).fetchall()
        return [self._document_row(row) for row in rows]

    def list_manuscript_document_summaries(
        self,
        offset: int = 0,
        limit: Optional[int] = None,
        *,
        query: str = "",
        has_content: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Return lightweight publication rows without loading document bodies.

        Calling without limit keeps the legacy full-list behavior for internal
        callers. Paginated workspace APIs should pass an explicit limit.
        """
        if limit is not None and int(limit) <= 0:
            return []
        if limit is None and not query and has_content is None:
            return self.list_manuscript_document_summaries_page(
                offset=max(0, int(offset)),
                limit=1_000_000,
            )
        return self.list_manuscript_document_summaries_page(
            offset=offset,
            limit=100 if limit is None else int(limit),
            query=query,
            has_content=has_content,
        )

    @staticmethod
    def _summary_filters(
        *,
        query: str = "",
        has_content: Optional[bool] = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        needle = str(query or "").strip()
        if needle:
            clauses.append("(chapter_id LIKE ? OR title LIKE ?)")
            like = f"%{needle}%"
            params.extend([like, like])
        if has_content is True:
            clauses.append("length(trim(plain_text)) > 0")
        elif has_content is False:
            clauses.append("length(trim(plain_text)) = 0")
        sql = (" where " + " and ".join(clauses)) if clauses else ""
        return sql, params

    def get_manuscript_document_summary(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select chapter_id, title, revision, length(trim(plain_text)) as word_count,
                       case when length(trim(plain_text)) > 0 then 1 else 0 end as has_content,
                       updated_at
                from documents where chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "chapter_id": str(row["chapter_id"]),
            "title": str(row["title"]),
            "revision": int(row["revision"]),
            "word_count": int(row["word_count"] or 0),
            "has_content": bool(row["has_content"]),
            "updated_at": str(row["updated_at"]),
        }

    def get_manuscript_document_summary_position(
        self,
        chapter_id: str,
        *,
        query: str = "",
        has_content: Optional[bool] = None,
    ) -> Optional[int]:
        """Return the zero-based position in the stable filtered catalog order."""

        where, params = self._summary_filters(query=query, has_content=has_content)
        with safe_connection(self.db_path) as conn:
            row = conn.execute(
                f"""
                select position from (
                  select chapter_id,
                         row_number() over (
                           order by
                             case when chapter_id GLOB '[0-9]*' then 0 else 1 end,
                             cast(chapter_id as integer),
                             chapter_id
                         ) - 1 as position
                  from documents
                  {where}
                ) where chapter_id = ?
                """,
                [*params, chapter_id],
            ).fetchone()
        return int(row[0]) if row is not None else None

    def count_manuscript_document_summaries(
        self,
        *,
        query: str = "",
        has_content: Optional[bool] = None,
    ) -> int:
        where, params = self._summary_filters(query=query, has_content=has_content)
        with safe_connection(self.db_path) as conn:
            row = conn.execute(
                f"select count(*) from documents{where}",
                params,
            ).fetchone()
        return int(row[0] if row else 0)

    def sum_manuscript_word_count(
        self,
        *,
        has_content: Optional[bool] = True,
        query: str = "",
    ) -> int:
        where, params = self._summary_filters(query=query, has_content=has_content)
        with safe_connection(self.db_path) as conn:
            row = conn.execute(
                f"select coalesce(sum(length(trim(plain_text))), 0) from documents{where}",
                params,
            ).fetchone()
        return int(row[0] if row else 0)

    def list_manuscript_document_summaries_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        query: str = "",
        has_content: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        offset = max(0, int(offset))
        limit = int(limit)
        if limit <= 0:
            return []
        limit = min(limit, 1_000_000)
        where, params = self._summary_filters(query=query, has_content=has_content)
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                select chapter_id, title, revision, length(trim(plain_text)) as word_count,
                       case when length(trim(plain_text)) > 0 then 1 else 0 end as has_content,
                       updated_at
                from documents
                {where}
                order by
                  case when chapter_id GLOB '[0-9]*' then 0 else 1 end,
                  cast(chapter_id as integer),
                  chapter_id
                limit ? offset ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return [
            {
                "chapter_id": str(row["chapter_id"]),
                "title": str(row["title"]),
                "revision": int(row["revision"]),
                "word_count": int(row["word_count"] or 0),
                "has_content": bool(row["has_content"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ]

    def iter_manuscript_export_rows(
        self,
        *,
        chapter_ids: Optional[List[str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        selected = {
            f"{int(item):03d}" if str(item).isdigit() else str(item)
            for item in (chapter_ids or [])
            if str(item).strip()
        }
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                select chapter_id, title, plain_text, markdown_text, revision
                from documents
                order by
                  case when chapter_id GLOB '[0-9]*' then 0 else 1 end,
                  cast(chapter_id as integer),
                  chapter_id
                """
            )
            for row in cursor:
                chapter_id = str(row["chapter_id"])
                normalized = (
                    f"{int(chapter_id):03d}" if chapter_id.isdigit() else chapter_id
                )
                if selected and normalized not in selected and chapter_id not in selected:
                    continue
                plain_text = str(row["plain_text"] or "").strip()
                if not plain_text:
                    continue
                yield {
                    "chapter_id": chapter_id,
                    "title": str(row["title"] or "").strip(),
                    "plain_text": plain_text,
                    "markdown_text": str(row["markdown_text"] or "").strip(),
                    "revision": int(row["revision"] or 1),
                    "word_count": len(plain_text),
                }

    @db_write_lock
    def bulk_create_manuscript_documents(
        self,
        items: List[Dict[str, Any]],
    ) -> int:
        if not items:
            return 0
        created = 0
        with safe_connection(self.db_path) as conn:
            with conn:
                for item in items:
                    chapter_id = str(item["chapter_id"])
                    title = str(item.get("title") or f"第 {chapter_id} 章")
                    plain_text = str(item.get("plain_text") or "")
                    markdown_text = str(item.get("markdown_text") or plain_text)
                    content_json = item.get("content_json") or {}
                    serialized = json.dumps(
                        content_json, ensure_ascii=False, separators=(",", ":")
                    )
                    source = str(item.get("source") or "synth")
                    document_id = str(uuid.uuid4())
                    cursor = conn.execute(
                        """
                        insert into documents (
                          document_id, chapter_id, title, content_json, plain_text,
                          markdown_text, revision, source
                        ) values (?, ?, ?, ?, ?, ?, 1, ?)
                        on conflict(chapter_id) do nothing
                        """,
                        (
                            document_id,
                            chapter_id,
                            title,
                            serialized,
                            plain_text,
                            markdown_text,
                            source,
                        ),
                    )
                    if cursor.rowcount <= 0:
                        continue
                    conn.execute(
                        """
                        insert into document_revisions (
                          revision_id, document_id, chapter_id, revision, title,
                          content_json, plain_text, markdown_text, source
                        ) values (?, ?, ?, 1, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            document_id,
                            chapter_id,
                            title,
                            serialized,
                            plain_text,
                            markdown_text,
                            source,
                        ),
                    )
                    conn.execute(
                        """
                        insert into chapters (
                          id, title, final_path, word_count, risk_level,
                          has_final, gate_status, indexed_at
                        )
                        values (?, ?, ?, ?, '', 1, 'passed', 0)
                        on conflict(id) do update set
                          title=excluded.title,
                          word_count=excluded.word_count,
                          has_final=excluded.has_final,
                          gate_status=excluded.gate_status
                        """,
                        (
                            chapter_id,
                            title,
                            str(
                                Path("workspace")
                                / "chapters"
                                / f"chapter_{chapter_id}"
                                / "chapter_final.txt"
                            ),
                            int(item.get("word_count") or len(plain_text.strip())),
                        ),
                    )
                    created += 1
        if created:
            self.mark_story_search_dirty()
        return created

    @db_write_lock
    def create_manuscript_document(
        self,
        *,
        chapter_id: str,
        title: str,
        content_json: Dict[str, Any],
        plain_text: str,
        markdown_text: str,
        source: str,
    ) -> Dict[str, Any]:
        document_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        serialized = json.dumps(content_json, ensure_ascii=False, separators=(",", ":"))
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                conn.execute(
                    """
                    insert into documents (
                      document_id, chapter_id, title, content_json, plain_text,
                      markdown_text, revision, source
                    ) values (?, ?, ?, ?, ?, ?, 1, ?)
                    on conflict(chapter_id) do nothing
                    """,
                    (
                        document_id,
                        chapter_id,
                        title,
                        serialized,
                        plain_text,
                        markdown_text,
                        source,
                    ),
                )
                row = conn.execute(
                    """
                    select document_id, chapter_id, title, content_json, plain_text,
                           markdown_text, revision, source, created_at, updated_at
                    from documents where chapter_id = ?
                    """,
                    (chapter_id,),
                ).fetchone()
                if row and row["document_id"] == document_id:
                    conn.execute(
                        """
                        insert into document_revisions (
                          revision_id, document_id, chapter_id, revision, title,
                          content_json, plain_text, markdown_text, source
                        ) values (?, ?, ?, 1, ?, ?, ?, ?, ?)
                        """,
                        (
                            revision_id,
                            document_id,
                            chapter_id,
                            title,
                            serialized,
                            plain_text,
                            markdown_text,
                            source,
                        ),
                    )
        if row is None:
            raise RuntimeError("Failed to create manuscript document")
        self.mark_story_search_dirty()
        return self._document_row(row)

    @db_write_lock
    def save_manuscript_document(
        self,
        *,
        chapter_id: str,
        title: str,
        content_json: Dict[str, Any],
        plain_text: str,
        markdown_text: str,
        expected_revision: int,
        source: str,
    ) -> Dict[str, Any]:
        serialized = json.dumps(content_json, ensure_ascii=False, separators=(",", ":"))
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                current_row = conn.execute(
                    """
                    select document_id, chapter_id, title, content_json, plain_text,
                           markdown_text, revision, source, created_at, updated_at
                    from documents where chapter_id = ?
                    """,
                    (chapter_id,),
                ).fetchone()
                if current_row is None:
                    raise KeyError(chapter_id)
                current = self._document_row(current_row)
                if current["revision"] != int(expected_revision):
                    raise DocumentConflictError(current)
                if (
                    current["title"] == title
                    and current_row["content_json"] == serialized
                    and current["plain_text"] == plain_text
                    and current["markdown_text"] == markdown_text
                ):
                    return current

                next_revision = current["revision"] + 1
                updated = conn.execute(
                    """
                    update documents set
                      title = ?, content_json = ?, plain_text = ?, markdown_text = ?,
                      revision = ?, source = ?, updated_at = current_timestamp
                    where chapter_id = ? and revision = ?
                    """,
                    (
                        title,
                        serialized,
                        plain_text,
                        markdown_text,
                        next_revision,
                        source,
                        chapter_id,
                        expected_revision,
                    ),
                )
                if updated.rowcount != 1:
                    latest = conn.execute(
                        """
                        select document_id, chapter_id, title, content_json, plain_text,
                               markdown_text, revision, source, created_at, updated_at
                        from documents where chapter_id = ?
                        """,
                        (chapter_id,),
                    ).fetchone()
                    raise DocumentConflictError(self._document_row(latest))
                conn.execute(
                    """
                    insert into document_revisions (
                      revision_id, document_id, chapter_id, revision, title,
                      content_json, plain_text, markdown_text, source
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        current["document_id"],
                        chapter_id,
                        next_revision,
                        title,
                        serialized,
                        plain_text,
                        markdown_text,
                        source,
                    ),
                )
                row = conn.execute(
                    """
                    select document_id, chapter_id, title, content_json, plain_text,
                           markdown_text, revision, source, created_at, updated_at
                    from documents where chapter_id = ?
                    """,
                    (chapter_id,),
                ).fetchone()
        self.mark_story_search_dirty()
        return self._document_row(row)

    def list_manuscript_revisions(
        self, chapter_id: str, *, limit: int = 100
    ) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select revision_id, document_id, chapter_id, revision, title,
                       content_json, plain_text, markdown_text, source, created_at
                from document_revisions
                where chapter_id = ?
                order by revision desc
                limit ?
                """,
                (chapter_id, max(1, min(int(limit), 500))),
            ).fetchall()
        return [self._revision_row(row) for row in rows]

    @db_write_lock
    def restore_manuscript_revision(
        self,
        *,
        chapter_id: str,
        revision_id: str,
        expected_revision: int,
    ) -> Dict[str, Any]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                current_row = conn.execute(
                    """
                    select document_id, chapter_id, title, content_json, plain_text,
                           markdown_text, revision, source, created_at, updated_at
                    from documents where chapter_id = ?
                    """,
                    (chapter_id,),
                ).fetchone()
                if current_row is None:
                    raise KeyError(chapter_id)
                current = self._document_row(current_row)
                if current["revision"] != int(expected_revision):
                    raise DocumentConflictError(current)
                target = conn.execute(
                    """
                    select revision_id, document_id, chapter_id, revision, title,
                           content_json, plain_text, markdown_text, source, created_at
                    from document_revisions
                    where revision_id = ? and chapter_id = ?
                    """,
                    (revision_id, chapter_id),
                ).fetchone()
                if target is None:
                    raise KeyError(revision_id)

                next_revision = current["revision"] + 1
                conn.execute(
                    """
                    update documents set
                      title = ?, content_json = ?, plain_text = ?, markdown_text = ?,
                      revision = ?, source = 'restore', updated_at = current_timestamp
                    where chapter_id = ? and revision = ?
                    """,
                    (
                        target["title"],
                        target["content_json"],
                        target["plain_text"],
                        target["markdown_text"],
                        next_revision,
                        chapter_id,
                        expected_revision,
                    ),
                )
                conn.execute(
                    """
                    insert into document_revisions (
                      revision_id, document_id, chapter_id, revision, title,
                      content_json, plain_text, markdown_text, source
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, 'restore')
                    """,
                    (
                        str(uuid.uuid4()),
                        current["document_id"],
                        chapter_id,
                        next_revision,
                        target["title"],
                        target["content_json"],
                        target["plain_text"],
                        target["markdown_text"],
                    ),
                )
                row = conn.execute(
                    """
                    select document_id, chapter_id, title, content_json, plain_text,
                           markdown_text, revision, source, created_at, updated_at
                    from documents where chapter_id = ?
                    """,
                    (chapter_id,),
                ).fetchone()
        self.mark_story_search_dirty()
        return self._document_row(row)
