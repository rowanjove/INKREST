import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from novel_agent.state.sqlite_schema import db_write_lock, safe_connection


class StateRepositoryMixin:
    """Contains character, object, timeline relations, and candidate persistence methods."""
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
    def sync_state_update(self, chapter_id: str, update: Dict[str, Any]) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                self._sync_events(conn, chapter_id, update.get("events", []))
                self._sync_objects(conn, update.get("objects", []), chapter_id)
                self._sync_threads(conn, update.get("threads", []), chapter_id)
                self._sync_characters(conn, update.get("characters", {}))
                self._sync_timeline_nodes(conn, chapter_id, update.get("timeline_nodes", []))
                self._sync_timeline_edges(conn, chapter_id, update.get("timeline_edges", []))
                self._sync_markers(conn, chapter_id, update)
                self._sync_character_relations(conn, chapter_id, update.get("character_relations", []))

    def _sync_events(self, conn, chapter_id: str, events: List[Dict[str, Any]]) -> None:
        for event in events:
            if not event.get("id"):
                event["id"] = f"evt_{chapter_id}_{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                insert into events (
                  id, chapter_id, scene_id, summary, characters, objects, threads, payload
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                  chapter_id=excluded.chapter_id,
                  scene_id=excluded.scene_id,
                  summary=excluded.summary,
                  characters=excluded.characters,
                  objects=excluded.objects,
                  threads=excluded.threads,
                  payload=excluded.payload
                """,
                (
                    event.get("id"),
                    chapter_id,
                    event.get("scene_id", ""),
                    event.get("summary", ""),
                    self._json(event.get("characters", [])),
                    self._json(event.get("objects", [])),
                    self._json(event.get("threads", [])),
                    self._json(event),
                ),
            )

    def _sync_objects(self, conn, objects: List[Dict[str, Any]], chapter_id: str = "") -> None:
        for item in objects:
            if chapter_id and isinstance(item, dict):
                item = {**item, "last_chapter_id": chapter_id}
            conn.execute(
                """
                insert into objects (id, name, holder, status, payload)
                values (?, ?, ?, ?, ?)
                on conflict(id) do update set
                  name=excluded.name,
                  holder=excluded.holder,
                  status=excluded.status,
                  payload=excluded.payload
                """,
                (
                    item.get("id") or item.get("name"),
                    item.get("name", item.get("id", "")),
                    item.get("holder", ""),
                    item.get("status", ""),
                    self._json(item),
                ),
            )

    def _sync_threads(self, conn, threads: List[Dict[str, Any]], chapter_id: str = "") -> None:
        for thread in threads:
            if chapter_id and isinstance(thread, dict):
                thread = {**thread, "last_chapter_id": chapter_id}
            conn.execute(
                """
                insert into threads (id, title, status, summary, payload)
                values (?, ?, ?, ?, ?)
                on conflict(id) do update set
                  title=excluded.title,
                  status=excluded.status,
                  summary=excluded.summary,
                  payload=excluded.payload
                """,
                (
                    thread.get("id"),
                    thread.get("title", ""),
                    thread.get("status", ""),
                    thread.get("summary", ""),
                    self._json(thread),
                ),
            )

    def _sync_characters(self, conn, characters: Dict[str, Any]) -> None:
        for char_id, state in characters.items():
            conn.execute(
                """
                insert into character_state (id, name, location, emotion, payload)
                values (?, ?, ?, ?, ?)
                on conflict(id) do update set
                  name=excluded.name,
                  location=excluded.location,
                  emotion=excluded.emotion,
                  payload=excluded.payload
                """,
                (
                    char_id,
                    state.get("name", char_id) if isinstance(state, dict) else char_id,
                    state.get("location", "") if isinstance(state, dict) else "",
                    state.get("emotion", "") if isinstance(state, dict) else "",
                    self._json(state),
                ),
            )

    def _sync_timeline_nodes(self, conn, chapter_id: str, timeline_nodes: List[Dict[str, Any]]) -> None:
        for node in timeline_nodes:
            conn.execute(
                """
                insert into timeline_nodes (id, type, name, description, status, chapter_id, payload)
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                  type=excluded.type,
                  name=excluded.name,
                  description=excluded.description,
                  status=excluded.status,
                  chapter_id=excluded.chapter_id,
                  payload=excluded.payload
                """,
                (
                    node.get("id"),
                    node.get("type", ""),
                    node.get("name", ""),
                    node.get("description", ""),
                    node.get("status", ""),
                    chapter_id,
                    self._json(node),
                ),
            )

    def _sync_timeline_edges(self, conn, chapter_id: str, timeline_edges: List[Dict[str, Any]]) -> None:
        for edge in timeline_edges:
            conn.execute(
                """
                insert into timeline_edges (id, from_node, to_node, type, description, strength, change, chapter_id, payload)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                  from_node=excluded.from_node,
                  to_node=excluded.to_node,
                  type=excluded.type,
                  description=excluded.description,
                  strength=excluded.strength,
                  change=excluded.change,
                  chapter_id=excluded.chapter_id,
                  payload=excluded.payload
                """,
                (
                    edge.get("id"),
                    edge.get("from") or edge.get("fromNode") or edge.get("fromNodeId", ""),
                    edge.get("to") or edge.get("toNode") or edge.get("toNodeId", ""),
                    edge.get("type", ""),
                    edge.get("description", ""),
                    edge.get("strength", ""),
                    edge.get("change", ""),
                    chapter_id,
                    self._json(edge),
                ),
            )

    def _sync_markers(self, conn, chapter_id: str, update: Dict[str, Any]) -> None:
        for foreshadow in update.get("foreshadows", []):
            self._upsert_marker(conn, "foreshadows", chapter_id, foreshadow)
        for hook in update.get("hooks", []):
            self._upsert_marker(conn, "hooks", chapter_id, hook)
        for promise in update.get("reader_promises", []):
            self._upsert_marker(conn, "reader_promises", chapter_id, promise)
        for secret in update.get("secrets", []):
            self._upsert_marker(conn, "secrets", chapter_id, secret)

    def _sync_character_relations(self, conn, chapter_id: str, relations: List[Dict[str, Any]]) -> None:
        for rel in relations:
            source = rel.get("source_char") or rel.get("source")
            target = rel.get("target_char") or rel.get("target")
            if not source or not target:
                continue

            rel_type = rel.get("relation_type") or rel.get("type", "")
            try:
                intensity = float(rel.get("intensity", 0.0))
            except (ValueError, TypeError):
                intensity = 0.0
            since = int(chapter_id) if chapter_id.isdigit() else 1
            desc = rel.get("description", "")

            row = conn.execute(
                "select id from character_relations where source_char = ? and target_char = ?",
                (source, target)
            ).fetchone()
            if row:
                conn.execute(
                    """
                    update character_relations set
                      relation_type = ?,
                      intensity = ?,
                      last_updated = ?,
                      description = ?
                    where id = ?
                    """,
                    (rel_type, intensity, since, desc, row[0])
                )
            else:
                conn.execute(
                    """
                    insert into character_relations (
                      source_char, target_char, relation_type, intensity, since_chapter, last_updated, description
                    )
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (source, target, rel_type, intensity, since, since, desc)
                )

    def _upsert_marker(self, conn, table: str, chapter_id: str, item: Dict[str, Any]) -> None:
        allowed_tables = {"foreshadows", "hooks", "reader_promises", "secrets"}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")
        conn.execute(
            f"""
            insert into {table} (
              id, title, status, description, chapter_id,
              deadline_chapter, reveal_chapter, pressure_level, related_characters,
              user_priority, plan_chapter, payload
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
              title=excluded.title,
              status=excluded.status,
              description=excluded.description,
              chapter_id=excluded.chapter_id,
              deadline_chapter=excluded.deadline_chapter,
              reveal_chapter=excluded.reveal_chapter,
              pressure_level=excluded.pressure_level,
              related_characters=excluded.related_characters,
              user_priority=excluded.user_priority,
              plan_chapter=excluded.plan_chapter,
              payload=excluded.payload
            """,
            (
                item.get("id"),
                item.get("title", item.get("name", "")),
                item.get("status", ""),
                item.get("description", ""),
                chapter_id,
                item.get("deadline_chapter", ""),
                item.get("reveal_chapter", ""),
                item.get("pressure_level", ""),
                self._json(item.get("related_characters", [])),
                int(item.get("user_priority", 0)),
                str(item.get("plan_chapter", "")),
                self._json(item),
            ),
        )

    @db_write_lock
    def save_character_relation(
        self,
        source_char: str,
        target_char: str,
        relation_type: str,
        intensity: float,
        since_chapter: int,
        last_updated: int,
        description: str
    ) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                row = conn.execute(
                    "select id from character_relations where source_char = ? and target_char = ?",
                    (source_char, target_char)
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        update character_relations set
                          relation_type = ?,
                          intensity = ?,
                          since_chapter = ?,
                          last_updated = ?,
                          description = ?
                        where id = ?
                        """,
                        (relation_type, intensity, since_chapter, last_updated, description, row[0])
                    )
                else:
                    conn.execute(
                        """
                        insert into character_relations (
                          source_char, target_char, relation_type, intensity, since_chapter, last_updated, description
                        )
                        values (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (source_char, target_char, relation_type, intensity, since_chapter, last_updated, description)
                    )

    def list_character_relations(self) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, source_char, target_char, relation_type, intensity, since_chapter, last_updated, description from character_relations").fetchall()
        return [dict(r) for r in rows]

    @db_write_lock
    def delete_character_relation(self, relation_id: int) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute("delete from character_relations where id = ?", (relation_id,))

    def list_characters(self) -> Dict[str, Any]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, name, location, emotion, payload from character_state").fetchall()
        result = {}
        for row in rows:
            payload = self._loads(row["payload"]) if row["payload"] else {}
            result[row["id"]] = {
                "name": row["name"],
                "location": row["location"],
                "emotion": row["emotion"],
                **{k: v for k, v in payload.items() if k not in ("name", "location", "emotion")},
            }
        return result

    def list_foreshadows(self) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, title, status, description, chapter_id, deadline_chapter, reveal_chapter, pressure_level, related_characters, user_priority, plan_chapter from foreshadows order by chapter_id").fetchall()
        return [self._marker_row(r) for r in rows]

    def list_hooks(self) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, title, status, description, chapter_id, deadline_chapter, reveal_chapter, pressure_level, related_characters, user_priority, plan_chapter from hooks order by chapter_id").fetchall()
        return [self._marker_row(r) for r in rows]

    def list_objects(self) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, name, holder, status from objects").fetchall()
        return [{"id": r["id"], "name": r["name"], "holder": r["holder"], "status": r["status"]} for r in rows]

    def list_threads(self) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("select id, title, status, summary from threads").fetchall()
        return [{"id": r["id"], "title": r["title"], "status": r["status"], "summary": r["summary"]} for r in rows]

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "select id, chapter_id, scene_id, summary, characters, objects, threads from events order by chapter_id desc, id desc limit ?",
                (limit,),
            ).fetchall()
        return [self._event_row(row) for row in rows]

    def get_continuity_state(self) -> Dict[str, Any]:
        return {
            "characters": self.list_characters(),
            "foreshadows": self.list_foreshadows(),
            "hooks": self.list_hooks(),
            "reader_promises": self.list_reader_promises(),
            "secrets": self.list_secrets(),
            "objects": self.list_objects(),
            "threads": self.list_threads(),
        }

    def create_snapshot(self, chapter_id: str) -> None:
        snapshot_dir = self.root_dir / "state" / "snapshots" / f"chapter_{chapter_id}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        state = self.get_continuity_state()
        (snapshot_dir / "state_snapshot.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @db_write_lock
    def save_state_change_candidates(self, chapter_id: str, candidates: List[Dict[str, Any]]) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                for cand in candidates:
                    cand_id = cand.get("id") or f"cand_{chapter_id}_{uuid.uuid4().hex[:8]}"
                    conn.execute(
                        """
                        insert into state_change_candidates (
                          id, chapter_id, entity_type, entity_id, change_type, old_value, new_value, evidence_quote, confidence, status
                        )
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        on conflict(id) do update set
                          chapter_id=excluded.chapter_id,
                          entity_type=excluded.entity_type,
                          entity_id=excluded.entity_id,
                          change_type=excluded.change_type,
                          old_value=excluded.old_value,
                          new_value=excluded.new_value,
                          evidence_quote=excluded.evidence_quote,
                          confidence=excluded.confidence,
                          status=excluded.status
                        """,
                        (
                            cand_id,
                            chapter_id,
                            cand.get("entity_type"),
                            cand.get("entity_id"),
                            cand.get("change_type", "update"),
                            self._json(cand.get("old_value")),
                            self._json(cand.get("new_value")),
                            cand.get("evidence_quote", ""),
                            cand.get("confidence", 1.0),
                            cand.get("status", "pending")
                        )
                    )

    def list_state_change_candidates(self, chapter_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "select id, chapter_id, entity_type, entity_id, change_type, old_value, new_value, evidence_quote, confidence, status, created_at from state_change_candidates"
        where_clauses = []
        params = []
        if chapter_id:
            where_clauses.append("chapter_id = ?")
            params.append(chapter_id)
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if where_clauses:
            sql += " where " + " and ".join(where_clauses)
        sql += " order by created_at"
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, tuple(params)).fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "chapter_id": r["chapter_id"],
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "change_type": r["change_type"],
                    "old_value": self._loads(r["old_value"]) if r["old_value"] else None,
                    "new_value": self._loads(r["new_value"]) if r["new_value"] else None,
                    "evidence_quote": r["evidence_quote"],
                    "confidence": r["confidence"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                })
            return results

    @db_write_lock
    def update_candidate_status(self, candidate_id: str, status: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    "update state_change_candidates set status = ? where id = ?",
                    (status, candidate_id)
                )

    @db_write_lock
    def accept_chapter_candidates(self, chapter_id: str) -> None:
        candidates = self.list_state_change_candidates(chapter_id=chapter_id, status="pending")
        if not candidates:
            return

        update = {}
        for cand in candidates:
            etype = cand["entity_type"]
            val = cand["new_value"]
            eid = cand["entity_id"]
            if etype == "event":
                update.setdefault("events", []).append(val)
            elif etype == "character":
                update.setdefault("characters", {})[eid] = val
            elif etype == "object":
                update.setdefault("objects", []).append(val)
            elif etype == "thread":
                update.setdefault("threads", []).append(val)
            elif etype == "foreshadow":
                update.setdefault("foreshadows", []).append(val)
            elif etype == "hook":
                update.setdefault("hooks", []).append(val)
            elif etype == "reader_promise":
                update.setdefault("reader_promises", []).append(val)
            elif etype == "secret":
                update.setdefault("secrets", []).append(val)
            elif etype == "character_relation":
                update.setdefault("character_relations", []).append(val)
            elif etype == "timeline_node":
                update.setdefault("timeline_nodes", []).append(val)
            elif etype == "timeline_edge":
                update.setdefault("timeline_edges", []).append(val)

        with safe_connection(self.db_path) as conn:
            with conn:
                if update.get("events"):
                    self._sync_events(conn, chapter_id, update["events"])
                if update.get("objects"):
                    self._sync_objects(conn, update["objects"])
                if update.get("threads"):
                    self._sync_threads(conn, update["threads"])
                if update.get("characters"):
                    self._sync_characters(conn, update["characters"])
                if update.get("timeline_nodes"):
                    self._sync_timeline_nodes(conn, chapter_id, update["timeline_nodes"])
                if update.get("timeline_edges"):
                    self._sync_timeline_edges(conn, chapter_id, update["timeline_edges"])
                self._sync_markers(conn, chapter_id, update)
                if update.get("character_relations"):
                    self._sync_character_relations(conn, chapter_id, update["character_relations"])

                conn.executemany(
                    "update state_change_candidates set status = 'accepted' where id = ?",
                    [(c["id"],) for c in candidates]
                )

    @db_write_lock
    def accept_candidate(self, candidate_id: str) -> None:
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "select id, chapter_id, entity_type, entity_id, new_value from state_change_candidates where id = ? and status = 'pending'",
                    (candidate_id,)
                ).fetchone()
                if not row:
                    return

                chapter_id = row["chapter_id"]
                etype = row["entity_type"]
                eid = row["entity_id"]
                val = self._loads(row["new_value"]) if row["new_value"] else {}

                if etype == "event":
                    self._sync_events(conn, chapter_id, [val])
                elif etype == "character":
                    self._sync_characters(conn, {eid: val})
                elif etype == "object":
                    self._sync_objects(conn, [val])
                elif etype == "thread":
                    self._sync_threads(conn, [val])
                elif etype == "foreshadow":
                    self._upsert_marker(conn, "foreshadows", chapter_id, val)
                elif etype == "hook":
                    self._upsert_marker(conn, "hooks", chapter_id, val)
                elif etype == "reader_promise":
                    self._upsert_marker(conn, "reader_promises", chapter_id, val)
                elif etype == "secret":
                    self._upsert_marker(conn, "secrets", chapter_id, val)
                elif etype == "character_relation":
                    self._sync_character_relations(conn, chapter_id, [val])
                elif etype == "timeline_node":
                    self._sync_timeline_nodes(conn, chapter_id, [val])
                elif etype == "timeline_edge":
                    self._sync_timeline_edges(conn, chapter_id, [val])

                conn.execute(
                    "update state_change_candidates set status = 'accepted' where id = ?",
                    (candidate_id,)
                )
