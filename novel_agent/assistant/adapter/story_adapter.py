"""StoryAdapter - Read-only adapter connecting ShanShan Assistant to INKREST story assets.

Adheres strictly to Principle 3.1: INKREST is the single source of truth.
This adapter never duplicates story databases; it provides typed read/query access
to project outlines, character cards, world rules, chapter texts, unified gate reports,
and SQLite narrative state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from novel_agent.assistant.models import CitationReference, SourceType


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_read_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class StoryAdapter:
    def __init__(self, root_dir: Optional[Path]):
        self.root_dir = Path(root_dir) if root_dir else None

    @property
    def is_valid(self) -> bool:
        return bool(self.root_dir and self.root_dir.is_dir())

    def get_project_meta(self) -> Dict[str, Any]:
        if not self.is_valid or not self.root_dir:
            return {}
        meta = _safe_read_json(self.root_dir / "config" / "project_meta.json")
        outline = _safe_read_json(self.root_dir / "workspace" / "outline.json")
        title = outline.get("chosen_title") or meta.get("title") or meta.get("name") or "未命名作品"
        return {
            "title": title,
            "genre": outline.get("genre") or meta.get("genre") or "通用",
            "premise": outline.get("premise") or meta.get("premise") or meta.get("description") or "",
            "target_chapters": outline.get("target_chapters") or meta.get("target_chapters") or 0,
        }

    def get_outline(self) -> Dict[str, Any]:
        if not self.is_valid or not self.root_dir:
            return {}
        return _safe_read_json(self.root_dir / "workspace" / "outline.json")

    def get_chapter_outline(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        outline = self.get_outline()
        macro = outline.get("macro_outline") or []
        target_str = str(chapter_id).lstrip("0") or "0"
        for arc in macro:
            if not isinstance(arc, dict):
                continue
            chapters = arc.get("chapter_list") or arc.get("chapters") or []
            if isinstance(chapters, list):
                for ch in chapters:
                    if isinstance(ch, dict):
                        ch_num = str(ch.get("chapter_id") or ch.get("id") or "").lstrip("0")
                        if ch_num == target_str or str(ch.get("chapter_id")) == str(chapter_id):
                            return ch
        return None

    def get_character_cards(self) -> List[Dict[str, Any]]:
        if not self.is_valid or not self.root_dir:
            return []
        cards_path = self.root_dir / "assets" / "character_cards.yaml"
        if not cards_path.is_file():
            cards_path = self.root_dir / "templates" / "assets" / "character_cards.yaml"
        doc = _safe_read_yaml(cards_path)
        characters = doc.get("characters")
        return characters if isinstance(characters, list) else []

    def get_character_by_name_or_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        norm = identifier.strip().lower()
        for char in self.get_character_cards():
            if not isinstance(char, dict):
                continue
            cid = str(char.get("id") or "").strip().lower()
            name = str(char.get("name") or "").strip().lower()
            if norm == cid or norm == name:
                return char
        return None

    def get_world_rules(self) -> Dict[str, Any]:
        if not self.is_valid or not self.root_dir:
            return {}
        rules_path = self.root_dir / "assets" / "world_rules.yaml"
        if not rules_path.is_file():
            rules_path = self.root_dir / "templates" / "assets" / "world_rules.yaml"
        return _safe_read_yaml(rules_path)

    def get_chapter_text(self, chapter_id: str) -> str:
        if not self.is_valid or not self.root_dir or not chapter_id:
            return ""
        safe_id = str(chapter_id).replace("/", "").replace("\\", "").strip()
        ch_dir = self.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
        if not ch_dir.is_dir():
            for p in (self.root_dir / "workspace" / "chapters").glob("chapter_*"):
                if p.is_dir() and p.name.endswith(safe_id):
                    ch_dir = p
                    break

        txt_file = ch_dir / "chapter.txt"
        if txt_file.is_file():
            try:
                return txt_file.read_text(encoding="utf-8")
            except Exception:
                pass

        json_file = ch_dir / "chapter.json"
        if json_file.is_file():
            data = _safe_read_json(json_file)
            content = data.get("content") or data.get("text") or ""
            if content:
                return str(content)
        return ""

    def get_gate_report(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_valid or not self.root_dir or not chapter_id:
            return None
        safe_id = str(chapter_id).replace("/", "").replace("\\", "").strip()
        gate_path = (
            self.root_dir
            / "workspace"
            / "chapters"
            / f"chapter_{safe_id}"
            / "reports"
            / "unified_gate.json"
        )
        if not gate_path.is_file():
            return None
        return _safe_read_json(gate_path)

    def search_characters_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Find characters from character cards that are mentioned in the given text."""
        if not text:
            return []
        found: List[Dict[str, Any]] = []
        for char in self.get_character_cards():
            if not isinstance(char, dict):
                continue
            name = char.get("name")
            cid = char.get("id")
            if (name and name in text) or (cid and str(cid) in text):
                found.append(char)
        return found

    def search_story_memory(
        self,
        query: str,
        before_chapter: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search story manuscript and summaries using FTS5 if available, with file scanner fallback."""
        if not self.is_valid or not self.root_dir or not query.strip():
            return []

        # 1. Try SQLiteStateStore FTS5
        sqlite_file = self.root_dir / "data" / "novel.sqlite"
        if sqlite_file.is_file():
            try:
                from novel_agent.state.sqlite_store import SQLiteStateStore
                store = SQLiteStateStore(self.root_dir)
                results = store.search_story(
                    query,
                    limit=limit,
                    before_chapter=before_chapter,
                )
                if results:
                    return results
            except Exception:
                pass

        # 2. Filesystem fallback: scan chapter.txt files up to before_chapter
        fallback_results: List[Dict[str, Any]] = []
        chapters_dir = self.root_dir / "workspace" / "chapters"
        if not chapters_dir.is_dir():
            return []

        q_terms = [t for t in query.split() if len(t) > 1]
        if not q_terms:
            q_terms = [query.strip()]

        for ch_dir in sorted(chapters_dir.glob("chapter_*")):
            if not ch_dir.is_dir():
                continue
            ch_id = ch_dir.name.replace("chapter_", "")
            if before_chapter:
                try:
                    if int(ch_id.lstrip("0") or "0") > int(str(before_chapter).lstrip("0") or "0"):
                        continue
                except ValueError:
                    pass

            txt_file = ch_dir / "chapter.txt"
            if not txt_file.is_file():
                continue
            try:
                content = txt_file.read_text(encoding="utf-8")
            except Exception:
                continue

            for term in q_terms:
                pos = content.find(term)
                if pos != -1:
                    start = max(0, pos - 40)
                    end = min(len(content), pos + len(term) + 80)
                    snippet = "…" + content[start:end].replace("\n", " ").strip() + "…"
                    fallback_results.append({
                        "memory_id": f"chapter:{ch_id}",
                        "kind": "chapter_text",
                        "text": snippet,
                        "source_chapter": ch_id,
                        "rank": 1.0,
                    })
                    break
            if len(fallback_results) >= limit:
                break

        return fallback_results

    def get_narrative_events(self, chapter_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve authoritative narrative events from SQLite if available."""
        if not self.is_valid or not self.root_dir:
            return []
        sqlite_file = self.root_dir / "data" / "novel.sqlite"
        if not sqlite_file.is_file():
            return []
        try:
            import sqlite3
            with sqlite3.connect(sqlite_file) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM narrative_events WHERE 1=1"
                params: List[Any] = []
                if chapter_id:
                    query += " AND chapter_id = ?"
                    params.append(str(chapter_id))
                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(query, params).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def resolve_citations(
        self,
        query: str,
        mentioned_characters: Optional[List[str]] = None,
        chapter_id: Optional[str] = None,
    ) -> List[CitationReference]:
        """Generate structured citation references for grounding answers."""
        citations: List[CitationReference] = []

        # 1. Match characters
        all_chars = self.get_character_cards()
        for char in all_chars:
            name = char.get("name") or char.get("id") or ""
            if not name:
                continue
            if (mentioned_characters and name in mentioned_characters) or (name in query):
                profile = char.get("fixed_profile") or {}
                motivation = profile.get("core_motivation") or char.get("motivation") or ""
                snippet = f"角色：{name} | 身份：{profile.get('role') or char.get('role') or '重要角色'} | 动机：{motivation}"
                citations.append(
                    CitationReference(
                        source_type=SourceType.CHARACTER,
                        source_id=str(char.get("id") or name),
                        title=f"人物卡 · {name}",
                        snippet=snippet[:180],
                    )
                )

        # 2. Match chapter outline
        if chapter_id:
            ch_outline = self.get_chapter_outline(chapter_id)
            if ch_outline:
                goal = ch_outline.get("goal") or ch_outline.get("summary") or ch_outline.get("title") or ""
                citations.append(
                    CitationReference(
                        source_type=SourceType.OUTLINE,
                        source_id=f"chapter_{chapter_id}",
                        chapter_id=str(chapter_id),
                        title=f"第 {chapter_id} 章大纲",
                        snippet=str(goal)[:180],
                    )
                )

        # 3. Match world rules
        world_rules = self.get_world_rules()
        for rule_key, rule_val in world_rules.items():
            if isinstance(rule_val, dict):
                r_title = rule_val.get("title") or rule_key
                r_desc = rule_val.get("description") or rule_val.get("content") or ""
                if r_title in query or (isinstance(r_desc, str) and any(w in query for w in r_title.split() if len(w) > 1)):
                    citations.append(
                        CitationReference(
                            source_type=SourceType.WORLD,
                            source_id=rule_key,
                            title=f"世界规则 · {r_title}",
                            snippet=str(r_desc)[:180],
                        )
                    )

        # 4. Match historical chapter manuscript / memory
        mem_results = self.search_story_memory(query, before_chapter=chapter_id, limit=2)
        for mem in mem_results:
            src_ch = mem.get("source_chapter")
            snippet = mem.get("text") or ""
            if src_ch and snippet:
                citations.append(
                    CitationReference(
                        source_type=SourceType.CHAPTER,
                        source_id=f"chapter_{src_ch}",
                        chapter_id=str(src_ch),
                        title=f"正文出处 · 第 {src_ch} 章",
                        snippet=snippet[:180],
                    )
                )

        return citations[:5]
