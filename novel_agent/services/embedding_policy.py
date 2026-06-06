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
    return scale in ("long", "epic", "infinite") or target >= 100


def resolve_embedding_config(settings: Dict[str, Any], root_dir: Path) -> Dict[str, Any]:
    """Apply scale-aware defaults (Chroma for long runs when available)."""
    emb = deepcopy(settings.get("embedding") or {})
    provider = str(emb.get("provider") or "stub").strip().lower()
    backend = str(emb.get("backend") or "sqlite").strip().lower()

    if provider != "stub" and should_prefer_chromadb_backend(root_dir):
        if backend == "sqlite" and CHROMA_AVAILABLE:
            emb["backend"] = "chromadb"
        elif backend == "sqlite" and not CHROMA_AVAILABLE:
            emb.setdefault("_backend_hint", "install chromadb for long-form vector recall")

    profile = merge_scale_profile(
        {
            "scale": resolve_runtime_policy(root_dir).scale,
            "target_chapters": _target_chapters(root_dir),
        }
    )
    rebuild = profile.get("hnsw_rebuild_every")
    if rebuild is not None:
        emb["_scale_hnsw_rebuild_every"] = int(rebuild)

    return emb