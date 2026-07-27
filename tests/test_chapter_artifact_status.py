import json
from pathlib import Path

from novel_agent.services.chapter_artifact_status import (
    build_chapter_artifact_status,
    summarize_chapter_artifact_status,
)


def _chapter_dir(root: Path, chapter_id: str = "001") -> Path:
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    (chapter_dir / "reports").mkdir(parents=True, exist_ok=True)
    return chapter_dir


def test_blocked_gate_marks_state_update_stale(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path)
    (chapter_dir / "chapter_final.txt").write_text("正文。", encoding="utf-8")
    (chapter_dir / "state_update.json").write_text(
        json.dumps({"events": [{"id": "e1"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    rows = build_chapter_artifact_status(
        chapter_dir,
        unified_gate={"blocked": True, "resumable_from": "audit"},
    )
    by_key = {row["key"]: row for row in rows}

    assert by_key["final"]["status"] == "authoritative"
    assert by_key["state_update"]["status"] == "stale"
    assert by_key["state_update"]["resumable_from"] == "audit"


def test_artifact_summary_returns_counts_keys_and_repair_steps(tmp_path: Path) -> None:
    chapter_dir = _chapter_dir(tmp_path)
    (chapter_dir / "chapter_final.txt").write_text("正文。", encoding="utf-8")
    (chapter_dir / "state_update.json").write_text(
        json.dumps({"events": [{"id": "e1"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    rows = build_chapter_artifact_status(
        chapter_dir,
        unified_gate={"blocked": True, "resumable_from": "audit"},
    )
    summary = summarize_chapter_artifact_status(rows)

    assert summary["total"] == len(rows)
    assert summary["missing_count"] > 0
    assert summary["stale_count"] > 0
    assert "plan" in summary["missing_keys"]
    assert "state_update" in summary["stale_keys"]
    assert any("resume" in step["action"] for step in summary["repair_steps"])
