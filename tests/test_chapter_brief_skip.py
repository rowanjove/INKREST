"""Tests for chapter_planner expand skip when brief is rich."""

import json
from pathlib import Path

from novel_agent.control.chapter_brief import brief_fingerprint, should_skip_chapter_planner_expand


def test_skip_when_synopsis_matches_expanded_plan(tmp_path: Path) -> None:
    root = tmp_path
    chapter_dir = root / "workspace" / "chapters" / "chapter_007"
    chapter_dir.mkdir(parents=True)
    synopsis = "主角在雨夜抵达旧城，发现门牌被换掉，线索指向失踪的师妹。" * 2
    brief = {
        "chapter_id": "007",
        "detailed_synopsis": synopsis,
        "chapter_goal": "推进调查",
    }
    expanded = {"detailed_synopsis": synopsis, "chapter_goal": "推进调查"}
    (chapter_dir / "expanded_plan.json").write_text(
        json.dumps(expanded, ensure_ascii=False), encoding="utf-8"
    )
    (chapter_dir / "expanded_plan.meta.json").write_text(
        json.dumps({"brief_fp": brief_fingerprint(brief)}, ensure_ascii=False),
        encoding="utf-8",
    )

    skip, reason, cached = should_skip_chapter_planner_expand(root, "007", brief)
    assert skip is True
    assert reason in ("synopsis_match", "cached_expand")
    assert cached.get("detailed_synopsis") == synopsis


def test_no_skip_when_brief_not_rich(tmp_path: Path) -> None:
    root = tmp_path
    brief = {"chapter_id": "001", "chapter_goal": "短目标"}
    skip, reason, _ = should_skip_chapter_planner_expand(root, "001", brief)
    assert skip is False
    assert reason == "brief_not_rich"