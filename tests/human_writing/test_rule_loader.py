"""Tests for HWE rule loader and registry."""

from novel_agent.human_writing.rules.loader import load_rules_from_dir, compute_ruleset_hash
from novel_agent.human_writing.rules.registry import RuleRegistry, get_rule_registry


def test_rule_loader_loads_builtin_rules():
    rules = load_rules_from_dir()
    assert len(rules) >= 20
    rule_ids = {r.id for r in rules}
    assert "HWE.STAGING.BINARY_CONTRAST" in rule_ids
    assert "HWE.NARRATION.OVER_EXPLANATION" in rule_ids
    assert "HWE.RHYTHM.TRIPLE_LIST_OVERUSE" in rule_ids
    assert "HWE.IMAGERY.BODY_REACTION_REPEAT" in rule_ids
    assert "HWE.DIALOGUE.EXPOSITION_DIALOGUE" in rule_ids


def test_rule_registry_queries():
    registry = get_rule_registry()
    assert registry.count() >= 20

    staging_rules = registry.list_rules(family="staging")
    assert len(staging_rules) >= 4

    rule = registry.get_rule("HWE.STAGING.BINARY_CONTRAST")
    assert rule is not None
    assert rule.family == "staging"
    assert rule.severity in ("low", "medium", "high")
    assert rule.why != ""

    hash_val = registry.ruleset_version
    assert isinstance(hash_val, str)
    assert len(hash_val) > 0
