"""Each scale tier at its design ceiling: policy, replenish, and hot-path bounds."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from novel_agent.control.runtime_policy import resolve_runtime_policy
from novel_agent.control.scale_profile import SCALE_PROFILES
from novel_agent.services.chapter_highwater import resolve_max_generated_chapter_num
from novel_agent.services.rolling_planner import (
    max_generated_chapter_num,
    replenish_rolling_window,
)
from novel_agent.services.writing_context import gather_recent_writing_context


TIER_CEILING = {
    "micro": 3,
    "short": 20,
    "medium": 100,
    "long": 500,
    "epic": 3000,
    "infinite": 999999,
}


def _outline(root: Path, scale: str) -> None:
    prof = dict(SCALE_PROFILES[scale])
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps({"scale_profile": prof}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_chapter(root: Path, num: int) -> None:
    from novel_agent.services.rolling_planner import format_chapter_id

    cid = format_chapter_id(num)
    d = root / "workspace" / "chapters" / f"chapter_{cid}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chapter_final.txt").write_text("正文" * 80, encoding="utf-8")


@pytest.mark.parametrize("scale", list(TIER_CEILING.keys()))
def test_runtime_policy_matches_tier_max(scale: str, tmp_path: Path) -> None:
    _outline(tmp_path, scale)
    ceiling = TIER_CEILING[scale]
    outline_path = tmp_path / "workspace" / "outline.json"
    data = json.loads(outline_path.read_text(encoding="utf-8"))
    data["target_chapters"] = ceiling
    outline_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    policy = resolve_runtime_policy(tmp_path)
    assert policy.target_chapters == ceiling
    assert policy.planning_mode == SCALE_PROFILES[scale]["planning_mode"]


@pytest.mark.parametrize(
    "scale,expect_rolling",
    [
        ("micro", False),
        ("short", False),
        ("medium", True),
        ("long", True),
        ("epic", True),
        ("infinite", True),
    ],
)
def test_rolling_planner_only_medium_plus(
    scale: str, expect_rolling: bool, tmp_path: Path
) -> None:
    _outline(tmp_path, scale)
    mode = SCALE_PROFILES[scale]["planning_mode"]
    uses_rolling = mode in (
        "rolling_window",
        "dynamic_volume",
        "fractal_dynamic_volume",
        "container_episode",
    )
    assert uses_rolling is expect_rolling


@pytest.mark.asyncio
@pytest.mark.parametrize("scale", ["medium", "long", "epic"])
async def test_replenish_stops_at_tier_ceiling(scale: str, tmp_path: Path) -> None:
    ceiling = TIER_CEILING[scale]
    _outline(tmp_path, scale)
    outline_path = tmp_path / "workspace" / "outline.json"
    data = json.loads(outline_path.read_text(encoding="utf-8"))
    data["target_chapters"] = ceiling
    outline_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for n in range(max(1, ceiling - 5), ceiling + 1):
        _write_chapter(tmp_path, n)
    from novel_agent.services.chapter_highwater import bump_chapter_written

    bump_chapter_written(
        tmp_path, str(ceiling), pipeline_complete=True
    )
    orch = MagicMock()
    orch.root_dir = tmp_path
    orch._chapter_pipeline_complete = lambda cid: True
    added = await replenish_rolling_window(orch)
    assert added == 0


def test_epic_hot_path_no_full_scan_with_cache(tmp_path: Path) -> None:
    _outline(tmp_path, "epic")
    for n in [1, 100, 500]:
        _write_chapter(tmp_path, n)
    from novel_agent.services.chapter_highwater import bump_chapter_written

    bump_chapter_written(tmp_path, "500", pipeline_complete=True)

    def complete(cid: str) -> bool:
        return int(cid) <= 500

    assert max_generated_chapter_num(tmp_path, complete) == 500
    ctx = gather_recent_writing_context(tmp_path, before_chapter=501, max_chapters=5)
    assert len(ctx["recent_chapters"]) <= 5


def test_micro_tier_max_three_chapters_policy(tmp_path: Path) -> None:
    _outline(tmp_path, "micro")
    policy = resolve_runtime_policy(tmp_path)
    assert policy.target_chapters == 3
    assert policy.vector_enabled is False


def test_epic_tier_compression_and_hnsw_flags(tmp_path: Path) -> None:
    prof = SCALE_PROFILES["epic"]
    assert prof.get("compress_hot_every") == 10
    assert prof.get("hnsw_rebuild_every") == 50
    assert prof["max_chapters"] == 3000


@pytest.mark.asyncio
async def test_micro_max_chapters_no_replenish_beyond_three(tmp_path: Path) -> None:
    _outline(tmp_path, "micro")
    outline_path = tmp_path / "workspace" / "outline.json"
    data = json.loads(outline_path.read_text(encoding="utf-8"))
    data["target_chapters"] = 3
    outline_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for n in range(1, 4):
        _write_chapter(tmp_path, n)
    from novel_agent.services.chapter_highwater import bump_chapter_written

    bump_chapter_written(tmp_path, "003", pipeline_complete=True)
    orch = MagicMock()
    orch.root_dir = tmp_path
    orch._chapter_pipeline_complete = lambda cid: True
    assert await replenish_rolling_window(orch) == 0