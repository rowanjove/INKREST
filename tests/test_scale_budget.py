"""Scale hard max, project soft target, and per-run chapter budget are distinct."""

from __future__ import annotations

import pytest

from novel_agent.control.scale_profile import (
    DEFAULT_RUN_CHAPTER_BUDGET,
    MAX_RUN_CHAPTER_BUDGET,
    ScaleLimitError,
    clamp_run_chapter_budget,
    resolve_scale_budget,
    resolve_scale_profile,
    validate_scale_target,
)


def test_epic_hard_max_stays_3000() -> None:
    budget = resolve_scale_budget(scale="epic", target_chapters=800)
    assert budget.scale == "epic"
    assert budget.scale_hard_max == 3000
    assert budget.project_soft_target == 800
    assert budget.run_chapter_budget <= MAX_RUN_CHAPTER_BUDGET
    assert budget.run_chapter_budget >= 1


def test_target_above_3000_without_scale_resolves_to_infinite() -> None:
    profile = resolve_scale_profile(target_chapters=5000)
    assert profile["scale"] == "infinite"
    assert profile["scale_hard_max"] == 999999
    assert profile["project_soft_target"] == 5000
    assert profile["run_chapter_budget"] == DEFAULT_RUN_CHAPTER_BUDGET


def test_epic_rejects_3001_with_upgrade_hint() -> None:
    with pytest.raises(ScaleLimitError) as exc:
        validate_scale_target(scale="epic", target_chapters=3001)
    err = exc.value
    assert err.recommended_scale == "infinite"
    assert "3000" in str(err)
    assert "无限" in str(err) or "infinite" in str(err).lower()


def test_infinite_accepts_5000_soft_target() -> None:
    budget = validate_scale_target(scale="infinite", target_chapters=5000)
    assert budget.scale == "infinite"
    assert budget.project_soft_target == 5000
    assert budget.scale_hard_max == 999999


def test_run_budget_rejects_5000_generation_tasks() -> None:
    with pytest.raises(ScaleLimitError) as exc:
        clamp_run_chapter_budget(5000, scale="infinite")
    assert "预算" in str(exc.value) or "run" in str(exc.value).lower()


def test_run_budget_zero_uses_default() -> None:
    assert clamp_run_chapter_budget(0, scale="long") == DEFAULT_RUN_CHAPTER_BUDGET


def test_profile_exposes_three_limits_without_collapsing_max_chapters() -> None:
    profile = resolve_scale_profile(target_chapters=200, scale="long")
    assert profile["max_chapters"] == 500
    assert profile["scale_hard_max"] == 500
    assert profile["project_soft_target"] == 200
    assert "run_chapter_budget" in profile
    assert profile["scale_hard_max"] != profile["project_soft_target"]
