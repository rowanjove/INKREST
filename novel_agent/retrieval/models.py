"""Stable, provenance-preserving retrieval result contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Hardness = Literal["required", "supporting", "style"]


@dataclass
class RetrievalCandidate:
    memory_id: str
    kind: str
    text: str
    source_chapter: str = ""
    source_revision_id: str = ""
    source_span: list[int] | None = None
    routes: list[str] = field(default_factory=list)
    route_scores: dict[str, float] = field(default_factory=dict)
    fused_score: float = 0.0
    hardness: Hardness = "supporting"
    superseded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: dict[str, Any], *, route: str = "") -> "RetrievalCandidate":
        routes = [str(item) for item in value.get("routes", []) if str(item)]
        if route and route not in routes:
            routes.append(route)
        route_scores = {
            str(key): float(score)
            for key, score in (value.get("route_scores") or {}).items()
        }
        if route and "route_score" in value:
            route_scores[route] = float(value.get("route_score") or 0.0)
        return cls(
            memory_id=str(value.get("memory_id") or value.get("id") or ""),
            kind=str(value.get("kind") or "memory"),
            text=str(value.get("text") or value.get("summary") or ""),
            source_chapter=str(value.get("source_chapter") or value.get("chapter_id") or ""),
            source_revision_id=str(value.get("source_revision_id") or ""),
            source_span=value.get("source_span") if isinstance(value.get("source_span"), list) else None,
            routes=routes,
            route_scores=route_scores,
            fused_score=float(value.get("fused_score") or 0.0),
            hardness=str(value.get("hardness") or "supporting"),
            superseded=bool(value.get("superseded", False)),
        )
