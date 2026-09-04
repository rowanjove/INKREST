from unittest.mock import MagicMock, patch
from pathlib import Path

from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.agents.writer_task_card import build_writer_task_card, format_writer_task_card


PLAN = {
    "chapter_id": "001",
    "chapter_title": "雨夜",
    "detailed_synopsis": "林澈取信后离开出租屋。",
    "beats": [
        {"beat_id": "B01", "function": "开场", "content": "推门进屋看到信"},
        {"beat_id": "B02", "function": "转折", "content": "信上要求连夜离开"},
        {"beat_id": "B03", "function": "钩子", "content": "门外有人等着"},
    ],
    "foreshadow_plan": [
        {"title": "匿名信", "action": "progress", "detail": "信上只有一个地址"}
    ],
    "handoff_to_scene_planner": {
        "must_include": ["信", "离开"],
        "must_not_include": ["解释信的来源"],
    },
}

SCENE = {
    "scene_id": "001-01",
    "purpose": "开门取信离开",
    "entry": "林澈回到出租屋",
    "exit": "他拉开门走出去",
    "must_include": ["信"],
    "must_not_include": [],
}


def test_task_card_compresses_plan_into_short_card():
    card = build_writer_task_card(PLAN, SCENE)
    assert card["goal"]
    assert "信" in card["must_include"]
    assert "解释信的来源" in card["must_not_include"]
    assert any("门外" in beat for beat in card["beats"])
    assert any("匿名信" in item for item in card["foreshadow_collect"])
    assert "走出去" in card["exit_hook"]
    text = format_writer_task_card(card)
    assert "写前任务卡" in text
    assert len(text) <= 1200


def test_context_builder_injects_task_card_as_critical_block():
    mock_store = MagicMock()
    mock_store.get_continuity_state.return_value = {}
    mock_store.list_secrets.return_value = []
    mock_store.list_reader_promises.return_value = []
    with patch("novel_agent.agents.context_builder.SQLiteStateStore", return_value=mock_store):
        builder = ContextBuilderAgent(Path("/mock/root"), MagicMock())
    builder._writer_anti_ai_enabled = lambda: False
    builder._prune_character_cards = lambda scene: ""
    builder._build_character_memories_block = lambda chars: ""
    builder._character_consistency_block = lambda scene: ""
    builder._build_debt_block = lambda scene: ""
    builder._build_expression_avoidance_block = lambda scene: ""
    builder._build_content_lock_block = lambda *args, **kwargs: ""
    builder._build_character_voice_block = lambda scene: ""
    builder._build_event_evidence_block = lambda scene: ""
    builder._build_medium_priority_blocks = lambda goal, scene: []
    builder._build_low_priority_blocks = lambda goal, scene: []
    builder._persist_context_pack_contract = lambda scene, text: None

    context = builder.build("林澈取信后离开。", SCENE, plan=PLAN)
    assert "写前任务卡" in context
    assert "匿名信" in context
