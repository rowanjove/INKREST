"""Manual external (platform) review flags per chapter."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_VALID = frozenset({"none", "pending_external", "external_passed"})


def _path(root: Path) -> Path:
    return root / "workspace" / "reports" / "external_review.json"


def _load(root: Path) -> Dict[str, Any]:
    path = _path(root)
    if not path.is_file():
        return {"chapters": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("chapters", {})
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"chapters": {}}


def _save(root: Path, data: Dict[str, Any]) -> None:
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from novel_agent.services.pipeline_pending import invalidate_pipeline_alerts_cache

        invalidate_pipeline_alerts_cache(root)
    except Exception:
        pass


def set_external_review_status(
    root: Path,
    chapter_id: str,
    status: str,
    *,
    note: str = "",
) -> Dict[str, Any]:
    st = str(status or "none").strip()
    if st not in _VALID:
        raise ValueError(f"status must be one of {sorted(_VALID)}")
    data = _load(root)
    chapters = data.setdefault("chapters", {})
    if st == "none":
        chapters.pop(chapter_id, None)
    else:
        chapters[chapter_id] = {
            "status": st,
            "note": note,
            "updated_at": datetime.now().isoformat(),
        }
    _save(root, data)
    return chapters.get(chapter_id) or {"status": "none"}


def get_external_review_status(root: Path, chapter_id: str) -> str:
    return str(_load(root).get("chapters", {}).get(chapter_id, {}).get("status") or "none")


def list_pending_external(root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for cid, row in sorted(_load(root).get("chapters", {}).items()):
        if row.get("status") == "pending_external":
            out.append({"chapter_id": cid, **row})
    return out


def count_pending_external(root: Path) -> int:
    return len(list_pending_external(root))


def block_continue_until_external_pass(root: Path) -> bool:
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root).get("runtime", {}) or {}
    return bool(runtime.get("block_continue_until_external_pass"))