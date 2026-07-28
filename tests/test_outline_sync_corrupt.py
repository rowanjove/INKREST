"""outline.json corruption must block continue."""

from pathlib import Path

from novel_agent.services.outline_sync import check_arc_queue_stale
from tests.test_full_chain_chaos import _seed_ready
from novel_agent.services.novel_run_guard import validate_novel_continue


def test_outline_read_error_is_stale(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    (tmp_path / "workspace" / "outline.json").write_text("{", encoding="utf-8")
    stale = check_arc_queue_stale(tmp_path)
    assert stale["stale"] is True
    assert stale["reason"] == "outline_read_error"
    ok, msg = validate_novel_continue(tmp_path)
    assert not ok
    assert "outline.json" in msg