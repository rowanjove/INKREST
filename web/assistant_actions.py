"""Whitelist and sanitize assistant/pet chat actions."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse

ALLOWED_FIX_TYPES = frozenset(
    {
        "test_model",
        "retry_task",
        "auto_repair_chapter",
        "rerun_gate",
        "inspect_gate_detail",
    }
)
GENERATING_ACTION_TYPES = frozenset({"retry_task", "auto_repair_chapter", "rerun_gate"})
ALLOWED_ACTION_TYPES = ALLOWED_FIX_TYPES | frozenset({"navigate", "factory_intent"})
ALLOWED_FACTORY_INTENTS = frozenset({"create", "plan", "run", "monitor", "repair", "export"})
def _safe_route(raw: Any) -> Optional[str]:
    route = str(raw or "").strip()
    if not route.startswith("/") or route.startswith("//"):
        return None
    parsed = urlparse(route)
    if parsed.scheme or parsed.netloc:
        return None
    return route


def production_confirm_route(action_type: str, payload: Mapping[str, Any]) -> str:
    chapter_id = str(payload.get("chapter_id") or "").strip()
    if action_type in {"auto_repair_chapter", "rerun_gate"}:
        query = "tab=reviews"
        if chapter_id:
            query += f"&chapter={chapter_id}"
        return f"/production?{query}"
    if action_type == "retry_task":
        return "/production?intent=novel_continue&confirm=1"
    return "/production?confirm=1"


def sanitize_assistant_action(action: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(action, dict):
        return None
    action_type = str(action.get("type") or "").strip()
    if action_type not in ALLOWED_ACTION_TYPES:
        return None
    label = str(action.get("label") or action_type).strip() or action_type
    raw_payload = action.get("payload")
    payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}

    if action_type == "navigate":
        route = _safe_route(payload.get("route"))
        if not route:
            return None
        return {"type": "navigate", "label": label, "payload": {"route": route}}

    if action_type == "factory_intent":
        intent = str(payload.get("intent") or "").strip()
        if intent not in ALLOWED_FACTORY_INTENTS:
            return None
        return {"type": "factory_intent", "label": label, "payload": {"intent": intent}}

    if action_type in GENERATING_ACTION_TYPES:
        return {
            "type": "navigate",
            "label": label,
            "payload": {"route": production_confirm_route(action_type, payload)},
        }

    cleaned_payload: Dict[str, Any] = {}
    chapter_id = str(payload.get("chapter_id") or "").strip()
    if chapter_id:
        cleaned_payload["chapter_id"] = chapter_id
    return {"type": action_type, "label": label, "payload": cleaned_payload}


def sanitize_assistant_actions(actions: Any) -> List[Dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for item in actions:
        safe = sanitize_assistant_action(item)
        if safe:
            cleaned.append(safe)
    return cleaned
