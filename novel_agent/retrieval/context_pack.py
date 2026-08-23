"""Budget-aware Context Pack preserving required fact coverage."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .models import RetrievalCandidate


def build_context_pack(
    candidates: Sequence[RetrievalCandidate],
    *,
    required_memory_ids: Sequence[str] = (),
    max_chars: int = 12_000,
) -> dict[str, Any]:
    budget = max(1, int(max_chars))
    required = {str(item) for item in required_memory_ids if str(item)}
    ordered = sorted(
        candidates,
        key=lambda item: (
            0 if item.memory_id in required or item.hardness == "required" else 1,
            -float(item.fused_score),
            item.memory_id,
        ),
    )
    included: list[RetrievalCandidate] = []
    used = 0
    omitted_required: list[str] = []
    for item in ordered:
        text = item.text.strip()
        if not text:
            continue
        rendered = text if not included else "\n\n" + text
        if used + len(rendered) > budget:
            if item.memory_id in required or item.hardness == "required":
                omitted_required.append(item.memory_id)
            continue
        included.append(item)
        used += len(rendered)
    requested = len(required) or sum(item.hardness == "required" for item in candidates)
    included_required = sum(
        item.memory_id in required or item.hardness == "required" for item in included
    )
    coverage = included_required / requested if requested else 1.0
    return {
        "items": [item.to_dict() for item in included],
        "text": "\n\n".join(item.text.strip() for item in included),
        "char_count": used,
        "max_chars": budget,
        "required_memory_ids": sorted(required),
        "included_required_memory_ids": [
            item.memory_id for item in included if item.memory_id in required or item.hardness == "required"
        ],
        "missing_required_memory_ids": sorted(set(omitted_required) | (required - {item.memory_id for item in included})),
        "coverage": round(coverage, 6),
        "status": "error" if omitted_required else "ready",
        "truncation_reason": "required_over_budget" if omitted_required else "",
        "route_hits": {
            route: sum(route in item.routes for item in included)
            for route in sorted({route for item in included for route in item.routes})
        },
    }
