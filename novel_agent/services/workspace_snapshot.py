"""Workspace Checkpoint & Disaster Recovery Service.

Allows creating and restoring atomic checkpoints of workspace outlines,
character assets, and serialized arcs before/after large autopilot generation runs.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _get_checkpoints_dir(root_dir: Path) -> Path:
    cp_dir = Path(root_dir) / "data" / "checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    return cp_dir


def create_workspace_checkpoint(root_dir: Path, label: str = "auto") -> dict[str, Any]:
    """Capture an incremental snapshot of essential story state."""
    root = Path(root_dir)
    cp_dir = _get_checkpoints_dir(root)
    timestamp = int(time.time())
    iso_time = datetime.now(timezone.utc).isoformat()
    clean_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")) or "checkpoint"
    checkpoint_id = f"cp_{timestamp}_{clean_label}"
    target_dir = cp_dir / checkpoint_id
    target_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []

    # 1. Capture workspace outline & arc files
    ws = root / "workspace"
    if ws.is_dir():
        ws_target = target_dir / "workspace"
        ws_target.mkdir(parents=True, exist_ok=True)
        for item in ws.iterdir():
            if item.is_file() and (item.name.endswith(".json") or item.name.endswith(".yaml")):
                shutil.copy2(item, ws_target / item.name)
                copied_files.append(f"workspace/{item.name}")

    # 2. Capture assets
    assets = root / "assets"
    if assets.is_dir():
        assets_target = target_dir / "assets"
        assets_target.mkdir(parents=True, exist_ok=True)
        for item in assets.iterdir():
            if item.is_file() and (item.name.endswith(".json") or item.name.endswith(".yaml") or item.name.endswith(".txt")):
                shutil.copy2(item, assets_target / item.name)
                copied_files.append(f"assets/{item.name}")

    # 3. Write checkpoint manifest
    manifest = {
        "id": checkpoint_id,
        "label": label,
        "timestamp": timestamp,
        "created_at": iso_time,
        "copied_files": copied_files,
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return manifest


def list_workspace_checkpoints(root_dir: Path) -> list[dict[str, Any]]:
    """List existing checkpoints ordered from newest to oldest."""
    root = Path(root_dir)
    cp_dir = _get_checkpoints_dir(root)
    checkpoints: list[dict[str, Any]] = []

    for entry in cp_dir.iterdir():
        if entry.is_dir() and (entry / "manifest.json").is_file():
            try:
                data = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    checkpoints.append(data)
            except Exception:
                continue

    checkpoints.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return checkpoints


def restore_workspace_checkpoint(root_dir: Path, checkpoint_id: str) -> bool:
    """Restore workspace and asset state from a saved checkpoint."""
    clean_id = str(checkpoint_id or "").strip()
    if not clean_id or not re.match(r"^cp_[0-9]+_[a-zA-Z0-9_\-]+$", clean_id):
        return False

    root = Path(root_dir)
    cp_dir = _get_checkpoints_dir(root).resolve()
    target_dir = (cp_dir / clean_id).resolve()
    try:
        if not target_dir.is_relative_to(cp_dir):
            return False
    except AttributeError:
        # Fallback for Python versions without is_relative_to
        if not str(target_dir).startswith(str(cp_dir)):
            return False

    if not target_dir.is_dir() or not (target_dir / "manifest.json").is_file():
        return False

    # Restore workspace files
    cp_ws = target_dir / "workspace"
    if cp_ws.is_dir():
        ws = root / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        for item in cp_ws.iterdir():
            if item.is_file():
                shutil.copy2(item, ws / item.name)

    # Restore asset files
    cp_assets = target_dir / "assets"
    if cp_assets.is_dir():
        assets = root / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        for item in cp_assets.iterdir():
            if item.is_file():
                shutil.copy2(item, assets / item.name)

    return True
