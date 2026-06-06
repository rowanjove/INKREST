"""Agent bridge (CLI / snapshot / MCP helpers) smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_resolve_project_root_rejects_traversal(tmp_path):
    (tmp_path / "projects").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("leak", encoding="utf-8")

    from novel_agent.integrations.agent_bridge import resolve_project_root, set_default_base_dir

    set_default_base_dir(tmp_path)
    with pytest.raises((ValueError, FileNotFoundError)):
        resolve_project_root(tmp_path, "..\\outside")


def test_list_projects_structure(tmp_path):
    reg = {
        "active_id": "p1",
        "projects": {"p1": {"name": "Test Novel", "target_chapters": 10}},
    }
    (tmp_path / "projects.json").write_text(json.dumps(reg), encoding="utf-8")
    (tmp_path / "projects" / "p1").mkdir(parents=True)
    (tmp_path / "projects" / "p1" / "workspace").mkdir(parents=True)

    from novel_agent.integrations.agent_bridge import list_projects, set_default_base_dir

    set_default_base_dir(tmp_path)
    data = list_projects(tmp_path)
    assert data["active_id"] == "p1"
    assert len(data["projects"]) == 1
    assert data["projects"][0]["id"] == "p1"


def test_build_agent_snapshot_minimal(tmp_path):
    proj = tmp_path / "projects" / "p1"
    ws = proj / "workspace"
    ws.mkdir(parents=True)
    (ws / "outline.json").write_text(
        json.dumps({"chosen_title": "测试书名"}),
        encoding="utf-8",
    )
    reports = proj / "workspace" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "novel_batch_progress.json").write_text(
        json.dumps({"status": "idle", "fail_streak": 0}),
        encoding="utf-8",
    )

    from novel_agent.integrations.agent_bridge import build_agent_snapshot

    snap = build_agent_snapshot(proj, project_id="p1")
    assert snap["project_id"] == "p1"
    assert snap["outline_title"] == "测试书名"
    assert "progress_summary" in snap
    assert "readiness" in snap


def test_cli_agent_projects(tmp_path):
    (tmp_path / "projects.json").write_text(
        json.dumps({"active_id": "p1", "projects": {"p1": {"name": "A"}}}),
        encoding="utf-8",
    )
    (tmp_path / "projects" / "p1").mkdir(parents=True)

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "cli.py"),
            "agent",
            "projects",
            "--novel-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["active_id"] == "p1"


def test_agent_api_snapshot_route(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "p1"
    ws = proj / "workspace"
    ws.mkdir(parents=True)
    (ws / "outline.json").write_text(json.dumps({"chosen_title": "X"}), encoding="utf-8")
    reports = ws / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "novel_batch_progress.json").write_text(
        json.dumps({"status": "paused", "pause_reason": "test"}),
        encoding="utf-8",
    )

    import web.context as ctx

    monkeypatch.setattr(ctx, "BASE_DIR", tmp_path)
    monkeypatch.setattr(ctx, "_active_project_id", "p1")

    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    resp = client.get("/api/agent/snapshot")
    assert resp.status_code == 200
    body = resp.json()
    assert body["outline_title"] == "X"
    assert body["batch"]["paused"] is True


def test_agent_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("web.context.BASE_DIR", tmp_path)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)

    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    get_resp = client.get("/api/agent/settings")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert "integration" in body
    assert body["settings"]["mcp_mode"] == "auto"

    put_resp = client.put(
        "/api/agent/settings",
        json={"mcp_mode": "offline", "api_url_override": "http://127.0.0.1:9000"},
    )
    assert put_resp.status_code == 200
    saved = put_resp.json()["settings"]
    assert saved["mcp_mode"] == "offline"
    assert saved["api_url_override"] == "http://127.0.0.1:9000"
    assert put_resp.json()["integration"]["env_vars"]["NOVEL_AGENT_API_URL"] == "http://127.0.0.1:9000"