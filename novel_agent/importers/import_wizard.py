"""Smart Import Wizard and Manuscript Demarcation Parser (Milestone E).

Recognizes Volumes, Chapters, and body text from TXT/Markdown documents,
generates preview trees with word counts, and safely commits to projects.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


VOLUME_PATTERNS = [
    re.compile(r"^\s*第\s*([0-9一二三四五六七八九十百千]+)\s*卷\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*Volume\s*(\d+)\s*[:：]?\s*(.*)$", re.IGNORECASE),
]

CHAPTER_PATTERNS = [
    re.compile(r"^\s*第\s*([0-9一二三四五六七八九十百千]+)\s*[章节回]\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*Chapter\s*(\d+)\s*[:：]?\s*(.*)$", re.IGNORECASE),
]


@dataclass
class ParsedChapter:
    index: int
    title: str
    content: str
    word_count: int = 0

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.content.strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "word_count": self.word_count,
            "preview": self.content[:100] + ("..." if len(self.content) > 100 else ""),
        }


@dataclass
class ParsedVolume:
    index: int
    title: str
    chapters: List[ParsedChapter] = field(default_factory=list)

    @property
    def total_words(self) -> int:
        return sum(c.word_count for c in self.chapters)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "chapter_count": len(self.chapters),
            "total_words": self.total_words,
            "chapters": [c.to_dict() for c in self.chapters],
        }


@dataclass
class ImportPreviewTree:
    total_chapters: int
    total_words: int
    volumes: List[ParsedVolume] = field(default_factory=list)
    unassigned_chapters: List[ParsedChapter] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chapters": self.total_chapters,
            "total_words": self.total_words,
            "volume_count": len(self.volumes),
            "volumes": [v.to_dict() for v in self.volumes],
            "unassigned_chapters": [c.to_dict() for c in self.unassigned_chapters],
        }


class ImportWizard:
    """Parses raw text files into structured Volumes and Chapters."""

    @classmethod
    def parse_text(cls, text: str) -> ImportPreviewTree:
        lines = text.splitlines()
        volumes: List[ParsedVolume] = []
        unassigned: List[ParsedChapter] = []

        current_volume: Optional[ParsedVolume] = None
        current_chapter_title: Optional[str] = None
        current_chapter_lines: List[str] = []
        chapter_counter = 0
        volume_counter = 0

        def flush_current_chapter():
            nonlocal chapter_counter, current_chapter_title, current_chapter_lines
            if current_chapter_title is not None:
                chapter_counter += 1
                body = "\n".join(current_chapter_lines).strip()
                ch = ParsedChapter(
                    index=chapter_counter,
                    title=current_chapter_title,
                    content=body,
                )
                if current_volume is not None:
                    current_volume.chapters.append(ch)
                else:
                    unassigned.append(ch)
            current_chapter_title = None
            current_chapter_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_chapter_title is not None:
                    current_chapter_lines.append(line)
                continue

            # Check for Volume heading
            is_volume = False
            for v_pat in VOLUME_PATTERNS:
                m = v_pat.match(stripped)
                if m:
                    flush_current_chapter()
                    volume_counter += 1
                    sub = m.group(2).strip()
                    raw_title = f"第{m.group(1)}卷 {sub}" if sub else f"第{m.group(1)}卷"
                    current_volume = ParsedVolume(
                        index=volume_counter,
                        title=raw_title,
                    )
                    volumes.append(current_volume)
                    is_volume = True
                    break
            if is_volume:
                continue

            # Check for Chapter heading
            is_chapter = False
            for c_pat in CHAPTER_PATTERNS:
                m = c_pat.match(stripped)
                if m:
                    flush_current_chapter()
                    sub_title = m.group(2).strip()
                    num_part = m.group(1).strip()
                    full_title = f"第{num_part}章 {sub_title}" if sub_title else f"第{num_part}章"
                    current_chapter_title = full_title
                    is_chapter = True
                    break
            if is_chapter:
                continue

            # Body line
            if current_chapter_title is not None:
                current_chapter_lines.append(line)
            else:
                # Content before the first detected chapter heading
                # If non-empty, initiate a default chapter 1 if not yet created
                if not unassigned and not volumes and chapter_counter == 0:
                    current_chapter_title = "序章 / 正文开始"
                    current_chapter_lines.append(line)

        flush_current_chapter()

        all_chapters = unassigned + [c for v in volumes for c in v.chapters]
        total_w = sum(c.word_count for c in all_chapters)

        return ImportPreviewTree(
            total_chapters=len(all_chapters),
            total_words=total_w,
            volumes=volumes,
            unassigned_chapters=unassigned,
        )

    @classmethod
    def commit_to_project(cls, tree: ImportPreviewTree, project_dir: Path) -> int:
        """Write parsed chapters into the project's SQLite database."""
        db_path = Path(project_dir) / "project.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        inserted_count = 0
        try:
            conn.execute(
                """
                create table if not exists documents (
                    id text primary key,
                    title text not null,
                    content text not null,
                    word_count integer not null,
                    chapter_index integer not null,
                    volume_name text,
                    created_at text not null
                )
                """
            )
            # Write unassigned chapters
            for ch in tree.unassigned_chapters:
                doc_id = f"doc_{ch.index:04d}"
                conn.execute(
                    """
                    insert or replace into documents (id, title, content, word_count, chapter_index, volume_name, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (doc_id, ch.title, ch.content, ch.word_count, ch.index, None, now_iso()),
                )
                inserted_count += 1

            # Write volume chapters
            for vol in tree.volumes:
                for ch in vol.chapters:
                    doc_id = f"doc_{ch.index:04d}"
                    conn.execute(
                        """
                        insert or replace into documents (id, title, content, word_count, chapter_index, volume_name, created_at)
                        values (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (doc_id, ch.title, ch.content, ch.word_count, ch.index, vol.title, now_iso()),
                    )
                    inserted_count += 1
            conn.commit()
        finally:
            conn.close()

        return inserted_count
