"""Shared Context Pack identity and role-binding artifacts.

Writer, auditor and style-editor calls may use different prompt windows, but
they must be traceable to the same source-bound pack/render contract.  This
module stores only hashes and bounded metadata, never a second narrative truth
source or unbounded duplicate of the manuscript.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTEXT_CONTRACT_SCHEMA_VERSION = 1


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def context_pack_id(
    *,
    chapter_id: str,
    scene_id: str = "",
    context_text: str = "",
    required_memory_ids: Sequence[str] = (),
    content_lock_id: str = "",
) -> str:
    return "ctx:" + _digest(
        {
            "chapter_id": str(chapter_id),
            "scene_id": str(scene_id),
            "context_sha256": _digest(str(context_text or "")),
            "required_memory_ids": sorted(str(item) for item in required_memory_ids if str(item)),
            "content_lock_id": str(content_lock_id or ""),
        }
    )[:32]


def context_pack_path(root_dir: Path, chapter_id: str, scene_id: str = "") -> Path:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(scene_id or "chapter"))
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / f"context_pack_{safe or 'chapter'}.json"


def save_context_pack_contract(root_dir: Path, payload: Mapping[str, Any]) -> Path:
    chapter_id = str(payload.get("chapter_id") or "")
    scene_id = str(payload.get("scene_id") or "chapter")
    path = context_pack_path(root_dir, chapter_id, scene_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": CONTEXT_CONTRACT_SCHEMA_VERSION,
        "pack_id": str(payload.get("pack_id") or ""),
        "chapter_id": chapter_id,
        "scene_id": scene_id,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "context_sha256": str(payload.get("context_sha256") or ""),
        "content_lock_id": str(payload.get("content_lock_id") or ""),
        "required_memory_ids": sorted(str(item) for item in payload.get("required_memory_ids") or [] if str(item)),
        "coverage": payload.get("coverage"),
        "status": str(payload.get("status") or "ready"),
        "route_hits": dict(payload.get("route_hits") or {}),
        "roles": sorted({str(item) for item in payload.get("roles") or ["writer"] if str(item)}),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def load_context_pack_contract(root_dir: Path, chapter_id: str, scene_id: str = "") -> dict[str, Any]:
    path = context_pack_path(root_dir, chapter_id, scene_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def bind_context_role(root_dir: Path, chapter_id: str, *, role: str, pack_id: str, report_name: str = "context_bindings.json") -> Path:
    """Record a role binding without modifying the immutable pack identity."""

    path = Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / report_name
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        current = {}
    document = dict(current) if isinstance(current, Mapping) else {}
    bindings = dict(document.get("bindings") or {})
    bindings[str(role)] = {"pack_id": str(pack_id), "bound_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    document.update({"schema_version": CONTEXT_CONTRACT_SCHEMA_VERSION, "bindings": bindings})
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def bind_latest_context_role(root_dir: Path, chapter_id: str, *, role: str) -> Path | None:
    """Bind a downstream role to the newest Context Pack for a chapter.

    The helper is deliberately report-only: it never rebuilds context and never
    mutates the pack.  This makes auditor/style-editor provenance available
    even when those stages run after a scene writer in a separate process.
    """

    report_dir = Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports"
    candidates = [path for path in report_dir.glob("context_pack_*.json") if path.is_file()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime_ns)
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    pack_id = str(payload.get("pack_id") or "") if isinstance(payload, Mapping) else ""
    if not pack_id:
        return None
    return bind_context_role(root_dir, chapter_id, role=role, pack_id=pack_id)


__all__ = [
    "CONTEXT_CONTRACT_SCHEMA_VERSION",
    "bind_context_role",
    "bind_latest_context_role",
    "context_pack_id",
    "context_pack_path",
    "load_context_pack_contract",
    "save_context_pack_contract",
]
