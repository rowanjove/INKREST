"""Tests for HWE SQLite persistence and repository mixin."""

from pathlib import Path
import tempfile
import pytest

from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.state.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SQLiteStateStore(Path(tmpdir))
        yield store


def test_hwe_report_persistence(temp_store: SQLiteStateStore):
    engine = HumanWritingEngine()
    text = "这不是一次普通的谈话，而是一场关乎生死存亡的残酷博弈。他面带微笑，眼中闪过一丝不易察觉的寒芒。"
    report = engine.scan_text(text, chapter_id="chap_01")

    report_id = temp_store.save_hwe_report(report, chapter_id="chap_01")
    assert report_id is not None

    latest = temp_store.get_latest_hwe_report("chap_01")
    assert latest is not None
    assert latest["id"] == report_id
    assert latest["chapter_id"] == "chap_01"
    assert len(latest["issues"]) >= 1
    assert "scores" in latest
    assert latest["scores"]["overall_score"] < 100

    issue = latest["issues"][0]
    issue_id = issue["id"]
    assert issue["status"] == "open"

    resolved = temp_store.resolve_hwe_issue(issue_id, status="ignored", resolution_note="Author intentional style")
    assert resolved is True

    updated_issues = temp_store.list_hwe_issues(chapter_id="chap_01")
    target_issue = next(i for i in updated_issues if i["id"] == issue_id)
    assert target_issue["status"] == "ignored"
    assert target_issue["resolution_note"] == "Author intentional style"


def test_hwe_patch_persistence(temp_store: SQLiteStateStore):
    patch_id = temp_store.save_hwe_patch({
        "chapter_id": "chap_02",
        "target_start": 10,
        "target_end": 35,
        "original_text": "这不是一次普通的谈话，而是一场生死博弈。",
        "patched_text": "二人相对而坐，各怀杀机。",
        "issues_addressed": ["HWE.STAGING.BINARY_CONTRAST"],
        "status": "applied",
    })
    assert patch_id is not None

    patches = temp_store.list_hwe_patches("chap_02")
    assert len(patches) == 1
    assert patches[0]["patched_text"] == "二人相对而坐，各怀杀机。"
    assert patches[0]["issues_addressed"] == ["HWE.STAGING.BINARY_CONTRAST"]


def test_hwe_preference_persistence(temp_store: SQLiteStateStore):
    temp_store.save_hwe_preference(
        project_id="proj_1",
        preference_key="suppressed_rules",
        rule_id="HWE.RHYTHM.STACCATO_ABUSE",
        value={"reason": "Action fight scene needs staccato", "suppressed": True},
    )

    prefs = temp_store.get_hwe_preferences("proj_1")
    assert len(prefs) == 1
    assert prefs[0]["preference_key"] == "suppressed_rules"
    assert prefs[0]["rule_id"] == "HWE.RHYTHM.STACCATO_ABUSE"
    assert prefs[0]["value"]["suppressed"] is True

    single = temp_store.get_hwe_rule_preference(
        rule_id="HWE.RHYTHM.STACCATO_ABUSE",
        preference_key="suppressed_rules",
        project_id="proj_1",
    )
    assert single is not None
    assert single["value"]["reason"] == "Action fight scene needs staccato"


def test_clear_narrative_state_clears_hwe(temp_store: SQLiteStateStore):
    engine = HumanWritingEngine()
    report = engine.scan_text("这不是普通的谈话，而是一场博弈。")
    temp_store.save_hwe_report(report, chapter_id="c_clear")
    temp_store.save_hwe_patch({
        "chapter_id": "c_clear",
        "target_start": 0,
        "target_end": 10,
        "original_text": "A",
        "patched_text": "B",
    })

    assert temp_store.get_latest_hwe_report("c_clear") is not None
    assert len(temp_store.list_hwe_patches("c_clear")) == 1

    cleared = temp_store.clear_narrative_state()
    assert "hwe_reports" in cleared
    assert "hwe_issues" in cleared
    assert "hwe_patches" in cleared

    assert temp_store.get_latest_hwe_report("c_clear") is None
    assert len(temp_store.list_hwe_patches("c_clear")) == 0
