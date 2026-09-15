"""Tests for HWE adaptive preference learning and calibrations (PRD §28.4, §59)."""

from pathlib import Path
import tempfile
import pytest

from novel_agent.human_writing import (
    HumanContextCompiler,
    HumanPromptContext,
    HumanWritingEngine,
    HWEPreferenceManager,
)
from novel_agent.state.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SQLiteStateStore(Path(tmpdir))
        yield store


def test_preference_manager_standalone():
    pm = HWEPreferenceManager()
    rule_id = "HWE.STAGING.BINARY_CONTRAST"

    assert rule_id not in pm.get_suppressed_rules()
    pm.suppress_rule(rule_id, reason="Author likes contrast")
    assert rule_id in pm.get_suppressed_rules()

    pm.unsuppress_rule(rule_id)
    assert rule_id not in pm.get_suppressed_rules()

    pm.adjust_rule_weight(rule_id, 0.5, reason="Soften severity")
    weights = pm.get_rule_weights()
    assert weights.get(rule_id) == 0.5

    profile = pm.export_profile()
    assert profile["rule_weights"][rule_id] == 0.5

    new_pm = HWEPreferenceManager()
    new_pm.import_profile(profile)
    assert new_pm.get_rule_weights().get(rule_id) == 0.5


def test_preference_manager_with_store(temp_store: SQLiteStateStore):
    pm = HWEPreferenceManager(store=temp_store, project_id="test_project")
    rule_id = "HWE.RHYTHM.STACCATO_ABUSE"

    # 1. Allow rule
    pm.record_issue_feedback(
        issue_id="issue_123",
        action="allow_rule",
        rule_id=rule_id,
        note="Intentional battle pacing",
    )
    assert rule_id in pm.get_suppressed_rules()

    # 2. False positive auto calibration on another rule
    fp_rule = "HWE.IMAGERY.STOCK_METAPHOR"
    for i in range(3):
        pm.record_issue_feedback(
            issue_id=f"fp_issue_{i}",
            action="false_positive",
            rule_id=fp_rule,
            note=f"False positive report {i}",
        )

    weights = pm.get_rule_weights()
    assert fp_rule in weights
    assert weights[fp_rule] <= 0.5


def test_preference_manager_engine_integration():
    pm = HWEPreferenceManager()
    engine = HumanWritingEngine()

    text = "这不是一次普通的谈话，而是一场关乎生死存亡的残酷博弈。"

    # Baseline scan: issue detected
    baseline_rep = engine.scan_text(text)
    assert any(i.hwe.rule_id == "HWE.STAGING.BINARY_CONTRAST" for i in baseline_rep.issues)

    # Scan with suppression preference
    pm.suppress_rule("HWE.STAGING.BINARY_CONTRAST")
    filtered_rep = engine.scan_text(text, preferences=pm)
    assert not any(i.hwe.rule_id == "HWE.STAGING.BINARY_CONTRAST" for i in filtered_rep.issues)


def test_preference_manager_compiler_integration():
    compiler = HumanContextCompiler()
    pm = HWEPreferenceManager()
    pm.suppress_rule("HWE.RHYTHM.TRIPLE_LIST_OVERUSE")

    ctx = HumanPromptContext(
        genre="玄幻",
        suppressed_rules=list(pm.get_suppressed_rules()),
    )
    prompt = compiler.compile(ctx)

    assert "机械三段式并列" not in prompt
