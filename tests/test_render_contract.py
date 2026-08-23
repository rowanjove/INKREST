from __future__ import annotations

import json

import pytest

from novel_agent.quality.quality_rewrite import attempt_quality_rewrite
from novel_agent.quality.render_contract import (
    build_content_lock,
    build_render_contract,
    build_scene_render_contract,
    persist_render_contract,
    validate_render_candidate,
)


def test_render_contract_accepts_a_comparable_prose_candidate():
    original = ("雨水敲在旧窗上，屋里只剩一盏灯。\n\n" * 8).strip()
    candidate = ("雨声落在旧窗上，屋内只留一盏灯。\n\n" * 8).strip()

    result = validate_render_candidate(original, candidate)

    assert result["status"] == "accepted"
    assert result["pass"] is True
    assert result["blocking"] is False
    assert result["metrics"]["length_ratio"] > 0.55


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        ("", "empty_candidate"),
        ("```\n正文\n```", "markdown_code_fence"),
        ("# 修订稿\n\n正文内容。", "markdown_heading"),
        ("- 第一条\n- 第二条\n- 第三条", "markdown_list"),
        ('{"text": "正文"}', "json_payload"),
    ],
)
def test_render_contract_rejects_format_pollution(candidate: str, reason: str):
    original = "这是原始正文。" * 20

    result = validate_render_candidate(original, candidate)

    assert result["status"] == "rejected"
    assert result["blocking"] is True
    assert reason in result["reasons"]


def test_render_contract_rejects_abnormally_short_or_long_candidates():
    original = "这是原始正文，包含足够的篇幅用于检测改写边界。" * 20

    short_result = validate_render_candidate(original, "短稿。")
    long_result = validate_render_candidate(original, original * 2)

    assert "candidate_too_short" in short_result["reasons"]
    assert "candidate_too_long" in long_result["reasons"]


def test_render_contract_marks_unchanged_candidate_without_blocking():
    original = "保留原文，不需要重复改写。" * 10

    result = validate_render_candidate(original, original)

    assert result["status"] == "unchanged"
    assert result["pass"] is True
    assert result["blocking"] is False


class _Editor:
    def __init__(self, output: str):
        self.output = output

    async def arun(self, _prompt: str) -> str:
        return self.output


class _Orchestrator:
    def __init__(self, output: str):
        self.style_editor = _Editor(output)


@pytest.mark.asyncio
async def test_quality_rewrite_keeps_rejected_candidate_out_of_final_text(tmp_path):
    original = "这是需要保留的正文，长度足够用于质量返工安全校验。" * 20
    orchestrator = _Orchestrator("短稿。")
    candidate_path = tmp_path / "quality_rewrite_candidate.txt"

    revised = await attempt_quality_rewrite(
        orchestrator,
        "chapter-1",
        original,
        {"guard_summary": {"blocked_by": ["style"]}},
        candidate_path=candidate_path,
    )

    assert revised == original
    assert candidate_path.read_text(encoding="utf-8") == "短稿。"
    metadata = json.loads((tmp_path / "quality_rewrite_candidate.json").read_text(encoding="utf-8"))
    assert metadata["accepted"] is False
    assert "candidate_too_short" in metadata["reasons"]


@pytest.mark.asyncio
async def test_quality_rewrite_returns_valid_candidate_and_records_it(tmp_path):
    original = ("这是需要保留语义的正文，编辑只做局部调整。\n\n" * 12).strip()
    candidate = ("这是需要保留语义的正文，编辑完成局部调整。\n\n" * 12).strip()
    orchestrator = _Orchestrator(candidate)
    candidate_path = tmp_path / "quality_rewrite_candidate.txt"

    revised = await attempt_quality_rewrite(
        orchestrator,
        "chapter-2",
        original,
        {"guard_summary": {"blocked_by": ["style"]}},
        candidate_path=candidate_path,
    )

    assert revised == candidate
    metadata = json.loads((tmp_path / "quality_rewrite_candidate.json").read_text(encoding="utf-8"))
    assert metadata["accepted"] is True
    assert metadata["status"] == "accepted"


def test_render_contract_can_be_serialised_for_report_storage():
    contract = build_render_contract("一段正文。" * 20)

    assert contract.to_dict()["min_chars"] > 0
    assert contract.to_dict()["max_chars"] >= contract.to_dict()["min_chars"]


def test_content_lock_binds_scene_facts_and_source_versions():
    lock = build_content_lock(
        chapter_id="012",
        scene={
            "scene_id": "012-02",
            "entry": "林澈进入旧城区",
            "exit": "拿到铜钥匙",
            "must_include": ["发现门后有脚印"],
            "must_not_include": ["不得揭露父亲身份"],
            "causal_predecessors": ["E011"],
        },
        plan={"immutable_facts": ["铜钥匙仍由林澈保管"]},
        state_snapshot={"characters": {"林澈": {"location": "旧城区"}}},
        prose_profile={"profile_id": "profile-3", "revision": 4},
        prompt_template_version="writer-sha",
        source_memory_ids=["event:E011", "expr:abc"],
    )

    assert lock["schema_version"] == 1
    assert lock["scene_id"] == "012-02"
    assert "发现门后有脚印" in lock["required_beats"]
    assert "铜钥匙仍由林澈保管" in lock["immutable_canon_facts"]
    assert lock["bindings"]["prose_profile_version"] == "profile-3"
    assert lock["bindings"]["source_memory_ids"] == ["event:E011", "expr:abc"]
    assert lock["lock_digest"]


def test_scene_render_contract_survives_candidate_validation_and_persistence(tmp_path):
    contract = build_scene_render_contract(
        "原始正文。" * 20,
        chapter_id="003",
        scene={"scene_id": "003-01", "must_include": ["状态改变"]},
        plan={"immutable_facts": ["不能改写事实"]},
        expression_contract="[SCENE_EXPRESSION_CONTRACT v1]",
    )
    candidate = "修订正文。" * 20

    result = validate_render_candidate("原始正文。" * 20, candidate, contract)
    assert result["pass"] is True
    assert result["contract"]["content_lock"]["scene_id"] == "003-01"
    assert result["contract"]["expression_contract"]
    assert result["contract"]["contract_id"]

    path = tmp_path / "render_contract.json"
    persist_render_contract(path, contract, metadata={"stage": "scene_generation"})
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["stage"] == "scene_generation"
    assert saved["content_lock"]["required_beats"] == ["状态改变"]
