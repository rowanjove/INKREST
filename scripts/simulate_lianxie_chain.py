#!/usr/bin/env python3
"""Simulate UI 连写链路: refresh → readiness → ensure-queue → continue (dry_run)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REFRESH_PATHS = (
    "/api/assets",
    "/api/chapters/count?sync=true",
    "/api/outline",
    "/api/models",
    "/api/config",
    "/api/config/embedding/status",
    "/api/novel/arc-progress",
    "/api/novel/batch-status",
    "/api/system/readiness",
)


def seed_production_like_project(root: Path, *, with_arcs: bool = True) -> None:
    """Match ensure_writing_standards_assets + typical user project layout."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: sim-daily\n  reasoning_model_id: sim-daily\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    (root / "config" / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "sim-daily": {
                        "name": "Sim Daily",
                        "provider": "openai",
                        "model": "gpt-test",
                    }
                },
                "slots": {"daily": "sim-daily", "reasoning": "sim-daily", "backup": []},
                "slots_version": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "world_bible.md").write_text("# 世界观\n" + "设定" * 30, encoding="utf-8")
    (assets / "style_guide.md").write_text("# 文风\n" + "风格" * 30, encoding="utf-8")
    (assets / "rules.yaml").write_text("rules:\n  version: 1\n", encoding="utf-8")
    (assets / "sensitive_words.txt").write_text("# seed\n测试\n", encoding="utf-8")
    outline = {
        "chosen_title": "链路模拟书",
        "target_chapters": 10,
        "scale_profile": {"scale": "medium", "max_chapters": 10},
        "macro_outline": [{"arc_id": "A01", "chapters": "1-5", "goal": "主线"}],
    }
    ws = root / "workspace"
    ws.mkdir(exist_ok=True)
    (ws / "outline.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
    if with_arcs:
        chapters = [{"chapter_id": f"{i:03d}", "goal": f"g{i}"} for i in range(1, 6)]
        (ws / "arc_A01.json").write_text(
            json.dumps({"arc_id": "A01", "chapters": chapters}, ensure_ascii=False),
            encoding="utf-8",
        )
        from novel_agent.services.outline_sync import mark_arcs_synced_with_outline

        mark_arcs_synced_with_outline(root)


def _step(name: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "BLOCK"
    line = f"[{mark}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


def run_simulation() -> int:
    import web.context as web_context
    import web.server as web_server
    from fastapi.testclient import TestClient
    from novel_agent.services.novel_run_guard import build_readiness_report, validate_novel_continue

    tmp = Path(tempfile.mkdtemp(prefix="lianxie-sim-"))
    print(f"Project root: {tmp}\n")

    seed_production_like_project(tmp, with_arcs=True)

    report = build_readiness_report(tmp)
    ok_report = bool(report.get("ok"))
    pending = report.get("pending") or []
    _step(
        "novel_run_guard.build_readiness_report",
        ok_report,
        "pending=" + ", ".join(p["label"] for p in pending) if pending else "none",
    )

    ok_val, val_detail = validate_novel_continue(tmp)
    _step("novel_run_guard.validate_novel_continue", ok_val, val_detail)

    original_base = web_server.BASE_DIR
    original_active = web_server._active_project_id
    web_context._task_manager = None
    try:
        web_server.BASE_DIR = tmp
        web_server._active_project_id = None
        from web.app import app

        client = TestClient(app)

        blocked = False
        for path in REFRESH_PATHS:
            r = client.get(path)
            if not _step(f"GET {path}", r.status_code == 200, r.text[:200]):
                blocked = True

        r = client.get("/api/novel/readiness")
        data = r.json() if r.status_code == 200 else {}
        if not _step(
            "GET /api/novel/readiness",
            r.status_code == 200 and data.get("ok"),
            json.dumps(data.get("pending") or [], ensure_ascii=False)[:300],
        ):
            blocked = True

        with patch(
            "novel_agent.services.rolling_planner.prepare_queue_for_run",
            new_callable=AsyncMock,
            return_value={"arcs_created": 0, "briefs_added": 0, "pending_briefs": 5},
        ):
            q = client.post("/api/novel/ensure-queue")
        if not _step("POST /api/novel/ensure-queue", q.status_code == 200, q.text[:200]):
            blocked = True

        body = {
            "resume": True,
            "max_chapters": 2,
            "dry_run": True,
            "autopilot": True,
            "full_book": True,
        }
        c = client.post("/api/novel/continue", json=body)
        if not _step("POST /api/novel/continue", c.status_code == 200, c.text[:200]):
            blocked = True
        else:
            task_id = c.json().get("task_id")
            _step("continue.task_id", bool(task_id), task_id or "")
            t = client.get(f"/api/chapters/tasks/{task_id}")
            _step(
                "GET task status",
                t.status_code == 200,
                (t.json().get("status") or "") + " " + str(t.json().get("error") or "")[:120],
            )

        # Cold path: no arcs, mock managing editor
        web_context._task_manager = None
        seed_production_like_project(tmp, with_arcs=False)
        for p in list(tmp.glob("workspace/arc_*.json")):
            p.unlink()
        client2 = TestClient(app)
        fake_arc = {
            "arc_id": "A01",
            "chapters": [{"chapter_id": "001", "goal": "mock"}],
        }
        with patch(
            "novel_agent.agents.managing_editor.ManagingEditorAgent.asplit_chapters",
            new_callable=AsyncMock,
            return_value=fake_arc,
        ), patch(
            "novel_agent.services.rolling_planner.prepare_queue_for_run",
            new_callable=AsyncMock,
            return_value={"arcs_created": 1, "briefs_added": 1, "pending_briefs": 1},
        ):
            q2 = client2.post("/api/novel/ensure-queue")
        (tmp / "workspace" / "arc_A01.json").write_text(
            json.dumps(fake_arc, ensure_ascii=False), encoding="utf-8"
        )
        from novel_agent.services.outline_sync import mark_arcs_synced_with_outline

        mark_arcs_synced_with_outline(tmp)
        if not _step("cold ensure-queue (mock split)", q2.status_code == 200, q2.text[:160]):
            blocked = True
        ok2, d2 = validate_novel_continue(tmp)
        if not _step("cold validate_novel_continue", ok2, d2):
            blocked = True

        print()
        if blocked:
            print("RESULT: 链路存在阻塞点（见上方 BLOCK）。")
            return 1
        print("RESULT: 链路模拟全部通过（dry_run，无真实 LLM）。")
        return 0
    finally:
        web_context._task_manager = None
        web_server.BASE_DIR = original_base
        web_server._active_project_id = original_active


if __name__ == "__main__":
    raise SystemExit(run_simulation())