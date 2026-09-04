import pytest
from pathlib import Path
from novel_agent.services.quality_review import build_quality_review_queue


def test_quality_review_queue_pagination(tmp_path: Path):
    chapters_dir = tmp_path / "workspace" / "chapters"
    chapters_dir.mkdir(parents=True)

    for i in range(1, 11):
        cid = f"{i:03d}"
        cdir = chapters_dir / f"chapter_{cid}"
        cdir.mkdir()
        report = {
            "overall_pass": False,
            "overall_score": 75 + (i % 20),
            "guard_summary": {
                "overall_status": "FAIL",
                "blocked_by": ["style" if i % 2 == 0 else "layout"],
            },
            "checks": {
                "style": {"pass": i % 2 != 0, "score": 70, "level": "error"},
                "layout": {"pass": i % 2 == 0, "score": 72, "level": "warning"},
            },
        }
        rdir = cdir / "reports"
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / "quality.json").write_text(
            __import__("json").dumps(report), encoding="utf-8"
        )

    # Test unpaginated fetch
    full = build_quality_review_queue(tmp_path)
    assert len(full["items"]) == 10
    assert full["total"] == 10
    assert full["has_more"] is False

    # Test paginated fetch page 1 (limit 3)
    p1 = build_quality_review_queue(tmp_path, limit=3)
    assert len(p1["items"]) == 3
    assert p1["total"] == 10
    assert p1["has_more"] is True
    c1 = p1["next_cursor"]
    assert c1 is not None

    # Test page 2 (cursor c1, limit 3)
    p2 = build_quality_review_queue(tmp_path, cursor=c1, limit=3)
    assert len(p2["items"]) == 3
    assert p2["has_more"] is True
    assert p2["items"][0]["chapter_id"] != p1["items"][0]["chapter_id"]

    # Test severity filter
    err_only = build_quality_review_queue(tmp_path, severity_filter="error")
    assert all(it["severity"] == "error" for it in err_only["items"])
