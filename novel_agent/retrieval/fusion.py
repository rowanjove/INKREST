"""Deterministic reciprocal-rank fusion with provenance-preserving dedupe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .models import RetrievalCandidate


def reciprocal_rank_fusion(
    routes: Mapping[str, Sequence[Mapping[str, Any] | RetrievalCandidate]],
    *,
    k: int = 60,
    limit: int = 50,
) -> list[RetrievalCandidate]:
    if int(k) <= 0:
        raise ValueError("RRF k must be positive")
    merged: dict[str, RetrievalCandidate] = {}
    for route_name in sorted(routes):
        for rank, raw in enumerate(routes[route_name], start=1):
            candidate = raw if isinstance(raw, RetrievalCandidate) else RetrievalCandidate.from_mapping(raw, route=route_name)
            if not candidate.memory_id:
                continue
            current = merged.get(candidate.memory_id)
            if current is None:
                current = candidate
                current.routes = list(dict.fromkeys(current.routes))
                current.route_scores = dict(current.route_scores)
                current.fused_score = 0.0
                merged[candidate.memory_id] = current
            if route_name not in current.routes:
                current.routes.append(route_name)
            current.route_scores[route_name] = max(
                float(current.route_scores.get(route_name, 0.0)),
                float(candidate.route_scores.get(route_name, candidate.fused_score)),
            )
            current.fused_score += 1.0 / (int(k) + rank)
            if candidate.hardness == "required":
                current.hardness = "required"
            current.superseded = current.superseded or candidate.superseded
    ordered = sorted(
        merged.values(),
        key=lambda item: (-item.fused_score, item.memory_id, item.source_revision_id),
    )
    return ordered[: max(1, min(int(limit), 500))]
