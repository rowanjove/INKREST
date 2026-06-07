"""E2E fixture seed API (disabled unless E2E_FIXTURES=1)."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

import web.context as web_context
import web.server as web_server
from web.server import app as web_app


def test_e2e_seed_disabled_by_default() -> None:
    original = os.environ.pop("E2E_FIXTURES", None)
    try:
        # Re-import would be needed for router mount; endpoint may be absent.
        # When disabled at startup, route is not registered — use 404 on path.
        client = TestClient(web_app)
        res = client.post("/api/e2e/seed-maintenance-scenario")
        assert res.status_code in (404, 405)
    finally:
        if original is not None:
            os.environ["E2E_FIXTURES"] = original


def test_e2e_seed_module_builds_pending_queue(tmp_path: Path) -> None:
    from web.e2e_seed import seed_maintenance_scenario
    from web.project_manager import ProjectManager
    from novel_agent.services.pipeline_pending import summarize_pipeline_pending

    pm = ProjectManager(tmp_path)
    payload = seed_maintenance_scenario(pm)
    root = tmp_path / "projects" / payload["project_id"]
    pending = summarize_pipeline_pending(root)
    assert payload["pending_total"] == pending["pending_total"]
    assert pending["pending_total"] >= 2
    assert payload["pause_reason"] == "quality_blocked"
    assert payload["pending_chapter_ids"] == ["002", "003"]