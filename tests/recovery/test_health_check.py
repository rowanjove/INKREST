"""Unit tests for ProjectHealthChecker and auto-repair."""

import sqlite3
from pathlib import Path
from novel_agent.recovery.health_check import ProjectHealthChecker, HealthStatus


def test_health_check_and_auto_repair(tmp_path: Path):
    proj_dir = tmp_path / "test_novel"
    proj_dir.mkdir()
    db_file = proj_dir / "project.db"

    # 1. Initially missing DB
    checker = ProjectHealthChecker(proj_dir)
    report = checker.run_check()
    assert report.overall_status == HealthStatus.CRITICAL

    # 2. Valid SQLite DB but missing app_metadata table
    conn = sqlite3.connect(db_file)
    try:
        conn.execute("create table documents (id text primary key, title text)")
        conn.execute("insert into documents values ('d1', '第一章')")
        conn.commit()
    finally:
        conn.close()

    report2 = checker.run_check()
    assert report2.overall_status == HealthStatus.WARNING
    assert report2.auto_repairable_count > 0

    # 3. Perform auto-repair
    repair_result = checker.auto_repair()
    assert repair_result["success"] is True

    # 4. Check again: now healthy
    report3 = checker.run_check()
    assert report3.overall_status == HealthStatus.HEALTHY
