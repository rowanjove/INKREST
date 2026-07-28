"""Tests for outline vs arc queue staleness detection."""

import json
from pathlib import Path

from novel_agent.services.outline_sync import (
    check_arc_queue_stale,
    macro_outline_fingerprint,
    mark_arcs_synced_with_outline,
    record_outline_saved,
)


def test_macro_fingerprint_stable(tmp_path: Path) -> None:
    macro = [{"arc_id": "a1", "name": "卷一", "chapters": [{"chapter_id": "001"}]}]
    assert macro_outline_fingerprint(macro) == macro_outline_fingerprint(macro)


def test_stale_after_outline_change(tmp_path: Path) -> None:
    root = tmp_path
    ws = root / "workspace"
    ws.mkdir(parents=True)
    outline_v1 = {
        "macro_outline": [{"arc_id": "a1", "name": "卷一", "chapters": [{"chapter_id": "001"}]}],
    }
    (ws / "outline.json").write_text(json.dumps(outline_v1, ensure_ascii=False), encoding="utf-8")
    (ws / "arc_001.json").write_text(
        json.dumps(
            {"arc_id": "a1", "arc_name": "卷一", "chapters": [{"chapter_id": "001", "goal": "g"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    record_outline_saved(root, outline_v1)

    outline_v2 = {
        "macro_outline": [{"arc_id": "a1", "name": "卷一改", "chapters": [{"chapter_id": "001"}]}],
    }
    (ws / "outline.json").write_text(json.dumps(outline_v2, ensure_ascii=False), encoding="utf-8")

    stale = check_arc_queue_stale(root)
    assert stale.get("stale") is True
    assert stale.get("reason") == "outline_changed"

    mark_arcs_synced_with_outline(root)
    stale2 = check_arc_queue_stale(root)
    assert stale2.get("stale") is False