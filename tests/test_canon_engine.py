from novel_agent.quality.canon_engine import (
    check_canon_visibility,
    facts_as_of_chapter,
    filter_visible_canon,
)


def test_canon_engine_blocks_future_superseded_and_unknown_facts() -> None:
    facts = [
        {"memory_id": "future", "source_chapter": "010"},
        {"memory_id": "old", "source_chapter": "002", "superseded": True},
        {
            "memory_id": "belief",
            "source_chapter": "002",
            "truth_scope": "character_belief",
            "knower_ids": ["沈砚"],
        },
        {"memory_id": "safe", "source_chapter": "002", "truth_scope": "objective"},
    ]
    violations = check_canon_visibility(
        facts,
        current_chapter="003",
        known_character_ids={"林澈"},
    )
    assert {item.code for item in violations} == {
        "future_fact",
        "superseded_fact",
        "knowledge_boundary",
    }
    visible, _ = filter_visible_canon(
        facts,
        current_chapter="003",
        known_character_ids={"林澈"},
    )
    assert [item["memory_id"] for item in visible] == ["safe"]


def test_facts_as_of_chapter_drops_future_events_before_visibility_check() -> None:
    facts = [
        {"memory_id": "past", "chapter_id": "002", "source_chapter": "002"},
        {"memory_id": "future", "chapter_id": "010", "source_chapter": "010"},
    ]
    as_of = facts_as_of_chapter(facts, "003")
    assert [item["memory_id"] for item in as_of] == ["past"]
    violations = check_canon_visibility(as_of, current_chapter="003")
    assert violations == []
