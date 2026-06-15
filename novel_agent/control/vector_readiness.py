"""Vector / embedding readiness policy for long-form continue."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

VectorReadinessLevel = Literal["ok", "warn", "block", "ignore"]

_LONG_SCALES = frozenset({"long", "epic", "infinite"})


def resolve_vector_readiness_level(root_dir: Path, scale: str, *, vector_stub: bool) -> VectorReadinessLevel:
    """
    Decide how to treat stub/missing embedding on long-form projects.

    runtime.vector_readiness:
      - auto (default): block when factory longform_stable + stub; else warn on long scales
      - block / warn / ignore: force behavior
    """
    if not vector_stub or scale not in _LONG_SCALES:
        return "ok"

    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    override = str(runtime.get("vector_readiness") or "auto").strip().lower()
    if override in ("block", "warn", "ignore"):
        return override  # type: ignore[return-value]

    from novel_agent.control.factory_policy import factory_requires_vector_for_long_scale

    if factory_requires_vector_for_long_scale(root_dir):
        return "block"
    return "warn"