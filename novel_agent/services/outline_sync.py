"""Detect when workspace arc queue is out of date vs outline.json macro_outline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from novel_agent.services.arc_queue import load_workspace_arcs


def macro_outline_fingerprint(macro_outline: List[Dict[str, Any]]) -> str:
    payload = json.dumps(
        [
            {
                "arc_id": a.get("arc_id"),
                "name": a.get("name"),
                "chapters": a.get("chapters"),
                "goal": (a.get("goal") or "")[:200],
            }
            for a in (macro_outline or [])
            if isinstance(a, dict)
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def arcs_queue_fingerprint(root_dir: Path) -> str:
    arcs = load_workspace_arcs(root_dir)
    payload = json.dumps(
        [
            {
                "arc_id": a.get("arc_id"),
                "n": len(a.get("chapters") or []),
                "first": (a.get("chapters") or [{}])[0].get("chapter_id")
                if a.get("chapters")
                else None,
            }
            for a in arcs
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _sync_meta_path(root_dir: Path) -> Path:
    return root_dir / "workspace" / "reports" / "outline_arc_sync.json"


def record_outline_saved(root_dir: Path, outline: Dict[str, Any]) -> None:
    path = _sync_meta_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    macro = outline.get("macro_outline") or []
    doc = {
        "outline_fp": macro_outline_fingerprint(macro),
        "arcs_fp_at_save": arcs_queue_fingerprint(root_dir),
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def check_arc_queue_stale(root_dir: Path) -> Dict[str, Any]:
    outline_path = root_dir / "workspace" / "outline.json"
    if not outline_path.is_file():
        return {"stale": False, "reason": "no_outline"}

    try:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "stale": True,
            "reason": "outline_read_error",
            "message": f"outline.json 无法解析（{exc}），请在大纲页修复或从备份恢复后再续跑全书。",
        }

    macro = outline.get("macro_outline") or []
    if not macro:
        return {"stale": False, "reason": "no_macro"}

    current_outline_fp = macro_outline_fingerprint(macro)
    current_arcs_fp = arcs_queue_fingerprint(root_dir)
    meta_path = _sync_meta_path(root_dir)

    if not meta_path.is_file():
        return {
            "stale": bool(load_workspace_arcs(root_dir)),
            "reason": "never_synced",
            "message": "大纲已保存，但卷级队列可能尚未按新卷纲重建。续跑前建议同步卷队列。",
            "outline_fp": current_outline_fp,
            "arcs_fp": current_arcs_fp,
        }

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        meta = {}

    saved_outline_fp = str(meta.get("outline_fp") or "")
    if saved_outline_fp and saved_outline_fp != current_outline_fp:
        return {
            "stale": True,
            "reason": "outline_changed",
            "message": "宏观卷纲已变更，与当前 arc 队列不一致。请在大纲页「同步卷队列」后再工作台续跑。",
            "outline_fp": current_outline_fp,
            "arcs_fp": current_arcs_fp,
            "saved_outline_fp": saved_outline_fp,
        }

    arcs_at_save = str(meta.get("arcs_fp_at_save") or "")
    if arcs_at_save and arcs_at_save != current_arcs_fp:
        return {
            "stale": True,
            "reason": "arcs_modified_externally",
            "message": "检测到 arc 文件与上次保存大纲时不一致，建议确认卷队列。",
            "outline_fp": current_outline_fp,
            "arcs_fp": current_arcs_fp,
        }

    return {
        "stale": False,
        "reason": "ok",
        "outline_fp": current_outline_fp,
        "arcs_fp": current_arcs_fp,
    }


def mark_arcs_synced_with_outline(root_dir: Path) -> Dict[str, Any]:
    outline_path = root_dir / "workspace" / "outline.json"
    outline = {}
    if outline_path.is_file():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    record_outline_saved(root_dir, outline)
    return check_arc_queue_stale(root_dir)