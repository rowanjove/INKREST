"""Fast chapter progress high-water marks for long runs (avoid O(n) directory scans)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from novel_agent.logging_config import get_logger
from novel_agent.services.rolling_planner import format_chapter_id

logger = get_logger("services.chapter_highwater")

CACHE_REL = "workspace/reports/chapter_highwater.json"
_FORWARD_SCAN_CAP = 48


def _cache_path(root_dir: Path) -> Path:
    return Path(root_dir) / CACHE_REL


def load_highwater(root_dir: Path) -> Dict[str, Any]:
    path = _cache_path(root_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_highwater(root_dir: Path, data: Dict[str, Any]) -> None:
    path = _cache_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def bump_chapter_written(root_dir: Path, chapter_id: str, *, pipeline_complete: bool = False) -> None:
    """Call after a chapter finishes writing (and optionally passes post_audit)."""
    try:
        num = int(str(chapter_id).strip())
    except ValueError:
        return
    data = load_highwater(root_dir)
    data["max_disk"] = max(int(data.get("max_disk") or 0), num)
    if pipeline_complete:
        data["last_complete_num"] = max(int(data.get("last_complete_num") or 0), num)
    save_highwater(root_dir, data)


def sync_highwater_from_store(root_dir: Path) -> None:
    """Refresh cache from SQLite chapter index when available."""
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(root_dir)
        mx = store.max_numeric_chapter_id()
        data = load_highwater(root_dir)
        if mx is None:
            data["max_disk"] = 0
            data["last_complete_num"] = 0
        else:
            mx_val = int(mx)
            data["max_disk"] = mx_val
            if "last_complete_num" in data and int(data["last_complete_num"]) > mx_val:
                data["last_complete_num"] = mx_val
        save_highwater(root_dir, data)
    except Exception as exc:
        logger.error("Highwater sync from store failed: %s", exc)


def _max_from_arcs(root_dir: Path) -> int:
    from novel_agent.services.arc_queue import chapter_id_from_brief, load_workspace_arcs

    high = 0
    for arc in load_workspace_arcs(root_dir):
        for ch in arc.get("chapters") or []:
            cid = chapter_id_from_brief(ch)
            if cid.isdigit():
                high = max(high, int(cid))
    return high


def _max_from_sqlite(root_dir: Path) -> int:
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        mx = SQLiteStateStore(root_dir).max_numeric_chapter_id()
        return int(mx) if mx is not None else 0
    except Exception:
        return 0


def _scan_disk_high(root_dir: Path, *, min_num: int = 0) -> int:
    """Fallback scan; only considers chapter dirs at or above min_num when possible."""
    ws = root_dir / "workspace" / "chapters"
    if not ws.is_dir():
        return 0
    high = 0
    for d in ws.iterdir():
        if not d.is_dir() or not d.name.startswith("chapter_"):
            continue
        raw = d.name.replace("chapter_", "", 1)
        if not raw.isdigit():
            continue
        num = int(raw)
        if num < min_num:
            continue
        final = d / "chapter_final.txt"
        if final.is_file():
            try:
                if len(final.read_text(encoding="utf-8").strip()) > 80:
                    high = max(high, num)
            except OSError:
                pass
    return high


def _forward_verify_complete(
    root_dir: Path,
    start_num: int,
    complete_fn: Callable[[str], bool],
) -> int:
    verified = start_num
    for n in range(start_num + 1, start_num + _FORWARD_SCAN_CAP + 1):
        cid = format_chapter_id(n)
        chapter_dir = root_dir / "workspace" / "chapters" / f"chapter_{cid}"
        if not chapter_dir.is_dir():
            break
        if complete_fn(cid):
            verified = n
        else:
            break
    return verified


def resolve_max_generated_chapter_num(
    root_dir: Path,
    complete_fn: Optional[Callable[[str], bool]] = None,
    *,
    allow_full_scan: bool = False,
) -> int:
    """
    Highest numeric chapter id relevant for rolling replenish.

    Uses arc queue + SQLite/cache before scanning all chapter_* directories.
    """
    high = max(_max_from_arcs(root_dir), _max_from_sqlite(root_dir))
    hw = load_highwater(root_dir)
    high = max(high, int(hw.get("max_disk") or 0))

    if complete_fn is None:
        if high == 0 or allow_full_scan:
            high = max(high, _scan_disk_high(root_dir))
        else:
            high = max(high, _scan_disk_high(root_dir, min_num=max(0, high - 5)))
        return high

    cached_complete = int(hw.get("last_complete_num") or 0)
    if cached_complete > 0:
        high = max(high, _forward_verify_complete(root_dir, cached_complete, complete_fn))
        return max(high, _max_from_arcs(root_dir))

    if allow_full_scan:
        return max(high, _scan_disk_high(root_dir, min_num=high))

    return max(high, _scan_disk_high(root_dir, min_num=max(0, high - 5)))