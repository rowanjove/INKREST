"""Tests for protected spans extraction."""

from novel_agent.human_writing.protected_spans import extract_protected_spans


def test_extract_characters_and_quantities():
    text = "凌晨两点十三分，林默在旧巷里数出了五百两银子，身边还放着三把长剑。"
    spans = extract_protected_spans(text, project_characters=["林默"])

    span_values = {s.value for s in spans}
    assert "林默" in span_values
    assert any("凌晨" in s.value for s in spans)
    assert any("五百两银子" in s.value or "两银子" in s.value for s in spans)
    assert any("三把" in s.value or "三把长剑" in s.value for s in spans)


def test_extract_known_plot_facts():
    text = "周晴没有看见凶手的脸，只记得对方戴着一只黑色皮手套。"
    facts = ["周晴没有看见凶手的脸"]
    spans = extract_protected_spans(text, known_facts=facts)

    plot_fact_spans = [s for s in spans if s.kind == "plot_fact"]
    assert len(plot_fact_spans) == 1
    assert plot_fact_spans[0].value == "周晴没有看见凶手的脸"
    assert plot_fact_spans[0].policy == "must_preserve"
