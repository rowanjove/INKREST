from novel_agent.control.arc_contract import (
    build_arc_contract,
    seal_arc_contract,
    supersede_arc_contract,
    validate_plan_against_arc,
)
from novel_agent.services.outline_impact import analyze_outline_impact


def test_arc_contract_is_versioned_and_sealed_before_plan_use() -> None:
    draft = build_arc_contract("arc-1", chapter_start=1, chapter_end=10, objective="夺回城门")
    sealed = seal_arc_contract(draft)
    assert sealed.status == "sealed"
    assert validate_plan_against_arc(sealed, {"arc_id": "arc-1", "arc_contract_version": 1}) == []
    revised = supersede_arc_contract(sealed, objective="夺回城门并揭露内鬼")
    assert revised.version == 2
    assert revised.contract_digest != sealed.contract_digest


def test_outline_impact_distinguishes_written_canon_conflict() -> None:
    impact = analyze_outline_impact(
        {"secret": "真相A"},
        {"secret": "真相B"},
        written_chapters=["003"],
        canon_events=[{"chapter_id": "003", "secret": "真相A"}],
    )
    assert impact["impact"] == "invalidates_canon"
    assert impact["requires_confirmation"] is True
