import pytest

from novel_agent.state.update_validator import StateUpdateValidationError, validate_state_update


def test_state_update_schema_rejects_wrong_collection_type():
    with pytest.raises(StateUpdateValidationError, match="schema invalid"):
        validate_state_update("001", {"events": "not-a-list"})


def test_state_update_schema_keeps_valid_payload():
    cleaned = validate_state_update(
        "001",
        {
            "events": [{"id": "e1", "summary": "开场"}],
            "characters": {"林澈": {"status": "alive"}},
            "garbage": "drop-me",
        },
    )
    assert "garbage" not in cleaned
    assert cleaned["events"][0]["id"] == "e1"
    assert cleaned["characters"]["林澈"]["status"] == "alive"
