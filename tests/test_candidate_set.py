"""Bounded local candidate-set and human-feedback primitives."""

from datetime import datetime, timedelta, timezone

import pytest

from novel_agent.quality.candidate_set import (
    build_candidate_set,
    content_lock_id,
    create_pairwise_session,
    list_candidate_feedback,
    list_candidate_timeline,
    load_candidate_set,
    rank_candidates,
    record_candidate_feedback,
    restore_candidate_set_snapshot,
    submit_pairwise_session,
    pairwise_calibration_summary,
)
from novel_agent.quality.render_contract import build_scene_render_contract


def _contract():
    return build_scene_render_contract(
        "林澈握着铜钥匙走进旧城区。",
        chapter_id="002",
        scene={
            "scene_id": "002-01",
            "must_include": ["铜钥匙", "旧城区"],
            "immutable_facts": ["钥匙仍由林澈保管"],
        },
    )


def test_build_candidate_set_binds_source_and_lock_and_enforces_budget(tmp_path):
    source = "林澈握着铜钥匙走进旧城区。"
    contract = _contract()
    payload = build_candidate_set(
        tmp_path,
        "002",
        source_text=source,
        content_lock=contract,
        candidates=[
            {"candidate_id": "a", "text": "林澈攥紧铜钥匙，走进旧城区。", "cost_units": 1},
            {"candidate_id": "b", "text": "林澈带着铜钥匙踏入旧城区。", "cost_units": 2},
            {"candidate_id": "c", "text": "超出成本预算的候选。", "cost_units": 2},
            {"candidate_id": "wrong-source", "text": "来源不一致。", "source_sha256": "bad"},
            {"candidate_id": "wrong-lock", "text": "锁不一致。", "content_lock_id": "other-lock"},
        ],
        cost_budget=3,
    )

    assert payload["enabled"] is False
    assert payload["content_lock_id"] == content_lock_id(contract)
    assert [item["candidate_id"] for item in payload["candidates"]] == ["a", "b"]
    assert payload["used_cost_units"] == 3
    reasons = {item["candidate_id"]: item["rejected_reason"] for item in payload["rejected_candidates"]}
    assert reasons["c"] == "cost_budget_exceeded"
    assert reasons["wrong-source"] == "source_sha256_mismatch"
    assert reasons["wrong-lock"] == "content_lock_mismatch"
    assert load_candidate_set(tmp_path, "002")["candidate_set_id"] == payload["candidate_set_id"]


def test_candidate_set_expires_without_mutating_the_saved_artifact(tmp_path):
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    payload = build_candidate_set(
        tmp_path,
        "003",
        source_text="原稿。",
        candidates=[{"candidate_id": "a", "text": "候选稿。"}],
        ttl_days=1,
        now=now,
    )

    loaded = load_candidate_set(tmp_path, "003", now=now + timedelta(days=1))
    assert loaded["status"] == "expired"
    assert loaded["candidates"][0]["status"] == "expired"
    saved = load_candidate_set(tmp_path, "003", now=now)
    assert saved["status"] == "ready"
    assert saved["candidates"][0]["status"] == "pending"
    assert payload["policy"]["ttl_days"] == 1


def test_feedback_is_validated_persisted_and_ranked_deterministically(tmp_path):
    build_candidate_set(
        tmp_path,
        "004",
        source_text="原稿。",
        candidates=[
            {"candidate_id": "a", "text": "候选甲。"},
            {"candidate_id": "b", "text": "候选乙。"},
        ],
    )

    record_candidate_feedback(
        tmp_path,
        "004",
        {"kind": "pairwise", "candidate_a": "a", "candidate_b": "b", "choice": "a"},
    )
    record_candidate_feedback(tmp_path, "004", {"kind": "accept", "candidate_id": "a"})
    record_candidate_feedback(tmp_path, "004", {"kind": "edit", "candidate_id": "a", "edited_text": "微调后。"})
    record_candidate_feedback(tmp_path, "004", {"kind": "delete", "candidate_id": "b"})

    events = list_candidate_feedback(tmp_path, "004")
    assert len(events) == 4
    assert all(event["source_sha256"] for event in events)
    assert events[2]["edited_text_sha256"]
    assert events[2]["edited_text_chars"] == 4
    ranked = rank_candidates(tmp_path, "004")
    assert [item["candidate_id"] for item in ranked] == ["a", "b"]
    assert ranked[0]["feedback_score"] == 4
    assert ranked[1]["feedback_score"] == -3
    assert load_candidate_set(tmp_path, "004")["candidates"][0]["status"] == "accepted"
    assert load_candidate_set(tmp_path, "004")["candidates"][1]["status"] == "rejected"

    with pytest.raises(ValueError, match="distinct candidates"):
        record_candidate_feedback(
            tmp_path,
            "004",
            {"kind": "pairwise", "candidate_a": "a", "candidate_b": "a", "choice": "tie"},
        )

    old_set_id = load_candidate_set(tmp_path, "004")["candidate_set_id"]
    build_candidate_set(
        tmp_path,
        "004",
        source_text="新源稿。",
        candidates=[{"candidate_id": "a", "text": "新候选甲。"}, {"candidate_id": "b", "text": "新候选乙。"}],
    )
    new_set = load_candidate_set(tmp_path, "004")
    assert new_set["candidate_set_id"] != old_set_id
    assert all(item["feedback_score"] == 0 for item in rank_candidates(tmp_path, "004"))
    assert list_candidate_feedback(tmp_path, "004", candidate_set_id=old_set_id)
    assert not list_candidate_feedback(tmp_path, "004", candidate_set_id=new_set["candidate_set_id"])


def test_l0_rejects_format_and_explicit_literal_fact_failures(tmp_path):
    source = "林澈握住铜钥匙，走进旧城区。"
    payload = build_candidate_set(
        tmp_path,
        "005",
        source_text=source,
        content_lock={
            "contract_id": "lock-5",
            "required_fragments": ["铜钥匙"],
            "forbidden_fragments": ["现代枪械"],
        },
        candidates=[
            {"candidate_id": "good", "text": "林澈攥紧铜钥匙，走进旧城区。"},
            {"candidate_id": "markdown", "text": "# 林澈攥紧铜钥匙，走进旧城区。"},
            {"candidate_id": "missing", "text": "林澈走进旧城区。"},
            {"candidate_id": "forbidden", "text": "林澈攥紧铜钥匙，带着现代枪械走进旧城区。"},
        ],
    )

    assert [item["candidate_id"] for item in payload["candidates"]] == ["good"]
    rejected = {item["candidate_id"]: item for item in payload["rejected_candidates"]}
    assert rejected["markdown"]["rejected_reason"] == "l0_validation_failed"
    assert "markdown_heading" in rejected["markdown"]["l0_validation"]["reasons"]
    assert "required_fragment_missing" in rejected["missing"]["l0_validation"]["reasons"]
    assert "forbidden_fragment_present" in rejected["forbidden"]["l0_validation"]["reasons"]


def test_candidate_timeline_restores_snapshot_with_fresh_identity(tmp_path):
    now = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)
    created = build_candidate_set(
        tmp_path,
        "006",
        source_text="原稿版本一。",
        candidates=[{"candidate_id": "a", "text": "候选版本一。"}],
        now=now,
    )
    created_snapshot = next(
        item for item in list_candidate_timeline(tmp_path, "006") if item["event"] == "created"
    )
    rebuilt = build_candidate_set(
        tmp_path,
        "006",
        source_text="原稿版本一。",
        candidates=[{"candidate_id": "a", "text": "候选版本一。"}],
        now=now + timedelta(seconds=1),
    )
    assert rebuilt["candidate_set_id"] != created["candidate_set_id"]
    record_candidate_feedback(
        tmp_path,
        "006",
        {"kind": "accept", "candidate_id": "a"},
        now=now + timedelta(minutes=1),
    )
    timeline = list_candidate_timeline(tmp_path, "006")
    assert [item["event"] for item in timeline[:2]] == ["feedback:accept", "created"]
    restored = restore_candidate_set_snapshot(
        tmp_path,
        "006",
        created_snapshot["timeline_id"],
        now=now + timedelta(hours=1),
    )
    assert restored["candidate_set_id"] != created["candidate_set_id"]
    assert restored["restored_from_timeline_id"] == created_snapshot["timeline_id"]
    assert restored["revision"] == 2
    assert restored["feedback_count"] == 0
    assert rank_candidates(tmp_path, "006")[0]["feedback_score"] == 0
    assert list_candidate_timeline(tmp_path, "006")[0]["event"] == "restored"


def test_expired_candidate_snapshot_cannot_be_restored(tmp_path):
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    build_candidate_set(
        tmp_path,
        "007",
        source_text="原稿。",
        candidates=[{"candidate_id": "a", "text": "候选稿。"}],
        ttl_days=1,
        now=now,
    )
    snapshot = list_candidate_timeline(tmp_path, "007")[0]
    with pytest.raises(ValueError, match="expired"):
        restore_candidate_set_snapshot(tmp_path, "007", snapshot["timeline_id"], now=now + timedelta(days=1))


def test_pairwise_session_blinds_candidate_ids_and_is_one_shot(tmp_path):
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    payload = build_candidate_set(
        tmp_path,
        "008",
        source_text="原稿。",
        candidates=[
            {"candidate_id": "a", "text": "候选甲。"},
            {"candidate_id": "b", "text": "候选乙。"},
        ],
        now=now,
    )
    public = create_pairwise_session(
        tmp_path,
        "008",
        candidate_set_id=payload["candidate_set_id"],
        candidate_a="a",
        candidate_b="b",
        now=now + timedelta(minutes=1),
    )
    assert {option["label"] for option in public["options"]} == {"A", "B"}
    assert {option["text"] for option in public["options"]} == {"候选甲。", "候选乙。"}
    assert "candidate_a_id" not in public
    result = submit_pairwise_session(
        tmp_path,
        "008",
        public["session_id"],
        choice="a",
        now=now + timedelta(minutes=2),
    )
    assert result["status"] == "recorded"
    assert result["feedback_id"]
    event = list_candidate_feedback(tmp_path, "008")[0]
    assert {event["candidate_a"], event["candidate_b"]} == {"a", "b"}
    with pytest.raises(ValueError, match="already closed"):
        submit_pairwise_session(tmp_path, "008", public["session_id"], choice="b")


def test_pairwise_calibration_is_grouped_and_uncalibrated_with_small_samples(tmp_path):
    payload = build_candidate_set(tmp_path, "009", source_text="原稿。", candidates=[{"candidate_id": "a", "text": "甲。"}, {"candidate_id": "b", "text": "乙。"}])
    record_candidate_feedback(tmp_path, "009", {"kind": "pairwise", "candidate_a": "a", "candidate_b": "b", "choice": "a", "user_id": "u1", "genre": "悬疑"})
    result = pairwise_calibration_summary(tmp_path, minimum_samples=2)
    assert result["status"] == "uncalibrated"
    assert result["groups"][0]["group"]["user_id"] == "u1"
    assert result["auto_choice_recommended"] is False


def test_pairwise_calibration_restores_candidate_direction_before_win_rate(tmp_path):
    build_candidate_set(
        tmp_path,
        "010",
        source_text="原稿。",
        candidates=[{"candidate_id": "a", "text": "甲。"}, {"candidate_id": "b", "text": "乙。"}],
    )
    record_candidate_feedback(
        tmp_path,
        "010",
        {"kind": "pairwise", "candidate_a": "a", "candidate_b": "b", "choice": "a", "user_id": "u1"},
    )
    record_candidate_feedback(
        tmp_path,
        "010",
        {"kind": "pairwise", "candidate_a": "a", "candidate_b": "b", "choice": "b", "user_id": "u1"},
    )
    result = pairwise_calibration_summary(tmp_path, minimum_samples=2)
    group = result["groups"][0]
    assert group["wins"] == 1
    assert group["losses"] == 1
    assert group["win_rate"] == 0.5
    assert group["candidate_outcomes"]["a"]["wins"] == 1
    assert group["candidate_outcomes"]["a"]["losses"] == 1
