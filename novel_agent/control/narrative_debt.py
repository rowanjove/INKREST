from __future__ import annotations

from typing import Any, Dict, List


def _to_int(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def classify_debt(
    items: List[Dict[str, Any]],
    current_chapter: str,
    default_period: int = 10,
    weight: float = 1.0
) -> List[Dict[str, Any]]:
    """Add due/overdue status to narrative debt rows and calculate tension score.
    
    Supports default recovery period based on debt sub-type if deadline_chapter is not set.
    """
    current = _to_int(current_chapter)
    result: List[Dict[str, Any]] = []
    for item in items:
        deadline_raw = item.get("deadline_chapter")
        if deadline_raw and str(deadline_raw).strip():
            deadline = _to_int(deadline_raw)
        else:
            start_ch = _to_int(item.get("chapter_id"))
            deadline = start_ch + default_period if start_ch > 0 else 0

        status = str(item.get("status", ""))
        # secrets are hidden when active, resolved when revealed/closed
        is_open = status not in ("resolved", "revealed", "closed", "shown")
        debt_status = "open" if is_open else "resolved"
        
        user_priority = _to_int(item.get("user_priority", 0))
        
        # Calculate Tension Score
        intro_chapter = _to_int(item.get("chapter_id"))
        priority_factor = user_priority if user_priority > 0 else 1
        delta = max(0, current - intro_chapter)
        tension_score = float(round(delta * priority_factor * weight, 2))
        
        alert = False
        if is_open:
            if user_priority > 0:
                debt_status = "overdue"
                alert = True
            elif deadline:
                if current > deadline:
                    debt_status = "overdue"
                    alert = True
                elif current >= deadline - 2:
                    debt_status = "due_soon"
            
            if tension_score >= 15.0:
                alert = True
                    
        result.append({
            **item,
            "deadline_chapter": str(deadline) if deadline else "",
            "debt_status": debt_status,
            "tension_score": tension_score,
            "alert": alert
        })
    return result

