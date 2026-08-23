from pathlib import Path

from novel_agent.evaluation.fixtures import build_consistency_fixtures, load_fixture_file
from novel_agent.evaluation.taxonomy import CONSISTENCY_TAXONOMY, VARIANTS


def test_fixture_matrix_covers_taxonomy_and_evidence():
    cases = build_consistency_fixtures()
    assert len(cases) == sum(len(items) for items in CONSISTENCY_TAXONOMY.values()) * len(VARIANTS)
    assert {case.variant for case in cases} == set(VARIANTS)
    assert all(case.chapters and case.chapters[0]["text"] for case in cases)
    assert any(case.expected_evidence for case in cases if case.expected_label == "fail")


def test_checked_in_core_fixture_is_loadable():
    path = Path(__file__).parent / "fixtures" / "longform_consistency" / "core.jsonl"
    cases = load_fixture_file(path)
    assert len(cases) >= 5
    assert {case.category for case in cases} == {"人物", "事实", "时间情节", "世界规则", "声线表达"}
