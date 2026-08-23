from pathlib import Path

import pytest

from novel_agent.control.arc_contract_store import (
    create_arc_contract,
    list_arc_contract_history,
    load_arc_contract,
    restore_saved_arc_contract,
    seal_saved_arc_contract,
    supersede_saved_arc_contract,
    validate_saved_plan,
)


def test_arc_contract_store_is_versioned_and_blocks_mismatched_plan(tmp_path: Path):
    contract = create_arc_contract(tmp_path, {"arc_id": "A01", "chapter_start": 1, "chapter_end": 10, "objective": "守住北门"})
    assert contract.status == "draft"
    sealed = seal_saved_arc_contract(tmp_path, "A01")
    assert sealed.status == "sealed"
    assert load_arc_contract(tmp_path, "A01").status == "sealed"
    issues = validate_saved_plan(tmp_path, "A01", {"arc_id": "A01", "arc_contract_version": 0})
    assert {item["code"] for item in issues} == {"ARC_VERSION_MISMATCH"}


def test_missing_contract_is_explicit_replan_issue(tmp_path: Path):
    assert validate_saved_plan(tmp_path, "missing", {})[0]["code"] == "ARC_CONTRACT_MISSING"


def test_arc_contract_history_is_immutable_and_restore_appends_revision(tmp_path: Path):
    create_arc_contract(tmp_path, {"arc_id": "A01", "chapter_start": 1, "chapter_end": 10, "objective": "守住北门"})
    seal_saved_arc_contract(tmp_path, "A01")
    revised = supersede_saved_arc_contract(tmp_path, "A01", {"objective": "夺回北门"})
    assert revised.version == 2
    history = list_arc_contract_history(tmp_path, "A01")
    assert [item.version for item in history] == [1, 2]
    restored = restore_saved_arc_contract(tmp_path, "A01", 1)
    assert restored.version == 3
    assert restored.objective == "守住北门"
    assert [item.version for item in list_arc_contract_history(tmp_path, "A01")] == [1, 2, 3]


def test_sealed_revision_is_the_archived_revision_and_duplicate_create_is_rejected(tmp_path: Path):
    create_arc_contract(tmp_path, {"arc_id": "A01", "chapter_start": 1, "chapter_end": 10, "objective": "守住北门"})
    sealed = seal_saved_arc_contract(tmp_path, "A01")
    revised = supersede_saved_arc_contract(
        tmp_path,
        "A01",
        {"expected_version": sealed.version, "objective": "夺回北门"},
    )

    history = list_arc_contract_history(tmp_path, "A01")
    assert [(item.version, item.status) for item in history] == [(1, "sealed"), (2, "draft")]
    with pytest.raises(FileExistsError):
        create_arc_contract(
            tmp_path,
            {"arc_id": "A01", "chapter_start": 1, "chapter_end": 10, "objective": "覆盖"},
        )
    with pytest.raises(ValueError, match="stale"):
        supersede_saved_arc_contract(
            tmp_path,
            "A01",
            {"expected_version": sealed.version, "objective": "过期更新"},
        )
    assert load_arc_contract(tmp_path, "A01").version == revised.version
