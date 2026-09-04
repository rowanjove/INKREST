from web.assistant_actions import sanitize_assistant_action, sanitize_assistant_actions


def test_chat_actions_drop_unknown_and_external_routes():
    cleaned = sanitize_assistant_actions(
        [
            {"type": "navigate", "label": "打开生产", "payload": {"route": "/production?tab=reviews"}},
            {"type": "navigate", "label": "外链", "payload": {"route": "https://evil.example/"}},
            {"type": "navigate", "label": "协议", "payload": {"route": "javascript:alert(1)"}},
            {"type": "rm_rf", "label": "删除", "payload": {}},
            {"type": "inspect_gate_detail", "label": "门禁", "payload": {"chapter_id": "012"}},
        ]
    )
    assert [item["type"] for item in cleaned] == ["navigate", "inspect_gate_detail"]
    assert cleaned[0]["payload"]["route"].startswith("/production")
    assert cleaned[1]["payload"]["chapter_id"] == "012"


def test_generating_chat_actions_become_production_navigation():
    retry = sanitize_assistant_action(
        {"type": "retry_task", "label": "重试第1章", "payload": {"chapter_id": "001", "goal": "开场"}}
    )
    repair = sanitize_assistant_action(
        {"type": "auto_repair_chapter", "label": "修章", "payload": {"chapter_id": "003"}}
    )
    assert retry["type"] == "navigate"
    assert "intent=novel_continue" in retry["payload"]["route"]
    assert repair["payload"]["route"] == "/production?tab=reviews&chapter=003"


def test_factory_intent_must_be_known():
    ok = sanitize_assistant_action({"type": "factory_intent", "label": "导出", "payload": {"intent": "export"}})
    bad = sanitize_assistant_action({"type": "factory_intent", "label": "炸", "payload": {"intent": "wipe"}})
    assert ok["payload"]["intent"] == "export"
    assert bad is None
