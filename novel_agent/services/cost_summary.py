"""LLM cost aggregates for monitor UI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

_ROUND_FIELDS = (
    "round",
    "tokens_used",
    "chapters_completed",
    "chapters_attempted",
    "ts",
    "started_at",
    "finished_at",
)

_SQL_TOTAL_ALL = """
    select
      count(*) as call_count,
      coalesce(sum(input_tokens), 0) as input_tokens,
      coalesce(sum(output_tokens), 0) as output_tokens,
      coalesce(sum(input_cost_cny), 0) as input_cost_cny,
      coalesce(sum(output_cost_cny), 0) as output_cost_cny
    from llm_cost_log
"""

_SQL_TOTAL_BY_PROJECT = """
    select
      count(*) as call_count,
      coalesce(sum(input_tokens), 0) as input_tokens,
      coalesce(sum(output_tokens), 0) as output_tokens,
      coalesce(sum(input_cost_cny), 0) as input_cost_cny,
      coalesce(sum(output_cost_cny), 0) as output_cost_cny
    from llm_cost_log
    where project_id = ?
"""

_SQL_TODAY_ALL = """
    select
      coalesce(sum(input_tokens + output_tokens), 0) as tokens,
      coalesce(sum(input_cost_cny + output_cost_cny), 0) as cost_cny
    from llm_cost_log
    where date(created_at, 'localtime') = date('now', 'localtime')
"""

_SQL_TODAY_BY_PROJECT = """
    select
      coalesce(sum(input_tokens + output_tokens), 0) as tokens,
      coalesce(sum(input_cost_cny + output_cost_cny), 0) as cost_cny
    from llm_cost_log
    where date(created_at, 'localtime') = date('now', 'localtime')
      and project_id = ?
"""


def _empty_persisted() -> Dict[str, Any]:
    return {
        "call_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "total_cost_cny": 0.0,
        "today_tokens": 0,
        "today_cost_cny": 0.0,
    }


def _row_to_persisted(row: tuple, today_row: Optional[tuple]) -> Dict[str, Any]:
    input_tokens = int(row[1] or 0)
    output_tokens = int(row[2] or 0)
    total_cost = float(row[3] or 0) + float(row[4] or 0)
    today_tokens = int(today_row[0] or 0) if today_row else 0
    today_cost = float(today_row[1] or 0) if today_row else 0.0
    return {
        "call_count": int(row[0] or 0),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "total_cost_cny": round(total_cost, 6),
        "today_tokens": today_tokens,
        "today_cost_cny": round(today_cost, 6),
    }


def query_persisted_cost_summary(
    root: Path,
    project_id: str = "",
) -> Tuple[Dict[str, Any], Optional[str]]:
    store = SQLiteStateStore(root)
    db_path = store.db_path
    if not db_path.is_file():
        return _empty_persisted(), None
    try:
        from novel_agent.state.sqlite_schema import safe_connection

        with safe_connection(db_path) as conn:
            if project_id:
                row = conn.execute(_SQL_TOTAL_BY_PROJECT, (project_id,)).fetchone()
                today_row = conn.execute(_SQL_TODAY_BY_PROJECT, (project_id,)).fetchone()
            else:
                row = conn.execute(_SQL_TOTAL_ALL).fetchone()
                today_row = conn.execute(_SQL_TODAY_ALL).fetchone()
    except Exception as exc:
        logger.warning("Failed to query llm cost summary for %s: %s", db_path, exc)
        return _empty_persisted(), str(exc)
    if not row:
        return _empty_persisted(), None
    return _row_to_persisted(row, today_row), None


def _sanitize_round(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: row[key] for key in _ROUND_FIELDS if key in row}


def read_recent_autopilot_rounds(root: Path, limit: int = 5) -> List[Dict[str, Any]]:
    path = root / "workspace" / "autopilot_rounds.jsonl"
    rows: List[Dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for line in lines[-max(1, limit) :]:
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(_sanitize_round(row))
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        logger.warning("Failed to read autopilot rounds from %s: %s", path, exc)
        return []
    return list(reversed(rows))


def build_cost_summary(root: Path) -> Dict[str, Any]:
    project_id = str(root.name)
    persisted, persisted_error = query_persisted_cost_summary(root, project_id=project_id)
    return {
        "project_id": project_id,
        "persisted": persisted,
        "persisted_error": persisted_error,
        "recent_rounds": read_recent_autopilot_rounds(root),
        "disclaimer": "落库实耗可能有延迟；连写弹窗估费为粗算，口径见 novel_agent/pricing.py",
    }