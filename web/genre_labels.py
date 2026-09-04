"""Resolve internal theme identifiers to user-facing genre labels."""

from pathlib import Path

from fastapi import HTTPException

from web.preset_manager import PresetManager


def normalize_genre_label(base_dir: Path, value: object) -> str:
    """Return a theme's Chinese display name while preserving free-form genres."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        component = PresetManager(Path(base_dir)).get_component("themes", raw)
    except (HTTPException, OSError, ValueError):
        return raw
    return str(component.get("name") or raw).strip() or raw
