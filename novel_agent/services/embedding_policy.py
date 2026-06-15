"""Resolve effective embedding backend for long/epic projects."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from novel_agent.control.runtime_policy import merge_scale_profile, resolve_runtime_policy
from novel_agent.state.vector_store import CHROMA_AVAILABLE


def _target_chapters(root_dir: Path) -> int:
    policy = resolve_runtime_policy(root_dir)
    return int(policy.target_chapters or 0)


def should_prefer_chromadb_backend(root_dir: Path) -> bool:
    policy = resolve_runtime_policy(root_dir)
    if not policy.vector_enabled:
        return False
    scale = str(policy.scale or "medium")
    target = _target_chapters(root_dir)
    if scale in ("long", "epic", "infinite") or target >= 100:
        return True
    profile = merge_scale_profile({"scale": scale, "target_chapters": target})
    return str(profile.get("embedding_backend") or "").strip().lower() == "chromadb"


def _wants_chromadb_backend(root_dir: Path) -> bool:
    return should_prefer_chromadb_backend(root_dir)


def resolve_embedding_config(settings: Dict[str, Any], root_dir: Path) -> Dict[str, Any]:
    """Apply scale-aware defaults (Chroma for long runs when available)."""
    raw_emb = settings.get("embedding") or {}
    emb = deepcopy(raw_emb)
    backend_explicit = "backend" in raw_emb
    backend = str(emb.get("backend") or "sqlite").strip().lower()
    policy = resolve_runtime_policy(root_dir)
    profile = merge_scale_profile(
        {
            "scale": policy.scale,
            "target_chapters": _target_chapters(root_dir),
        }
    )

    prefer_chroma = _wants_chromadb_backend(root_dir) or (
        str(profile.get("embedding_backend") or "").strip().lower() == "chromadb"
    )
    if prefer_chroma and backend == "sqlite" and not backend_explicit:
        if CHROMA_AVAILABLE:
            emb["backend"] = "chromadb"
        else:
            emb.setdefault(
                "_backend_hint",
                "install chromadb for long-form vector recall",
            )

    rebuild = profile.get("hnsw_rebuild_every")
    if rebuild is not None:
        emb["_scale_hnsw_rebuild_every"] = int(rebuild)

    return emb


def create_vector_store_for_project(root_dir: Path):
    """Create a vector store with scale-aware backend defaults applied."""
    from novel_agent.pipeline import load_pipeline_settings
    from novel_agent.state.vector_store import create_vector_store

    settings = load_pipeline_settings(root_dir)
    config = resolve_embedding_config(settings, root_dir)
    return create_vector_store(config, root_dir=root_dir)