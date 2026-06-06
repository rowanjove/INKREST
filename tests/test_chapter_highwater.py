"""Chapter high-water cache and bounded writing-context scans."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from novel_agent.services.chapter_highwater import (
    bump_chapter_written,
    load_highwater,
    resolve_max_generated_chapter_num,
)
from novel_agent.services.rolling_planner import format_chapter_id, max_generated_chapter_num
from novel_agent.services.writing_context import gather_recent_writing_context


def _write_chapter(root: Path, num: int, *, body_len: int = 200) -> None:
    cid = format_chapter_id(num)
    d = root / "workspace" / "chapters" / f"chapter_{cid}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapter_final.txt").write_text("x" * body_len, encoding="utf-8")


def test_highwater_avoids_full_iterdir_at_epic_scale(tmp_path: Path) -> None:
    for n in range(1, 51):
        _write_chapter(tmp_path, n)
    # 稀疏占位目录（无正文），模拟千章磁盘上的「空洞」章号
    sparse = tmp_path / "workspace" / "chapters" / "chapter_3000"
    sparse.mkdir(parents=True, exist_ok=True)

    bump_chapter_written(tmp_path, "050", pipeline_complete=True)

    def complete(cid: str) -> bool:
        return int(cid) <= 50

    assert resolve_max_generated_chapter_num(tmp_path, complete) == 50
    assert max_generated_chapter_num(tmp_path, complete) == 50


def test_highwater_forward_verifies_after_cache(tmp_path: Path) -> None:
    for n in range(1, 6):
        _write_chapter(tmp_path, n)
    bump_chapter_written(tmp_path, "5", pipeline_complete=True)

    def complete(cid: str) -> bool:
        return int(cid) <= 5

    assert resolve_max_generated_chapter_num(tmp_path, complete) == 5
    _write_chapter(tmp_path, 6)
    bump_chapter_written(tmp_path, "6", pipeline_complete=True)
    assert resolve_max_generated_chapter_num(tmp_path, complete) == 6


def test_writing_context_bounded_lookback(tmp_path: Path) -> None:
    for n in range(1, 121):
        _write_chapter(tmp_path, n, body_len=120)
    ctx = gather_recent_writing_context(tmp_path, before_chapter=120, max_chapters=3)
    assert len(ctx["recent_chapters"]) == 3
    nums = [int(c["chapter_id"]) for c in ctx["recent_chapters"]]
    assert nums == [119, 118, 117]


def test_load_highwater_empty(tmp_path: Path) -> None:
    assert load_highwater(tmp_path) == {}