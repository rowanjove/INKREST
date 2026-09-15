"""Tests for fidelity validator."""

from novel_agent.human_writing.fidelity import validate_fidelity
from novel_agent.human_writing.schemas import ProtectedSpan


def test_fidelity_validator_passed():
    orig = "林默数出了五百两银子，心里稍微安定了些。"
    cand = "林默清点好五百两银子，把钱袋收进怀中。"
    protected = [
        ProtectedSpan(kind="character", value="林默", policy="exact"),
        ProtectedSpan(kind="number", value="五百两银子", policy="exact"),
    ]
    res = validate_fidelity(orig, cand, protected, max_edit_ratio=0.60)
    assert res.passed is True
    assert len(res.violations) == 0
    assert len(res.preserved_spans) == 2


def test_fidelity_validator_missing_character():
    orig = "周晴快步走上前去，敲了敲门。"
    # The candidate omitted "周晴" and replaced it with someone else
    cand = "女孩快步走上前去，敲了敲门。"
    protected = [
        ProtectedSpan(kind="character", value="周晴", policy="exact"),
    ]
    res = validate_fidelity(orig, cand, protected)
    assert res.passed is False
    assert any("周晴" in v for v in res.violations)
    assert len(res.missing_spans) == 1


def test_fidelity_validator_code_fence_violation():
    orig = "林默低下头。"
    cand = "```markdown\n林默侧过身去。\n```"
    protected = [ProtectedSpan(kind="character", value="林默", policy="exact")]
    res = validate_fidelity(orig, cand, protected)
    assert res.passed is False
    assert any("代码块" in v for v in res.violations)
