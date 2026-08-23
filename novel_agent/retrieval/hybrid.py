"""Hybrid retrieval adapter that keeps legacy routes optional."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .fusion import reciprocal_rank_fusion
from .models import RetrievalCandidate


def hybrid_search(
    store: Any,
    query: str,
    *,
    limit: int = 20,
    before_chapter: str | None = None,
    route_results: Mapping[str, Sequence[Mapping[str, Any] | RetrievalCandidate]] | None = None,
) -> list[RetrievalCandidate]:
    """Combine FTS with caller-provided adjacent/entity/vector routes.

    A failed optional route is represented by an empty list; FTS results stay
    available.  This lets Chroma/vector integrations fail soft without
    fabricating an empty context.
    """

    routes: dict[str, Sequence[Mapping[str, Any] | RetrievalCandidate]] = {
        "fts": [
            *store.search_story(
                query,
                limit=max(1, int(limit) * 3),
                before_chapter=before_chapter,
            )
        ]
    }
    for name, values in (route_results or {}).items():
        routes[str(name)] = list(values or [])
    return reciprocal_rank_fusion(routes, limit=limit)
