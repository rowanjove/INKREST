from novel_agent.quality.canon_engine import check_canon_visibility, filter_visible_canon


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
