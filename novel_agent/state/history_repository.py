import json
import sqlite3
import uuid
import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from novel_agent.state.sqlite_schema import db_write_lock, safe_connection


class HistoryRepositoryMixin:
    """Contains chapter versions, task management, metrics, prompts, and reader feedback logging."""
    db_path: Path

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _loads(value: str):
        if not value:
            return []
        return json.loads(value)

    def _marker_row(self, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "description": row["description"],
            "chapter_id": row["chapter_id"],
            "deadline_chapter": row["deadline_chapter"] or "",
            "reveal_chapter": row["reveal_chapter"] or "",
            "pressure_level": row["pressure_level"] or "",
            "related_characters": self._loads(row["related_characters"]) if row["related_characters"] else [],
            "user_priority": row["user_priority"] if "user_priority" in row.keys() else 0,
            "plan_chapter": row["plan_chapter"] if "plan_chapter" in row.keys() else "",
        }

    def _event_row(self, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "chapter_id": row["chapter_id"],
            "scene_id": row["scene_id"],
            "summary": row["summary"],
            "characters": self._loads(row["characters"]),
            "objects": self._loads(row["objects"]),
            "threads": self._loads(row["threads"]),
        }

    @db_write_lock
    def index_chapter(
        self,
        chapter_id: str,
        title: str,
        final_path: Path,
        word_count: int,
        risk_level: str,
    ) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into chapters (id, title, final_path, word_count, risk_level)
                    values (?, ?, ?, ?, ?)
                    on conflict(id) do update set
                      title=excluded.title,
                      final_path=excluded.final_path,
                      word_count=excluded.word_count,
                      risk_level=excluded.risk_level
                    """,
                    (chapter_id, title, str(final_path), word_count, risk_level),
                )

    @db_write_lock
    def save_chapter_summary(
        self,
        chapter_id: str,
        summary: str,
        summary_path: Path,
    ) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into chapter_summaries (chapter_id, summary, summary_path)
                    values (?, ?, ?)
                    on conflict(chapter_id) do update set
                      summary=excluded.summary,
                      summary_path=excluded.summary_path
                    """,
                    (chapter_id, summary, str(summary_path)),
                )

    @db_write_lock
    def delete_chapter_index(self, chapter_id: str) -> None:
        from novel_agent.services.chapter_state_cleanup import purge_chapter_narrative_state

        with safe_connection(self.db_path) as conn:
            with conn:
                purge_chapter_narrative_state(conn, self.root_dir, chapter_id)

    def search_events(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
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

    def get_chapters(self) -> List[Dict[str, Any]]:
        return self.list_chapters_page(offset=0, limit=1_000_000)

    def count_chapters_indexed(self) -> int:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("select count(*) as c from chapters").fetchone()
        return int(row["c"]) if row else 0

    def sum_chapters_word_count_indexed(self) -> int:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select coalesce(sum(word_count), 0) as total from chapters"
            ).fetchone()
        return int(row["total"]) if row else 0

    def max_numeric_chapter_id(self) -> Optional[int]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select max(cast(id as integer)) as mx from chapters
                where id GLOB '[0-9]*'
                """
            ).fetchone()
        if row and row["mx"] is not None:
            return int(row["mx"])
        return None

    def list_chapters_page(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        offset = max(0, int(offset))
        limit = max(1, min(int(limit), 500))
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, title, final_path, word_count, risk_level from chapters
                order by cast(id as integer), id
                limit ? offset ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "final_path": r["final_path"],
                "word_count": r["word_count"],
                "risk_level": r["risk_level"],
            }
            for r in rows
        ]

    @db_write_lock
    def set_debt_priority(self, table: str, debt_id: str, priority: int) -> None:
        allowed_tables = {"foreshadows", "hooks", "reader_promises", "secrets"}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            priority = 0
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    f"update {table} set user_priority = ? where id = ?",
                    (priority, debt_id)
                )

    @db_write_lock
    def set_debt_plan_chapter(self, table: str, debt_id: str, plan_chapter: str) -> None:
        allowed_tables = {"foreshadows", "hooks", "reader_promises", "secrets"}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")
        plan_chapter_str = str(plan_chapter) if plan_chapter is not None else ""
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    f"update {table} set plan_chapter = ? where id = ?",
                    (plan_chapter_str, debt_id)
                )

    @db_write_lock
    def upsert_reader_promise(self, item: Dict[str, Any]) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                self._upsert_marker(conn, "reader_promises", item.get("chapter_id", ""), item)

    def list_reader_promises(self, status: str = "") -> List[Dict[str, Any]]:
        sql = "select id, title, status, description, chapter_id, deadline_chapter, reveal_chapter, pressure_level, related_characters, user_priority, plan_chapter from reader_promises"
        params = (status,) if status else ()
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql + (" where status = ?" if status else "") + " order by chapter_id", params).fetchall()
        return [self._marker_row(r) for r in rows]

    @db_write_lock
    def upsert_secret(self, item: Dict[str, Any]) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                self._upsert_marker(conn, "secrets", item.get("chapter_id", ""), item)

    def list_secrets(self, status: str = "") -> List[Dict[str, Any]]:
        sql = "select id, title, status, description, chapter_id, deadline_chapter, reveal_chapter, pressure_level, related_characters, user_priority, plan_chapter from secrets"
        params = (status,) if status else ()
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql + (" where status = ?" if status else "") + " order by chapter_id", params).fetchall()
        return [self._marker_row(r) for r in rows]

    @db_write_lock
    def log_llm_cost(
        self,
        call_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        project_id: str = ""
    ) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into llm_cost_log (call_id, model, input_tokens, output_tokens, input_cost_cny, output_cost_cny, project_id)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (call_id, model, input_tokens, output_tokens, input_cost, output_cost, project_id)
                )

    def get_llm_cost_summary(self, project_id: str = "") -> Dict[str, Any]:
        """Aggregate LLM cost rows for monitor UI (amounts stored in input/output_cost_cny columns)."""
        empty = {
            "call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_cost_cny": 0.0,
            "today_tokens": 0,
            "today_cost_cny": 0.0,
        }
        if not self.db_path.is_file():
            return empty
        try:
            with safe_connection(self.db_path) as conn:
                where = ""
                params: tuple = ()
                if project_id:
                    where = " where project_id = ?"
                    params = (project_id,)
                row = conn.execute(
                    f"""
                    select
                      count(*) as call_count,
                      coalesce(sum(input_tokens), 0) as input_tokens,
                      coalesce(sum(output_tokens), 0) as output_tokens,
                      coalesce(sum(input_cost_cny), 0) as input_cost_cny,
                      coalesce(sum(output_cost_cny), 0) as output_cost_cny
                    from llm_cost_log{where}
                    """,
                    params,
                ).fetchone()
                today_where = " where date(created_at, 'localtime') = date('now', 'localtime')"
                today_params: tuple = ()
                if project_id:
                    today_where += " and project_id = ?"
                    today_params = (project_id,)
                today_row = conn.execute(
                    f"""
                    select
                      coalesce(sum(input_tokens + output_tokens), 0) as tokens,
                      coalesce(sum(input_cost_cny + output_cost_cny), 0) as cost_cny
                    from llm_cost_log{today_where}
                    """,
                    today_params,
                ).fetchone()
        except Exception as exc:
            import logging

            logging.getLogger("state.history_repo").warning(
                "Failed to query llm cost summary: %s", exc
            )
            return empty
        if not row:
            return empty
        input_tokens = int(row[1] or 0)
        output_tokens = int(row[2] or 0)
        total_cost = float(row[3] or 0) + float(row[4] or 0)
        today_tokens = int(today_row[0] or 0) if today_row else 0
        today_cost = float(today_row[1] or 0) if today_row else 0.0
        return {
            "call_count": int(row[0] or 0),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "total_cost_cny": round(total_cost, 6),
            "today_tokens": today_tokens,
            "today_cost_cny": round(today_cost, 6),
        }

    def get_average_cost_per_scene(self) -> Tuple[float, float]:
        """Return average input_tokens and output_tokens per call. Explicit exception logger added."""
        try:
            with safe_connection(self.db_path) as conn:
                row = conn.execute("select avg(input_tokens), avg(output_tokens) from llm_cost_log").fetchone()
                if row and row[0] is not None:
                    return float(row[0]), float(row[1])
        except Exception as exc:
            import logging
            logging.getLogger("state.history_repo").warning("Failed to query average token costs from database, using defaults: %s", exc)
        return 1500.0, 800.0

    @db_write_lock
    def save_prompt_version(self, role: str, content: str, note: str = "", is_default: bool = False) -> int:
        with safe_connection(self.db_path) as conn:
            with conn:
                row = conn.execute(
                    "select version, content from prompt_versions where role = ? order by version desc limit 1",
                    (role,)
                ).fetchone()

                if row:
                    last_version, last_content = row[0], row[1]
                    if last_content == content:
                        return last_version
                    new_version = last_version + 1
                else:
                    new_version = 1

                conn.execute(
                    """
                    insert into prompt_versions (role, content, version, note, is_default)
                    values (?, ?, ?, ?, ?)
                    """,
                    (role, content, new_version, note, 1 if is_default else 0)
                )
                return new_version

    def get_latest_prompt_version(self, role: str) -> Dict[str, Any]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select id, role, content, version, saved_at, note, is_default from prompt_versions where role = ? order by version desc limit 1",
                (role,)
            ).fetchone()
            if row:
                return dict(row)
        return {}

    @db_write_lock
    def save_task(
        self,
        task_id: str,
        chapter_id: str,
        goal: str,
        dry_run: bool,
        status: str,
    ) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into tasks (id, chapter_id, goal, dry_run, status)
                    values (?, ?, ?, ?, ?)
                    on conflict(id) do update set
                      chapter_id=excluded.chapter_id,
                      goal=excluded.goal,
                      dry_run=excluded.dry_run,
                      status=excluded.status
                    """,
                    (task_id, chapter_id, goal, 1 if dry_run else 0, status),
                )

    @db_write_lock
    def update_task_progress(self, task_id: str, progress: Dict[str, Any]) -> None:
        progress_str = json.dumps(progress, ensure_ascii=False)
        step = progress.get("step")
        with safe_connection(self.db_path) as conn:
            with conn:
                if step:
                    conn.execute(
                        """
                        update tasks set
                          progress = ?,
                          current_step = ?,
                          pipeline_version = ?,
                          updated_at = datetime('now', 'localtime')
                        where id = ?
                        """,
                        (progress_str, step, "Chapter Pipeline v1.0", task_id),
                    )
                else:
                    conn.execute(
                        "update tasks set progress = ?, updated_at = datetime('now', 'localtime') where id = ?",
                        (progress_str, task_id),
                    )

    @db_write_lock
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        llm_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        res_str = json.dumps(result, ensure_ascii=False) if result else None
        logs_str = json.dumps(llm_logs, ensure_ascii=False) if llm_logs else None
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    update tasks set
                      status = ?,
                      result = coalesce(?, result),
                      error = coalesce(?, error),
                      llm_logs = coalesce(?, llm_logs),
                      updated_at = datetime('now', 'localtime')
                    where id = ?
                    """,
                    (status, res_str, error, logs_str, task_id),
                )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select id, chapter_id, goal, dry_run, status, result, error, progress, llm_logs, current_step, pipeline_version, updated_at, created_at from tasks where id = ?",
                (task_id,),
            ).fetchone()
            if row:
                t = dict(row)
                t["task_id"] = t.pop("id")
                t["dry_run"] = bool(t["dry_run"])
                t["result"] = json.loads(t["result"]) if t["result"] else None
                t["progress"] = json.loads(t["progress"]) if t["progress"] else None
                t["llm_logs"] = json.loads(t["llm_logs"]) if t["llm_logs"] else None
                return t
        return None

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "select id, chapter_id, goal, dry_run, status, result, error, progress, llm_logs, current_step, pipeline_version, updated_at, created_at from tasks order by created_at desc limit ?",
                (limit,),
            ).fetchall()
            results = []
            for r in rows:
                t = dict(r)
                t["task_id"] = t.pop("id")
                t["dry_run"] = bool(t["dry_run"])
                t["result"] = json.loads(t["result"]) if t["result"] else None
                t["progress"] = json.loads(t["progress"]) if t["progress"] else None
                t["llm_logs"] = json.loads(t["llm_logs"]) if t["llm_logs"] else None
                results.append(t)
            return results

    @db_write_lock
    def delete_old_tasks(self, max_tasks: int = 50) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                rows = conn.execute(
                    "select id from tasks where status in ('completed', 'failed') order by created_at desc"
                ).fetchall()
                if len(rows) > max_tasks:
                    to_delete = [r[0] for r in rows[max_tasks:]]
                    conn.executemany("delete from tasks where id = ?", [(i,) for i in to_delete])
                    conn.executemany("delete from task_logs where task_id = ?", [(i,) for i in to_delete])

    @db_write_lock
    def update_task_chapter_id(self, task_id: str, chapter_id: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    "update tasks set chapter_id = ? where id = ?",
                    (chapter_id, task_id)
                )

    @db_write_lock
    def delete_chapters_index(self, chapter_ids: List[str]) -> None:
        if not chapter_ids:
            return
        from novel_agent.services.chapter_state_cleanup import purge_chapter_narrative_state
        cids = [str(x) for x in chapter_ids]
        with safe_connection(self.db_path) as conn:
            with conn:
                for chapter_id in cids:
                    purge_chapter_narrative_state(conn, self.root_dir, chapter_id)

    def clean_interrupted_tasks(self) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    "update tasks set status = 'failed', error = '服务重启，任务意外中断' where status in ('pending', 'running')"
                )

    @db_write_lock
    def update_task_step(self, task_id: str, step: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    "update tasks set current_step = ?, updated_at = datetime('now', 'localtime') where id = ?",
                    (step, task_id)
                )

    @db_write_lock
    def save_chapter_version(
        self,
        chapter_id: str,
        version_name: str,
        content: str,
        plan: Optional[str] = None,
        is_active: bool = False,
        note: str = "",
        version_id: Optional[str] = None
    ) -> str:
        from novel_agent.scripts.count_chars import count_chinese_chars
        word_count = count_chinese_chars(content)
        v_id = version_id or str(uuid.uuid4())
        active_val = 1 if is_active else 0
        with safe_connection(self.db_path) as conn:
            with conn:
                if active_val == 1:
                    conn.execute(
                        "update chapter_versions set is_active = 0 where chapter_id = ?",
                        (chapter_id,)
                    )
                conn.execute(
                    """
                    insert into chapter_versions (id, chapter_id, version_name, content, plan, is_active, word_count, note)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(id) do update set
                      version_name = excluded.version_name,
                      content = excluded.content,
                      plan = excluded.plan,
                      is_active = excluded.is_active,
                      word_count = excluded.word_count,
                      note = excluded.note
                    """,
                    (v_id, chapter_id, version_name, content, plan or "", active_val, word_count, note)
                )
        return v_id

    def list_chapter_versions(self, chapter_id: str) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, chapter_id, version_name, content, plan, is_active, word_count, note, created_at
                from chapter_versions
                where chapter_id = ?
                order by created_at asc
                """,
                (chapter_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_chapter_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select id, chapter_id, version_name, content, plan, is_active, word_count, note, created_at
                from chapter_versions
                where id = ?
                """,
                (version_id,)
            ).fetchone()
        return dict(row) if row else None

    @db_write_lock
    def set_active_chapter_version(self, chapter_id: str, version_id: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                row = conn.execute(
                    "select chapter_id from chapter_versions where id = ?",
                    (version_id,)
                ).fetchone()
                if not row:
                    raise ValueError(f"Chapter version {version_id} not found.")
                if row[0] != chapter_id:
                    raise ValueError("Chapter version does not belong to the requested chapter.")
                conn.execute(
                    "update chapter_versions set is_active = 0 where chapter_id = ?",
                    (chapter_id,)
                )
                conn.execute(
                    "update chapter_versions set is_active = 1 where id = ? and chapter_id = ?",
                    (version_id, chapter_id)
                )

    @db_write_lock
    def delete_chapter_version(self, version_id: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                row = conn.execute("select is_active from chapter_versions where id = ?", (version_id,)).fetchone()
                if row and row[0] == 1:
                    raise ValueError("Cannot delete the currently active chapter version.")
                conn.execute("delete from chapter_versions where id = ?", (version_id,))

    def search_scrapbook(self, query: str = "", chapter_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
            select id, chapter_id, version_name, content, note, created_at
            from chapter_versions
            where is_active = 0
        """
        params = []
        if chapter_id:
            sql += " and chapter_id = ?"
            params.append(chapter_id)

        sql += " order by chapter_id asc, created_at desc"

        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        results = []
        import re
        for row in rows:
            content = row["content"] or ""
            norm_content = content.replace("\r\n", "\n")
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', norm_content) if p.strip()]
            if len(paragraphs) <= 1 and '\n' in norm_content:
                paragraphs = [p.strip() for p in norm_content.split('\n') if p.strip()]
            for idx, p in enumerate(paragraphs):
                if not query or query.lower() in p.lower():
                    results.append({
                        "version_id": row["id"],
                        "chapter_id": row["chapter_id"],
                        "version_name": row["version_name"],
                        "note": row["note"],
                        "paragraph_index": idx,
                        "text": p,
                        "created_at": row["created_at"]
                    })
        return results

    @db_write_lock
    def save_reader_feedback(
        self,
        chapter_id: str,
        bounce_rate: float,
        retention_rate: float,
        active_readers: int,
    ) -> str:
        feedback_id = uuid.uuid4().hex[:8]
        now = datetime.datetime.now().isoformat()
        with safe_connection(self.db_path) as conn:
            with conn:
                row = conn.execute("select id from reader_feedback where chapter_id = ?", (chapter_id,)).fetchone()
                if row:
                    conn.execute(
                        """
                        update reader_feedback
                        set bounce_rate = ?, retention_rate = ?, active_readers = ?, updated_at = ?
                        where chapter_id = ?
                        """,
                        (bounce_rate, retention_rate, active_readers, now, chapter_id)
                    )
                    fid = row[0]
                else:
                    conn.execute(
                        """
                        insert into reader_feedback (id, chapter_id, bounce_rate, retention_rate, active_readers, updated_at)
                        values (?, ?, ?, ?, ?, ?)
                        """,
                        (feedback_id, chapter_id, bounce_rate, retention_rate, active_readers, now)
                    )
                    fid = feedback_id
        return fid

    def get_reader_feedback(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select id, chapter_id, bounce_rate, retention_rate, active_readers, updated_at from reader_feedback where chapter_id = ?",
                (chapter_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def get_recent_feedback(self, limit: int = 5) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, chapter_id, bounce_rate, retention_rate, active_readers, updated_at
                from reader_feedback
                order by chapter_id desc limit ?
                """,
                (limit,)
            ).fetchall()
            results = [dict(r) for r in rows]
            results.reverse()
            return results
