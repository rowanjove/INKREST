"""Optional deterministic reranking; no model dependency by default."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .models import RetrievalCandidate


def resolve_reranker_readiness(root_dir: Path) -> dict[str, Any]:
    """Describe declarative reranker configuration without loading an SDK."""

    try:
        from novel_agent.pipeline import load_pipeline_settings

        settings = load_pipeline_settings(Path(root_dir))
    except Exception:
        settings = {}
    config = settings.get("reranker") or (settings.get("runtime") or {}).get("reranker") or {}
    if not isinstance(config, dict) or not config:
        return {"status": "disabled", "mode": "deterministic", "reason": "optional local/API reranker not configured"}
    provider = str(config.get("provider") or "").strip().lower()
    model = str(config.get("model") or config.get("model_id") or "").strip()
    endpoint = str(config.get("endpoint") or config.get("base_url") or "").strip()
    if provider not in {"local", "api", "plugin"}:
        return {"status": "invalid", "mode": "deterministic", "reason": "provider must be local, api, or plugin"}
    if not model and not endpoint:
        return {"status": "invalid", "mode": "deterministic", "reason": "model/model_id or endpoint is required"}
    return {
        "status": "configured",
        "mode": provider,
        "model": model,
        "endpoint_configured": bool(endpoint),
        "reason": "declarative configuration present; runtime adapter remains opt-in",
    }


def deterministic_rerank(
    candidates: Sequence[RetrievalCandidate],
    *,
    entity_hits: set[str] | None = None,
    reranker: Callable[[Sequence[RetrievalCandidate]], Sequence[RetrievalCandidate]] | None = None,
    limit: int = 50,
) -> list[RetrievalCandidate]:
    """Apply a bounded deterministic score; optional reranker failures fall back."""

    if reranker is not None:
        try:
            candidate_result = list(reranker(candidates))
            if candidate_result:
                candidates = candidate_result
        except Exception:
            pass
    entities = entity_hits or set()
    ranked = []
    for item in candidates:
        score = float(item.fused_score)
        score += 0.20 if item.hardness == "required" else 0.05
        score += 0.10 * len(entities.intersection(set(item.routes)))
        ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].memory_id))
    return [item for _, item in ranked[: max(1, min(int(limit), 500))]]
