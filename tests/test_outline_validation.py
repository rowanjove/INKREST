"""Outline validation and finalize."""

from novel_agent.control.outline_validation import (
    finalize_outline_for_save,
    validate_outline_document,
)


def test_validate_rejects_empty_protagonist() -> None:
    doc = {"macro_outline": [{"arc_id": "A01", "chapters": "1-5", "goal": "g"}], "target_chapters": 5}
    result = validate_outline_document(doc)
    assert result["valid"] is False
    assert any("protagonist" in e for e in result["errors"])


def test_finalize_adds_layer_impl() -> None:
    doc = {
        "core_theme": "测试",
        "protagonist": {"name": "林越"},
        "macro_outline": [{"arc_id": "A01", "name": "卷一", "chapters": "1-10", "goal": "开局"}],
        "target_chapters": 10,
        "scale_profile": {"scale": "short"},
    }
    out = finalize_outline_for_save(doc)
    assert "outline_layer_impl" in out
    assert out["outline_layer_impl"]["L3"]