import sqlite3
from typing import Any, Dict, List
from pathlib import Path
from novel_agent.state.sqlite_schema import safe_connection


class HistoryLegacySearchMixin:
    """Contains legacy search methods used primarily for tests and debugging."""
    db_path: Path

    def _event_row(self, row) -> Dict[str, Any]:
        raise NotImplementedError("Must be implemented by child class")

    def search_events(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Legacy literal search used primarily for tests and debugging."""
        like = f"%{query}%"
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, chapter_id, scene_id, summary, characters, objects, threads
                from events
                where summary like ? or characters like ? or objects like ? or threads like ?
                order by chapter_id desc, id desc
                limit ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
        return [self._event_row(row) for row in rows]

    def search_timeline(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Legacy literal search used primarily for tests and debugging."""
        like = f"%{query}%"
        results: List[Dict[str, Any]] = []
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            node_rows = conn.execute(
                """
                select id, type, name, description, status, chapter_id, 'node' as kind
                from timeline_nodes
                where name like ? or description like ? or type like ?
                  or ? like '%' || name || '%'
                order by chapter_id desc, id desc
                limit ?
                """,
                (like, like, like, query, limit),
            ).fetchall()
            edge_rows = conn.execute(
                """
                select id, type, from_node, to_node, description, strength, change, chapter_id, 'edge' as kind
                from timeline_edges
                where from_node like ? or to_node like ? or description like ? or type like ?
                  or ? like '%' || from_node || '%'
                  or ? like '%' || to_node || '%'
                order by chapter_id desc, id desc
                limit ?
                """,
                (like, like, like, like, query, query, limit),
            ).fetchall()
            foreshadow_rows = conn.execute(
                """
                select id, title, status, description, chapter_id, 'foreshadow' as kind
                from foreshadows
                where title like ? or description like ? or status like ?
                  or ? like '%' || title || '%'
                order by chapter_id desc, id desc
                limit ?
                """,
                (like, like, like, query, limit),
            ).fetchall()
            hook_rows = conn.execute(
                """
                select id, title, status, description, chapter_id, 'hook' as kind
                from hooks
                where title like ? or description like ? or status like ?
                  or ? like '%' || title || '%'
                order by chapter_id desc, id desc
                limit ?
                """,
                (like, like, like, query, limit),
            ).fetchall()
        for row in node_rows:
            results.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "type": row["type"],
                    "name": row["name"],
                    "description": row["description"],
                    "status": row["status"],
                    "chapter_id": row["chapter_id"],
                }
            )
        for row in edge_rows:
            results.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "type": row["type"],
                    "from": row["from_node"],
                    "to": row["to_node"],
                    "description": row["description"],
                    "strength": row["strength"],
                    "change": row["change"],
                    "chapter_id": row["chapter_id"],
                }
            )
        for row in foreshadow_rows + hook_rows:
            results.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "title": row["title"],
                    "status": row["status"],
                    "description": row["description"],
                    "chapter_id": row["chapter_id"],
                }
            )
        return results[:limit]
