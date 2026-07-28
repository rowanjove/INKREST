from __future__ import annotations

from typing import Any, Dict, List


def synthesize_constraints(
    state: Dict[str, Any],
    recall_items: List[Dict[str, Any]],
    scene: Dict[str, Any],
) -> List[str]:
    """Turn state and recall facts into concise constraints for the writer."""
    constraints: List[str] = []

    for secret in state.get("secrets", []):
        if secret.get("status") in ("hidden", "open"):
            title = secret.get("title", "")
            description = secret.get("description", "")
            constraints.append(f"不可提前揭露：{title}。{description}".strip())

    for promise in state.get("reader_promises", []):
        if promise.get("debt_status") in ("due_soon", "overdue"):
            title = promise.get("title", "")
            description = promise.get("description", "")
            constraints.append(f"需要推进读者承诺：{title}。{description}".strip())

    for item in recall_items[:3]:
        text = item.get("text") or item.get("summary") or ""
        if text:
            constraints.append(f"历史一致性参考：{text[:120]}")

    return [item for item in constraints if item]

