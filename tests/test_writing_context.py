"""Recent writing context for chapter split."""

import json
from pathlib import Path

from novel_agent.services.writing_context import gather_recent_writing_context


def test_gather_recent_context(tmp_path: Path) -> None:
    root = tmp_path
    ch_dir = root / "workspace" / "chapters" / "chapter_002"
    ch_dir.mkdir(parents=True)
    (ch_dir / "chapter_final.txt").write_text("x" * 200, encoding="utf-8")
    (ch_dir / "chapter_summary.md").write_text("第二章摘要", encoding="utf-8")
    arc = {
        "arc_id": "A01",
        "chapters": [{"chapter_id": "002", "output_state": "主角抵达旧城"}],
    }
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps(arc, ensure_ascii=False), encoding="utf-8"
    )
    ctx = gather_recent_writing_context(root, before_chapter=3)
    assert len(ctx["recent_chapters"]) == 1
    assert ctx["recent_chapters"][0]["chapter_id"] == "002"