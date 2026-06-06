"""Golden fixtures: stable fingerprints and skip decisions for pipeline shortcuts."""

import json
from pathlib import Path

from novel_agent.control.chapter_brief import brief_fingerprint, should_skip_chapter_planner_expand
from novel_agent.control.runtime_policy import (
    PIPELINE_TIER_BY_SCALE,
    resolve_pipeline_tier,
)


FIXTURES = Path(__file__).parent / "fixtures" / "golden_pipeline"


def test_golden_brief_fingerprint_regression() -> None:
    brief = json.loads((FIXTURES / "brief_rich.json").read_text(encoding="utf-8"))
    fp1 = brief_fingerprint(brief)
    fp2 = brief_fingerprint(dict(brief))
    assert fp1 == fp2
    assert len(fp1) == 16


def test_golden_brief_skip_with_cached_plan(tmp_path: Path) -> None:
    brief = json.loads((FIXTURES / "brief_rich.json").read_text(encoding="utf-8"))
    root = tmp_path
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{brief['chapter_id']}"
    chapter_dir.mkdir(parents=True)
    expanded = {
        "detailed_synopsis": brief["detailed_synopsis"],
        "chapter_goal": brief["chapter_goal"],
    }
    (chapter_dir / "expanded_plan.json").write_text(
        json.dumps(expanded, ensure_ascii=False), encoding="utf-8"
    )
    (chapter_dir / "expanded_plan.meta.json").write_text(
        json.dumps({"brief_fp": brief_fingerprint(brief)}, ensure_ascii=False),
        encoding="utf-8",
    )
    skip, reason, _ = should_skip_chapter_planner_expand(root, brief["chapter_id"], brief)
    assert skip is True
    assert reason == "cached_expand"


def test_pipeline_tier_by_scale_defaults(tmp_path: Path) -> None:
    assert PIPELINE_TIER_BY_SCALE["micro"] == "economy"
    assert resolve_pipeline_tier(tmp_path, "long") == "standard"