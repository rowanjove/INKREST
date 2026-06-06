"""Arc-level batch queue and novel batch progress for long runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.logging_config import get_logger

logger = get_logger("services.arc_queue")

PROGRESS_PATH_REL = "workspace/reports/novel_batch_progress.json"


def progress_path(root_dir: Path) -> Path:
    return Path(root_dir) / PROGRESS_PATH_REL


def load_arc_progress(root_dir: Path) -> Dict[str, Any]:
    path = progress_path(root_dir)
    if not path.exists():
        return {"status": "idle", "arcs": {}, "completed_chapters": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"status": "idle", "arcs": {}, "completed_chapters": 0}


def save_arc_progress(root_dir: Path, data: Dict[str, Any]) -> None:
    path = progress_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_workspace_arcs(root_dir: Path) -> List[Dict[str, Any]]:
    """Load arc_*.json files written by managing editor."""
    workspace = Path(root_dir) / "workspace"
    arcs: List[Dict[str, Any]] = []
    for path in sorted(workspace.glob("arc_*.json")):
        try:
            arc = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(arc, dict):
                arc.setdefault("arc_id", path.stem.replace("arc_", "", 1))
                arcs.append(arc)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skip invalid arc file %s: %s", path, exc)
    return arcs


def chapter_id_from_brief(brief: Dict[str, Any], fallback: str = "") -> str:
    return str(brief.get("chapter_id") or brief.get("id") or fallback).strip()


def sort_briefs_by_dependencies(briefs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Topological sort by optional depends_on chapter ids."""
    if not briefs:
        return []
    id_map: Dict[str, Dict[str, Any]] = {}
    for brief in briefs:
        cid = chapter_id_from_brief(brief)
        if cid:
            id_map[cid] = brief

    indegree: Dict[str, int] = {cid: 0 for cid in id_map}
    edges: Dict[str, List[str]] = {cid: [] for cid in id_map}
    for cid, brief in id_map.items():
        deps = brief.get("depends_on") or brief.get("depends") or []
        if isinstance(deps, str):
            deps = [deps]
        for dep in deps:
            dep_id = str(dep).strip()
            if dep_id not in id_map:
                continue
            edges[dep_id].append(cid)
            indegree[cid] = indegree.get(cid, 0) + 1

    queue = [cid for cid, deg in indegree.items() if deg == 0]
    ordered_ids: List[str] = []
    while queue:
        queue.sort()
        current = queue.pop(0)
        ordered_ids.append(current)
        for nxt in edges.get(current, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(ordered_ids) < len(id_map):
        logger.warning("Arc briefs have dependency cycle; falling back to list order")
        return briefs

    ordered = [id_map[cid] for cid in ordered_ids]
    for brief in briefs:
        cid = chapter_id_from_brief(brief)
        if not cid or cid in id_map:
            continue
        ordered.append(brief)
    return ordered


def filter_briefs_for_resume(
    briefs: List[Dict[str, Any]],
    chapter_complete_fn,
) -> List[Dict[str, Any]]:
    """Skip chapters that already reached post_audit in checkpoint."""
    out: List[Dict[str, Any]] = []
    for brief in briefs:
        cid = chapter_id_from_brief(brief)
        if not cid or chapter_complete_fn(cid):
            continue
        out.append(brief)
    return out


def select_arcs(
    arcs: List[Dict[str, Any]],
    arc_id: Optional[str] = None,
    arc_ids: Optional[List[str]] = None,
    start_arc_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if arc_id:
        return [a for a in arcs if str(a.get("arc_id")) == arc_id]
    if arc_ids:
        wanted = set(arc_ids)
        return [a for a in arcs if str(a.get("arc_id")) in wanted]
    if start_arc_id:
        started = False
        picked: List[Dict[str, Any]] = []
        for arc in arcs:
            if str(arc.get("arc_id")) == start_arc_id:
                started = True
            if started:
                picked.append(arc)
        return picked
    return list(arcs)


def record_novel_batch_paused(
    root_dir: Path,
    *,
    reason: str,
    last_chapter: str = "",
    arc_id: str = "",
    streak: int = 0,
) -> Dict[str, Any]:
    data = load_arc_progress(root_dir)
    data["status"] = "paused"
    data["pause_reason"] = reason
    data["last_chapter_id"] = last_chapter
    if arc_id:
        data["last_arc_id"] = arc_id
    data["fail_streak"] = streak
    save_arc_progress(root_dir, data)
    return data


def clear_batch_pause_for_resume(root_dir: Path) -> Dict[str, Any]:
    """Clear circuit-breaker pause when user or API resumes arc/novel batch."""
    data = load_arc_progress(root_dir)
    if data.get("status") == "paused":
        data["status"] = "running"
        data.pop("pause_reason", None)
        data["fail_streak"] = 0
        save_arc_progress(root_dir, data)
    return data


def mark_novel_batch_finished(root_dir: Path) -> Dict[str, Any]:
    data = load_arc_progress(root_dir)
    if data.get("status") != "paused":
        data["status"] = "done"
    save_arc_progress(root_dir, data)
    return data


def mark_arc_progress(
    root_dir: Path,
    arc_id: str,
    status: str,
    last_chapter_id: str = "",
    chapters_done: int = 0,
) -> Dict[str, Any]:
    data = load_arc_progress(root_dir)
    arcs_map = dict(data.get("arcs") or {})
    arcs_map[arc_id] = {"status": status, "last_chapter_id": last_chapter_id}
    data["arcs"] = arcs_map
    data["last_arc_id"] = arc_id
    if last_chapter_id:
        data["last_chapter_id"] = last_chapter_id
    # Global status: paused only via record_novel_batch_paused; do not promote per-arc "done".
    if status == "paused":
        data["status"] = "paused"
    elif status == "running" and data.get("status") != "paused":
        data["status"] = "running"
    if status == "done" and chapters_done:
        data["completed_chapters"] = int(data.get("completed_chapters") or 0) + chapters_done
    save_arc_progress(root_dir, data)
    return data


def should_run_by_arc_batches(target_chapters: int, scale: str) -> bool:
    if target_chapters >= 80:
        return True
    return scale in ("long", "epic", "infinite")