"""SQLite repository for authoritative manuscript documents and revisions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    def list_manuscript_document_summaries(self) -> List[Dict[str, Any]]:
        """Return lightweight publication rows without loading document bodies."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select chapter_id, title, revision, length(trim(plain_text)) as word_count,
                       case when length(trim(plain_text)) > 0 then 1 else 0 end as has_content,
                       updated_at
                from documents
                order by
                  case when chapter_id GLOB '[0-9]*' then 0 else 1 end,
                  cast(chapter_id as integer),
                  chapter_id
                """
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
        return self._document_row(row)
