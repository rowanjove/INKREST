import json
import sqlite3
import uuid
import threading
import queue
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


class SQLiteWriteQueue:
    _instances = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: Path):
        db_path_str = str(db_path.resolve())
        with cls._lock:
            if db_path_str not in cls._instances:
                cls._instances[db_path_str] = cls(db_path)
            return cls._instances[db_path_str]

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True, name=f"SQLiteWriter-{db_path.name}")
        self._thread.start()

    def submit(self, fn, *args, **kwargs) -> Future:
        future = Future()
        self._queue.put((fn, args, kwargs, future))
        return future

    def _worker(self):
        while True:
            fn, args, kwargs, future = self._queue.get()
            try:
                result = fn(*args, **kwargs)
                future.set_result(result)
            except BaseException as e:
                future.set_exception(e)
            finally:
                self._queue.task_done()


def db_write_lock(func):
    def wrapper(self, *args, **kwargs):
        write_queue = SQLiteWriteQueue.get_instance(self.db_path)
        future = write_queue.submit(func, self, *args, **kwargs)
        return future.result()
    return wrapper


class safe_connection:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.__enter__()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.conn.__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.conn.close()


class SchemaMixin:
    """Contains schema initialization and dynamic migration logic for SQLiteStateStore."""
    db_path: Path

    def _init_schema(self) -> None:
        with safe_connection(self.db_path) as conn:
            conn.executescript(
                """
                create table if not exists events (
                  id text primary key,
                  chapter_id text not null,
                  scene_id text,
                  summary text,
                  characters text,
                  objects text,
                  threads text,
                  payload text
                );
                create table if not exists objects (
                  id text primary key,
                  name text,
                  holder text,
                  status text,
                  payload text
                );
                create table if not exists threads (
                  id text primary key,
                  title text,
                  status text,
                  summary text,
                  payload text
                );
                create table if not exists character_state (
                  id text primary key,
                  name text,
                  location text,
                  emotion text,
                  payload text
                );
                create table if not exists chapters (
                  id text primary key,
                  title text,
                  final_path text,
                  word_count integer,
                  risk_level text
                );
                create table if not exists chapter_summaries (
                  chapter_id text primary key,
                  summary text,
                  summary_path text
                );
                create table if not exists timeline_nodes (
                  id text primary key,
                  type text,
                  name text,
                  description text,
                  status text,
                  chapter_id text,
                  payload text
                );
                create table if not exists timeline_edges (
                  id text primary key,
                  from_node text,
                  to_node text,
                  type text,
                  description text,
                  strength text,
                  change text,
                  chapter_id text,
                  payload text
                );
                create table if not exists foreshadows (
                  id text primary key,
                  title text,
                  status text,
                  description text,
                  chapter_id text,
                  deadline_chapter text,
                  reveal_chapter text,
                  pressure_level text,
                  related_characters text,
                  user_priority integer default 0,
                  plan_chapter text,
                  payload text
                );
                create table if not exists hooks (
                  id text primary key,
                  title text,
                  status text,
                  description text,
                  chapter_id text,
                  deadline_chapter text,
                  reveal_chapter text,
                  pressure_level text,
                  related_characters text,
                  user_priority integer default 0,
                  plan_chapter text,
                  payload text
                );
                create table if not exists reader_promises (
                  id text primary key,
                  title text,
                  status text,
                  description text,
                  chapter_id text,
                  deadline_chapter text,
                  reveal_chapter text,
                  pressure_level text,
                  related_characters text,
                  user_priority integer default 0,
                  plan_chapter text,
                  payload text
                );
                create table if not exists secrets (
                  id text primary key,
                  title text,
                  status text,
                  description text,
                  chapter_id text,
                  deadline_chapter text,
                  reveal_chapter text,
                  pressure_level text,
                  related_characters text,
                  user_priority integer default 0,
                  plan_chapter text,
                  payload text
                );
                create table if not exists vector_embeddings (
                  id text primary key,
                  type text,
                  text text,
                  embedding blob,
                  metadata text
                );
                create index if not exists idx_vector_embeddings_type on vector_embeddings(type);

                -- Prompt versions history
                create table if not exists prompt_versions (
                  id integer primary key autoincrement,
                  role text not null,
                  content text not null,
                  version integer not null,
                  saved_at datetime default current_timestamp,
                  note text,
                  is_default boolean default 0
                );
                create index if not exists idx_prompt_versions_role on prompt_versions(role);

                -- Asset versions history
                create table if not exists asset_versions (
                  id integer primary key autoincrement,
                  asset_name text not null,
                  content text not null,
                  version integer not null,
                  saved_at datetime default current_timestamp,
                  note text
                );
                create index if not exists idx_asset_versions_name on asset_versions(asset_name);

                -- Chapter rewrite history
                create table if not exists chapter_rewrites (
                  id integer primary key autoincrement,
                  chapter_id text not null,
                  version integer not null,
                  content text not null,
                  word_count integer,
                  rewrite_reason text,
                  created_at datetime default current_timestamp
                );
                create index if not exists idx_chapter_rewrites_chapter on chapter_rewrites(chapter_id);

                -- LLM Cost Tracking log
                create table if not exists llm_cost_log (
                  id integer primary key autoincrement,
                  call_id text,
                  model text,
                  input_tokens integer,
                  output_tokens integer,
                  input_cost_cny real,
                  output_cost_cny real,
                  created_at datetime default current_timestamp,
                  project_id text
                );

                -- Character relations graph
                create table if not exists character_relations (
                  id integer primary key autoincrement,
                  source_char text not null,
                  target_char text not null,
                  relation_type text,
                  intensity real,
                  since_chapter integer,
                  last_updated integer,
                  description text
                );
                create index if not exists idx_char_rel_source on character_relations(source_char);
                create index if not exists idx_char_rel_target on character_relations(target_char);

                -- Background task management tables
                create table if not exists tasks (
                  id text primary key,
                  chapter_id text,
                  goal text,
                  dry_run integer default 0,
                  status text,
                  result text,
                  error text,
                  progress text,
                  llm_logs text,
                  created_at datetime default current_timestamp
                );
                create table if not exists task_logs (
                  id integer primary key autoincrement,
                  task_id text not null,
                  level text,
                  message text,
                  step text,
                  timestamp real,
                  created_at datetime default current_timestamp
                );
                create index if not exists idx_task_logs_task_id on task_logs(task_id);
                create table if not exists task_status_events (
                  id integer primary key autoincrement,
                  task_id text not null,
                  from_status text,
                  to_status text not null,
                  reason text,
                  resumable_from text,
                  created_at datetime default current_timestamp
                );
                create index if not exists idx_task_status_events_task_id on task_status_events(task_id);

                -- State change candidates pending approval
                create table if not exists state_change_candidates (
                  id text primary key,
                  chapter_id text,
                  entity_type text,
                  entity_id text,
                  change_type text,
                  old_value text,
                  new_value text,
                  evidence_quote text,
                  confidence real,
                  status text default 'pending',
                  created_at datetime default current_timestamp
                );
                create index if not exists idx_state_change_candidates_chapter_id on state_change_candidates(chapter_id);

                -- Chapter versions
                create table if not exists chapter_versions (
                  id text primary key,
                  chapter_id text not null,
                  version_name text not null,
                  content text not null,
                  plan text,
                  is_active integer default 0,
                  word_count integer default 0,
                  note text,
                  created_at datetime default current_timestamp
                );
                create index if not exists idx_chapter_versions_chapter_id on chapter_versions(chapter_id);

                -- Reader feedback table
                create table if not exists reader_feedback (
                  id text primary key,
                  chapter_id text not null,
                  bounce_rate real default 0.0,
                  retention_rate real default 0.0,
                  active_readers integer default 0,
                  updated_at datetime default current_timestamp
                );
                create unique index if not exists idx_reader_feedback_chapter_id on reader_feedback(chapter_id);
                """
            )
            self._ensure_marker_columns(conn)
            self._ensure_task_columns(conn)
            self._ensure_chapter_index_columns(conn)

    def _ensure_chapter_index_columns(self, conn) -> None:
        columns = {
            row[1] for row in conn.execute("pragma table_info(chapters)").fetchall()
        }
        if "has_final" not in columns:
            conn.execute("alter table chapters add column has_final integer default 0")
        if "gate_status" not in columns:
            conn.execute("alter table chapters add column gate_status text default ''")
        if "indexed_at" not in columns:
            conn.execute("alter table chapters add column indexed_at real default 0")

    def _ensure_task_columns(self, conn) -> None:
        columns = {
            row[1]
            for row in conn.execute("pragma table_info(tasks)").fetchall()
        }
        if "current_step" not in columns:
            conn.execute("alter table tasks add column current_step text")
        if "pipeline_version" not in columns:
            conn.execute("alter table tasks add column pipeline_version text")
        if "updated_at" not in columns:
            conn.execute("alter table tasks add column updated_at datetime")
        if "last_heartbeat" not in columns:
            conn.execute("alter table tasks add column last_heartbeat datetime")
        if "resumable_from" not in columns:
            conn.execute("alter table tasks add column resumable_from text")
        if "status_reason" not in columns:
            conn.execute("alter table tasks add column status_reason text")

    def _ensure_marker_columns(self, conn) -> None:
        for table in ("foreshadows", "hooks", "reader_promises", "secrets"):
            columns = {
                row[1]
                for row in conn.execute(f"pragma table_info({table})").fetchall()
            }
            for name in ("deadline_chapter", "reveal_chapter", "pressure_level", "related_characters", "user_priority", "plan_chapter"):
                if name not in columns:
                    if name == "user_priority":
                        conn.execute(f"alter table {table} add column {name} integer default 0")
                    else:
                        conn.execute(f"alter table {table} add column {name} text")
