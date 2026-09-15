"""Unit tests for seed_demo_project generator."""

import sqlite3
from pathlib import Path
from novel_agent.demo.demo_book import seed_demo_project


def test_seed_demo_project(tmp_path: Path):
    target = tmp_path / "demo_space"
    out = seed_demo_project(target)
    assert out.is_dir()

    meta_file = target / "meta.json"
    assert meta_file.is_file()

    db_file = target / "project.db"
    assert db_file.is_file()

    conn = sqlite3.connect(db_file)
    try:
        # Check metadata
        val = conn.execute("select value from app_metadata where key='project_name'").fetchone()[0]
        assert val == "星渊回响"

        # Check chapters seeded
        rows = conn.execute("select title, volume_name from documents order by chapter_index").fetchall()
        assert len(rows) == 3
        assert rows[0][0] == "第1章 寂夜微光"
        assert rows[0][1] == "第一卷 寂静之海"
    finally:
        conn.close()
