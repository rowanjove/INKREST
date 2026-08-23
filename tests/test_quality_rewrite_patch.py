"""Issue-driven quality rewrite prompt and delta metadata tests."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_agent.quality.quality_rewrite import (
    analyse_content_delta,
    build_issue_driven_patch_prompt,
)
from novel_agent.quality.render_contract import build_scene_render_contract


def _report():
    return {
        "guard_summary": {"blocked_by": ["style"]},
        "checks": {
            "style": {
                "pass": False,
                "level": "warning",
                "details": ["出现模板化氛围描写"],
                "findings": [
                    {
                        "id": "style:4:8",
                        "rule_id": "generic_atmosphere",
                        "description": "模板化氛围描写",
                        "text": "空气凝固",
                        "start": 4,
                        "end": 8,
                    }
                ],
            },
            # Report-only checks must not silently become auto-rewrite spans.
            "event_consistency": {
                "pass": True,
                "findings": [{"type": "unanchored_turn", "start": 0, "end": 2, "text": "突然"}],
            },
        },
    }


def test_issue_driven_prompt_contains_only_failing_evidence_span():
    prompt = build_issue_driven_patch_prompt(_report(), "甲乙丙丁空气凝固后继续前进。")

    assert "issue-driven patch" in prompt
    assert "原文证据：空气凝固" in prompt
    assert "generic_atmosphere" in prompt
    assert "unanchored_turn" not in prompt
    assert "只输出修订后的完整正文" in prompt


def test_content_delta_reports_operations_and_preserved_facts():
    contract = build_scene_render_contract(
        "林澈拿着铜钥匙走进旧城区。",
        chapter_id="002",
        scene={"scene_id": "002-01", "must_include": ["拿到铜钥匙"]},
        plan={"immutable_facts": ["铜钥匙仍由林澈保管"]},
    )
    delta = analyse_content_delta(
        "林澈拿着铜钥匙走进旧城区。",
        "林澈握紧铜钥匙，走进旧城区。",
        contract,
    )

    assert delta["changed"] is True
    assert delta["operation_count"] >= 1
    assert delta["content_lock_digest"]
    assert delta["preserved_facts"][0]["preserved"] is False
    assert delta["operations"]


@pytest.mark.asyncio
async def test_quality_rewrite_persists_patch_metadata(tmp_path):
    from novel_agent.quality.quality_rewrite import attempt_quality_rewrite

    class Editor:
        async def arun(self, _prompt):
            return "甲乙丙丁空气凝固后继续前进。"

    class Orchestrator:
        style_editor = Editor()

    original = "甲乙丙丁空气凝固后继续前进。" * 8
    path = tmp_path / "quality_rewrite_candidate.txt"
    contract = build_scene_render_contract(
        original,
        chapter_id="002",
        scene={"scene_id": "002-01", "must_include": ["继续前进"]},
    )
    revised = await attempt_quality_rewrite(
        Orchestrator(),
        "002",
        original,
        _report(),
        candidate_path=path,
        contract=contract.to_dict(),
    )

    assert revised.startswith("甲乙丙丁")
    metadata = json.loads((tmp_path / "quality_rewrite_candidate.json").read_text(encoding="utf-8"))
    assert metadata["patch_mode"] == "issue_driven"
    assert "content_delta" in metadata
    assert "preserved_facts" in metadata
